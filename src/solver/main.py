"""Main entry point for the Solver Telegram bot."""

import asyncio
import sys
from typing import Callable, Awaitable

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from telegram.ext import Application, CommandHandler, ContextTypes

from solver.config import get_settings
from solver.application.ai_service import OpenAIAnalysisService
from solver.application.services import ProblemService
from solver.infrastructure.database import create_engine, create_session_factory, Base
from solver.infrastructure.repositories import (
    SqlAlchemyUserRepository,
    SqlAlchemyProblemRepository,
    SqlAlchemyConversationContextRepository,
)
from solver.presentation.handlers import BotHandlers
from solver.infrastructure.scheduler import ProactiveScheduler


ServiceFactory = Callable[[ContextTypes.DEFAULT_TYPE], Awaitable[ProblemService]]


def setup_logging(level: str = "INFO") -> None:
    """Configure application logging."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan> - <level>{message}</level>"
        ),
    )


def build_application(settings, session_factory) -> Application:
    """Build and configure the Telegram bot application."""
    ai_service = OpenAIAnalysisService(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        base_url=settings.ai_base_url,
    )

    async def service_factory(context: ContextTypes.DEFAULT_TYPE) -> ProblemService:
        """Create a ProblemService with a fresh DB session per request."""
        session: AsyncSession = session_factory()
        return ProblemService(
            problem_repo=SqlAlchemyProblemRepository(session),
            user_repo=SqlAlchemyUserRepository(session),
            context_repo=SqlAlchemyConversationContextRepository(session),
            ai_service=ai_service,
        )

    app = Application.builder().token(settings.telegram_bot_token).build()

    handlers = BotHandlers(service_factory=service_factory)

    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("help", handlers.help_cmd))
    app.add_handler(CommandHandler("test", handlers.test_cmd))
    app.add_handler(CommandHandler("run_test", handlers.run_test_cmd))
    app.add_handler(CommandHandler("list", handlers.list_problems))
    app.add_handler(CommandHandler("view", handlers.view_problem))
    app.add_handler(CommandHandler("done", handlers.done_step))
    app.add_handler(handlers.build_new_problem_handler())

    logger.info("Bot handlers registered")
    return app


def main() -> None:
    """Main entry point."""
    settings = get_settings()
    setup_logging(settings.log_level)

    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Configure your .env file.")
        sys.exit(1)

    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY is not set. AI analysis will not work.")

    logger.info("Starting Solver bot...")

    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    async def _run():
        # Init DB
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")

        # Build app
        app = build_application(settings, session_factory)

        # Initialize and start bot
        await app.initialize()
        await app.start()

        # --- Proactive scheduler ---
        ai_service = OpenAIAnalysisService(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.ai_base_url,
        )

        async def _send_nudge(telegram_id: int, text: str) -> None:
            """Send a proactive nudge to a user via the bot."""
            try:
                await app.bot.send_message(chat_id=telegram_id, text=text)
            except Exception as e:
                logger.warning(f"Failed to send nudge to {telegram_id}: {e}")

        _sched_session = session_factory()
        scheduler = ProactiveScheduler(
            user_repo=SqlAlchemyUserRepository(_sched_session),
            problem_repo=SqlAlchemyProblemRepository(_sched_session),
            context_repo=SqlAlchemyConversationContextRepository(_sched_session),
            ai_service=ai_service,
            notification_sender=_send_nudge,
            check_interval_minutes=settings.proactive_check_interval_minutes,
        )
        scheduler.start()
        logger.info("Proactive scheduler started")
        # ---

        await app.updater.start_polling()
        logger.info("Bot is polling... Press Ctrl+C to stop")

        # Wait until stopped
        stop_event = asyncio.Event()
        try:
            await stop_event.wait()
        except asyncio.CancelledError:
            pass
        finally:
            scheduler.stop()
            await app.updater.stop()
            await app.stop()
            await app.shutdown()
            logger.info("Bot stopped")

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
