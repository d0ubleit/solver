"""E2E tests for the Telegram bot — full handler → service → repository flow.

Tests simulate real user interactions: /start, /new, /list, /view, /done.
Uses real SQLite + mocked AI — covers the full code path through all layers.
"""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from telegram import Update, User as TgUser, Message, Chat

from solver.application.ai_service import AIAnalysisService
from solver.application.dtos import AIAnalysisResponseDTO
from solver.application.services import ProblemService
from solver.infrastructure.database import Base
from solver.infrastructure.repositories import (
    SqlAlchemyUserRepository,
    SqlAlchemyProblemRepository,
    SqlAlchemyConversationContextRepository,
)
from solver.presentation.handlers import BotHandlers


# ═══════════════════════════════════════════════════════════════════
# Fake Telegram objects
# ═══════════════════════════════════════════════════════════════════

class _FakeBot:
    """Fake bot that collects sent messages instead of calling Telegram API."""

    def __init__(self) -> None:
        self.sent_messages: list[dict] = []
        self.defaults = None  # PTB checks this

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str | None = None,
        reply_markup=None,
        **kwargs,
    ):
        self.sent_messages.append({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        })
        fake_msg = Message(
            message_id=len(self.sent_messages),
            date=datetime.now(),
            chat=Chat(id=chat_id, type="private"),
            text=text,
        )
        fake_msg.set_bot(self)
        return fake_msg


def _make_update(
    text: str,
    user_id: int = 12345,
    first_name: str = "Test",
    chat_id: int | None = None,
    bot: _FakeBot | None = None,
) -> tuple[Update, _FakeBot]:
    """Build a synthetic Telegram Update. Returns (update, fake_bot)."""
    if bot is None:
        bot = _FakeBot()

    cid = chat_id or user_id
    tg_user = TgUser(id=user_id, is_bot=False, first_name=first_name)
    chat = Chat(id=cid, type="private")
    message = Message(
        message_id=1,
        date=datetime.now(),
        chat=chat,
        from_user=tg_user,
        text=text,
    )
    for obj in (message, chat, tg_user):
        obj.set_bot(bot)

    update = Update(update_id=1, message=message)
    update.set_bot(bot)
    return update, bot


class _FakeContext:
    """Minimal fake ContextTypes for handlers."""

    def __init__(self, bot: _FakeBot, update: Update) -> None:
        self.bot = bot
        self._update = update
        self.user_data: dict = {}
        self.application = type("app", (), {"bot_data": {}})()

    @property
    def effective_user(self) -> TgUser:
        return self._update.effective_user

    @property
    def effective_chat(self) -> Chat:
        return self._update.effective_chat


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest_asyncio.fixture
async def db_session():
    """In-memory SQLite session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def problem_service(db_session: AsyncSession):
    """Real ProblemService with in-memory DB and mocked AI."""
    ai = AsyncMock(spec=AIAnalysisService)
    ai.analyze.return_value = AIAnalysisResponseDTO(
        analysis="Тестовый анализ.",
        steps=["Шаг 1: Понять суть", "Шаг 2: Составить план", "Шаг 3: Действовать"],
        tokens_used=50,
    )
    ai.check_in.return_value = "Как продвигается? Нужна помощь?"
    return ProblemService(
        problem_repo=SqlAlchemyProblemRepository(db_session),
        user_repo=SqlAlchemyUserRepository(db_session),
        context_repo=SqlAlchemyConversationContextRepository(db_session),
        ai_service=ai,
    )


@pytest_asyncio.fixture
async def handlers(problem_service: ProblemService):
    """BotHandlers backed by real services."""
    async def _factory(_ctx):
        return problem_service
    return BotHandlers(service_factory=_factory)


# ═══════════════════════════════════════════════════════════════════
# E2E Tests
# ═══════════════════════════════════════════════════════════════════

class TestStartCommand:
    @pytest.mark.asyncio
    async def test_start_sends_welcome(self, handlers):
        update, bot = _make_update("/start", user_id=111)
        ctx = _FakeContext(bot, update)
        await handlers.start(update, ctx)

        assert len(bot.sent_messages) == 1
        text = bot.sent_messages[0]["text"]
        assert "Solver" in text
        assert "/new" in text


class TestNewProblemFlow:
    @pytest.mark.asyncio
    async def test_full_creation_with_ai(self, handlers):
        """Full /new flow: title → description → AI analysis with steps."""
        # Use same context AND same FakeBot across conversation steps
        u1, bot = _make_update("/new", user_id=222)
        ctx = _FakeContext(bot, u1)
        await handlers.new_problem_start(u1, ctx)
        assert "Опиши" in bot.sent_messages[0]["text"]

        # title — reuse same context
        u2, _ = _make_update("Конфликт с коллегой", user_id=222, bot=bot)
        ctx._update = u2
        await handlers.new_problem_title(u2, ctx)
        assert "подробнее" in bot.sent_messages[-1]["text"].lower()

        # description → AI fires
        u3, _ = _make_update("Коллега перебивает на совещаниях", user_id=222, bot=bot)
        ctx._update = u3
        await handlers._finish_problem_creation(u3, ctx)
        final = bot.sent_messages[-2]["text"]  # problem details (last is session hint)
        assert "Шаг 1" in final
        assert "Шаг 2" in final
        assert "Шаг 3" in final

    @pytest.mark.asyncio
    async def test_skip_description_still_creates(self, handlers):
        u1, bot = _make_update("/new", user_id=333)
        ctx = _FakeContext(bot, u1)
        await handlers.new_problem_start(u1, ctx)

        u2, _ = _make_update("Быстрая проблема", user_id=333, bot=bot)
        ctx._update = u2
        await handlers.new_problem_title(u2, ctx)

        u3, _ = _make_update("/skip", user_id=333, bot=bot)
        ctx._update = u3
        await handlers.new_problem_skip_description(u3, ctx)
        assert len(bot.sent_messages) >= 1

    @pytest.mark.asyncio
    async def test_cancel_mid_flow(self, handlers):
        u1, b1 = _make_update("/new", user_id=444)
        await handlers.new_problem_start(u1, _FakeContext(b1, u1))

        u2, b2 = _make_update("/cancel", user_id=444)
        await handlers.cancel(u2, _FakeContext(b2, u2))
        assert "отменено" in b2.sent_messages[0]["text"].lower()


class TestListProblems:
    @pytest.mark.asyncio
    async def test_list_empty_for_new_user(self, handlers):
        u, b = _make_update("/list", user_id=555)
        await handlers.list_problems(u, _FakeContext(b, u))
        text = b.sent_messages[0]["text"].lower()
        assert "нет" in text or "активных" in text

    @pytest.mark.asyncio
    async def test_list_shows_created_problem(self, handlers):
        # Create one with shared context
        u1, bot = _make_update("/new", user_id=666)
        ctx = _FakeContext(bot, u1)
        await handlers.new_problem_start(u1, ctx)

        u2, _ = _make_update("Тестовая проблема", user_id=666, bot=bot)
        ctx._update = u2
        await handlers.new_problem_title(u2, ctx)

        u3, _ = _make_update("/skip", user_id=666, bot=bot)
        ctx._update = u3
        await handlers.new_problem_skip_description(u3, ctx)

        # List — fresh context is fine, data is in DB
        u4, b4 = _make_update("/list", user_id=666)
        await handlers.list_problems(u4, _FakeContext(b4, u4))
        assert "Тестовая проблема" in b4.sent_messages[0]["text"]


class TestViewAndDone:
    @pytest.mark.asyncio
    async def test_view_shows_steps(self, handlers):
        # Create with shared context
        u1, bot = _make_update("/new", user_id=777)
        ctx = _FakeContext(bot, u1)
        await handlers.new_problem_start(u1, ctx)

        u2, _ = _make_update("Для просмотра", user_id=777, bot=bot)
        ctx._update = u2
        await handlers.new_problem_title(u2, ctx)

        u3, _ = _make_update("/skip", user_id=777, bot=bot)
        ctx._update = u3
        await handlers.new_problem_skip_description(u3, ctx)

        # View — fresh context
        u4, b4 = _make_update("/view 1", user_id=777)
        await handlers.view_problem(u4, _FakeContext(b4, u4))
        assert "Для просмотра" in b4.sent_messages[0]["text"]

    @pytest.mark.asyncio
    async def test_done_marks_step_complete(self, handlers):
        # Create with shared context
        u1, bot = _make_update("/new", user_id=888)
        ctx = _FakeContext(bot, u1)
        await handlers.new_problem_start(u1, ctx)

        u2, _ = _make_update("Завершаемая", user_id=888, bot=bot)
        ctx._update = u2
        await handlers.new_problem_title(u2, ctx)

        u3, _ = _make_update("/skip", user_id=888, bot=bot)
        ctx._update = u3
        await handlers.new_problem_skip_description(u3, ctx)

        # Done — fresh context
        u4, b4 = _make_update("/done 1 1", user_id=888)
        await handlers.done_step(u4, _FakeContext(b4, u4))
        text = b4.sent_messages[0]["text"].lower()
        assert "выполнен" in text or "прогресс" in text


class TestHelp:
    @pytest.mark.asyncio
    async def test_help_lists_commands(self, handlers):
        u, b = _make_update("/help", user_id=999)
        await handlers.help_cmd(u, _FakeContext(b, u))
        text = b.sent_messages[0]["text"]
        assert "/new" in text
        assert "/list" in text
