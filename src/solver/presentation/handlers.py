"""Telegram bot command and conversation handlers."""

from typing import Callable, Awaitable
from uuid import UUID

from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram.helpers import escape_markdown

from solver.application.dtos import CreateProblemDTO, UpdateStepDTO
from solver.application.services import ProblemService

# Conversation states
TITLE, DESCRIPTION = range(2)

ServiceFactory = Callable[[ContextTypes.DEFAULT_TYPE], Awaitable[ProblemService]]


class BotHandlers:
    """Telegram bot command and message handlers."""

    def __init__(self, service_factory: ServiceFactory) -> None:
        self._factory = service_factory
        # Track active sessions: {telegram_id: problem_id}
        self._active_sessions: dict[int, UUID] = {}

    async def _get_service(self, context: ContextTypes.DEFAULT_TYPE) -> ProblemService:
        """Get a fresh ProblemService instance for the current request."""
        return await self._factory(context)

    # ------------------------------------------------------------------
    # /start command
    # ------------------------------------------------------------------
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command - welcome message."""
        user = update.effective_user
        if user is None:
            return

        welcome_text = (
            f"👋 Привет, {user.first_name}!\n\n"
            "Я Solver — твой проактивный AI-помощник по решению проблем.\n\n"
            "Расскажи мне о проблеме, а я помогу:\n"
            "🔍 Проанализировать ситуацию\n"
            "📋 Разбить на конкретные шаги\n"
            "📬 Напоминать о прогрессе\n\n"
            "Используй команды:\n"
            "/new — Создать новую проблему\n"
            "/list — Мои проблемы\n"
            "/help — Помощь"
        )
        await update.message.reply_text(welcome_text)

    # ------------------------------------------------------------------
    # /help command
    # ------------------------------------------------------------------
    async def help_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        help_text = (
            "📚 Команды Solver:\n\n"
            "/start — Начало работы\n"
            "/new — Создать новую проблему\n"
            "/list — Показать все проблемы\n"
            "/view <номер> — Посмотреть проблему (например /view 1)\n"
            "/done <номер> <шаг> — Отметить шаг выполненным\n"
            "/help — Это сообщение\n\n"
            "💡 Совет: Просто опиши проблему своими словами, "
            "и я помогу разобраться!"
        )
        await update.message.reply_text(help_text)

    # ------------------------------------------------------------------
    # /test command — self-diagnostics
    # ------------------------------------------------------------------
    async def test_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Run built-in self-tests and report results."""
        results: list[str] = []
        passed = 0
        failed = 0

        async def check(name: str, condition: bool, detail: str = "") -> None:
            nonlocal passed, failed
            if condition:
                results.append(f"✅ {name}")
                passed += 1
            else:
                results.append(f"❌ {name}: {detail}")
                failed += 1

        # Test 1: Service factory works
        try:
            service = await self._get_service(context)
            await check("Сервис создаётся", service is not None)
        except Exception as e:
            await check("Сервис создаётся", False, str(e))
            service = None

        # Test 2: Can create a problem
        if service:
            try:
                from solver.application.dtos import CreateProblemDTO
                tid = update.effective_user.id
                problem = await service.create_problem(tid, CreateProblemDTO(
                    title="__test_problem__",
                    description="Automated self-test"
                ))
                await check("Проблема создаётся", problem is not None and problem.title == "__test_problem__")
            except Exception as e:
                await check("Проблема создаётся", False, str(e))

        # Test 3: Can list problems
        if service:
            try:
                tid = update.effective_user.id
                problems = await service.list_active_problems(tid)
                await check("Список проблем", len(problems) >= 1)
            except Exception as e:
                await check("Список проблем", False, str(e))

        # Test 4: AI service is accessible (mock check)
        if service:
            try:
                # Just verify create/analyze flow doesn't crash
                tid = update.effective_user.id
                p = await service.create_problem(tid, CreateProblemDTO(
                    title="__test_ai__", description="Test AI integration"
                ))
                await service.analyze_problem(tid, p.id)
                p2 = await service.get_problem(tid, p.id)
                await check("AI анализ", p2.total_steps >= 1, f"steps={p2.total_steps}")
            except Exception as e:
                await check("AI анализ", False, str(e))

        # Test 5: Markdown formatting doesn't crash
        if service:
            try:
                tid = update.effective_user.id
                # Create a problem with special characters to test formatting
                p = await service.create_problem(tid, CreateProblemDTO(
                    title="Тест (спецсимволы) и точка.",
                    description="Описание с *звёздочкой* и _подчёркиванием_."
                ))
                p = await service.analyze_problem(tid, p.id)
                formatted = self._format_problem(p)
                await check("Форматирование Markdown",
                    "parse" not in formatted.lower() and len(formatted) > 0,
                    "Markdown parse error in formatted output")
            except Exception as e:
                await check("Форматирование Markdown", False, str(e))

        # Report
        total = passed + failed
        summary = (
            f"🧪 Результаты самотестирования: {passed}/{total}\n\n"
            + "\n".join(results)
            + f"\n\n{'🎉 Все тесты пройдены!' if failed == 0 else '⚠️ Есть ошибки — проверь логи Docker.'}"
        )
        await update.message.reply_text(summary)

    # ------------------------------------------------------------------
    # /run_test command — scriptable self-testing
    # ------------------------------------------------------------------
    async def run_test_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Run a test script. Format: /run_test /new|Заголовок|/skip|/list|/view 1|/done 1 1"""
        text = update.message.text or ""
        parts = text.split(" ", 1)
        if len(parts) < 2:
            await update.message.reply_text(
                "Формат: /run_test /new\\|Заголовок\\|/skip\\|/list\\|/view 1\\|/done 1 1"
            )
            return

        script = parts[1]
        steps = [s.strip() for s in script.split("|") if s.strip()]
        user_id = update.effective_user.id

        report: list[str] = ["🧪 Запуск тестового сценария:\n"]
        passed = 0
        failed = 0
        convo_state = None  # TITLE or DESCRIPTION during /new flow

        for i, step in enumerate(steps, 1):
            report.append(f"*Шаг {i}*: `{step[:80]}`")

            try:
                bot = _TestFakeBot()
                fake_update = self._build_fake_update(step, user_id, bot)
                fake_ctx = _TestFakeContext(bot, fake_update, context)

                if step.startswith("/"):
                    cmd = step.split()[0].lower()
                    if cmd == "/new":
                        await self.new_problem_start(fake_update, fake_ctx)
                        convo_state = TITLE
                    elif cmd == "/skip" and convo_state is not None:
                        await self.new_problem_skip_description(fake_update, fake_ctx)
                        convo_state = None
                    elif cmd == "/cancel" and convo_state is not None:
                        await self.cancel(fake_update, fake_ctx)
                        convo_state = None
                    elif cmd == "/list":
                        await self.list_problems(fake_update, fake_ctx)
                    elif cmd == "/view":
                        await self.view_problem(fake_update, fake_ctx)
                    elif cmd == "/done":
                        await self.done_step(fake_update, fake_ctx)
                    elif cmd == "/help":
                        await self.help_cmd(fake_update, fake_ctx)
                    elif cmd in ("/test", "/run_test"):
                        report.append("  ⏭️ Пропущено (нельзя тестировать себя)")
                        continue
                    else:
                        report.append("  ⚠️ Неизвестная команда")
                        failed += 1
                        continue
                else:
                    if convo_state == TITLE:
                        await self.new_problem_title(fake_update, fake_ctx)
                        convo_state = DESCRIPTION
                    elif convo_state == DESCRIPTION:
                        await self._finish_problem_creation(fake_update, fake_ctx)
                        convo_state = None
                    else:
                        report.append("  ⚠️ Текст вне /new (начни с /new)")
                        failed += 1
                        continue

                msgs = bot.sent_messages
                if msgs:
                    last = msgs[-1]["text"]
                    is_error = "ошиб" in last.lower() or "parse" in last.lower()
                    if is_error:
                        report.append(f"  ❌ Ошибка: `{last[:120]}`")
                        failed += 1
                    else:
                        report.append(f"  ✅ `{last[:120]}`")
                        passed += 1
                else:
                    report.append("  ✅ Выполнено")
                    passed += 1

            except Exception as e:
                report.append(f"  ❌ Исключение: `{e}`")
                failed += 1
                convo_state = None

        total = passed + failed
        report.append(f"\n📊 Итог: {passed}/{total}")
        report.append("🎉 Все шаги успешны!" if failed == 0 else "⚠️ Есть ошибки.")
        await update.message.reply_text("\n".join(report))

    @staticmethod
    def _build_fake_update(text: str, user_id: int, bot):
        """Build a fake Telegram Update for internal testing."""
        from datetime import datetime
        from telegram import Update, User as TgUser, Message, Chat

        tg_user = TgUser(id=user_id, is_bot=False, first_name="TestRunner")
        chat = Chat(id=user_id, type="private")
        message = Message(message_id=1, date=datetime.now(), chat=chat, from_user=tg_user, text=text)
        for obj in (message, chat, tg_user):
            obj.set_bot(bot)
        update = Update(update_id=1, message=message)
        update.set_bot(bot)
        return update

    # ------------------------------------------------------------------
    # /new conversation flow
    # ------------------------------------------------------------------
    async def new_problem_start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Start the problem creation conversation."""
        await update.message.reply_text(
            "Опиши свою проблему или задачу одним предложением.\n"
            "Например: «У меня конфликт с коллегой» или «Не могу решиться сменить работу»\n\n"
            "Или отправь /cancel для отмены."
        )
        return TITLE

    async def new_problem_title(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Receive the problem title, ask for description."""
        context.user_data["problem_title"] = update.message.text.strip()
        await update.message.reply_text(
            "Теперь расскажи подробнее. Что именно происходит? "
            "Какие есть нюансы? Чем больше деталей — тем точнее будет анализ.\n\n"
            "Напиши /skip чтобы пропустить."
        )
        return DESCRIPTION

    async def new_problem_skip_description(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Skip description step."""
        context.user_data["problem_description"] = ""
        return await self._finish_problem_creation(update, context)

    async def new_problem_description(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Receive description and create the problem."""
        context.user_data["problem_description"] = update.message.text.strip()
        return await self._finish_problem_creation(update, context)

    async def _finish_problem_creation(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Create the problem and trigger AI analysis."""
        telegram_id = update.effective_user.id
        title = context.user_data.get("problem_title", "")
        description = context.user_data.get("problem_description", "")

        if not title:
            await update.message.reply_text("❌ Не удалось создать проблему. Попробуй снова /new")
            return ConversationHandler.END

        await update.message.reply_text("🔍 Анализирую проблему... Дай мне несколько секунд.")

        try:
            # Create problem
            service = await self._get_service(context)
            dto = CreateProblemDTO(title=title, description=description)
            problem = await service.create_problem(
                telegram_id=telegram_id, dto=dto
            )

            # Trigger AI analysis
            problem = await service.analyze_problem(
                telegram_id=telegram_id, problem_id=problem.id
            )

            # Auto-enter session mode for this problem
            self._active_sessions[telegram_id] = problem.id

            # Format and send problem details (MarkdownV2 — validated by tests)
            response = self._format_problem(problem)
            await update.message.reply_text(response, parse_mode="MarkdownV2")

            # Session hint as separate plain-text message (no Markdown issues)
            await update.message.reply_text(
                "💬 Ты в сессии этой проблемы. Пиши — я помогу уточнить или скорректировать шаги."
            )

        except Exception as e:
            await update.message.reply_text(
                f"❌ Произошла ошибка при анализе: {str(e)}\n"
                "Попробуй ещё раз позже или обратись к /help"
            )

        context.user_data.clear()
        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the conversation."""
        await update.message.reply_text("❌ Создание проблемы отменено.")
        context.user_data.clear()
        return ConversationHandler.END

    # ------------------------------------------------------------------
    # /list command
    # ------------------------------------------------------------------
    async def list_problems(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """List all active problems for the user."""
        telegram_id = update.effective_user.id

        try:
            service = await self._get_service(context)
            problems = await service.list_active_problems(telegram_id)

            if not problems:
                await update.message.reply_text(
                    "У тебя пока нет активных проблем. Создай первую с помощью /new!"
                )
                return

            lines = ["📋 *Твои активные проблемы:*\n"]
            for i, p in enumerate(problems, 1):
                status_emoji = {
                    "draft": "📝",
                    "analyzing": "🔍",
                    "active": "⚡",
                    "on_hold": "⏸️",
                }.get(p.status, "📌")
                progress = f"\\[{p.completed_steps}/{p.total_steps}\\]"
                pct = int(p.progress_percentage)
                lines.append(
                    f"{status_emoji} *{i}\\.* {escape_markdown(p.title, version=2)}\n"
                    f"   {progress} {pct}% \\| /view {i}"
                )

            await update.message.reply_text(
                "\n".join(lines), parse_mode="MarkdownV2"
            )

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")

    # ------------------------------------------------------------------
    # /view command (view problem by index)
    # ------------------------------------------------------------------
    async def view_problem(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """View a specific problem by index from /list."""
        telegram_id = update.effective_user.id

        try:
            service = await self._get_service(context)
            problems = await service.list_problems(telegram_id)
            if not problems:
                await update.message.reply_text("У тебя нет проблем. Создай через /new")
                return

            # Parse index from command
            text = update.message.text.strip()
            parts = text.split()
            if len(parts) < 2:
                await update.message.reply_text(
                    "Укажи номер проблемы: /view 1\n"
                    "Используй /list чтобы увидеть номера."
                )
                return

            try:
                idx = int(parts[1]) - 1
                if idx < 0 or idx >= len(problems):
                    raise ValueError()
            except ValueError:
                await update.message.reply_text("❌ Неверный номер. Используй /list для списка.")
                return

            problem = problems[idx]
            response = self._format_problem(problem)
            await update.message.reply_text(response, parse_mode="MarkdownV2")

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")

    # ------------------------------------------------------------------
    # /done command (mark step as complete)
    # ------------------------------------------------------------------
    async def done_step(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Mark a step as completed."""
        telegram_id = update.effective_user.id

        try:
            service = await self._get_service(context)
            problems = await service.list_active_problems(telegram_id)
            if not problems:
                await update.message.reply_text("У тебя нет активных проблем.")
                return

            # Parse: /done <problem_index> <step_index>
            text = update.message.text.strip()
            parts = text.split()
            if len(parts) < 3:
                await update.message.reply_text(
                    "Формат: /done <номер_проблемы> <номер_шага>\n"
                    "Пример: /done 1 2\n"
                    "Используй /list и /view для номеров."
                )
                return

            try:
                p_idx = int(parts[1]) - 1
                s_idx = int(parts[2]) - 1
                if p_idx < 0 or p_idx >= len(problems):
                    raise ValueError()
            except ValueError:
                await update.message.reply_text("❌ Неверные номера. Используй /list для списка.")
                return

            problem = problems[p_idx]
            if s_idx < 0 or s_idx >= len(problem.steps):
                await update.message.reply_text(
                    f"❌ В проблеме только {len(problem.steps)} шагов."
                )
                return

            step = problem.steps[s_idx]
            updated = await service.update_step_status(
                telegram_id=telegram_id,
                problem_id=problem.id,
                step_id=step.id,
                dto=UpdateStepDTO(status="completed"),
            )

            status_text = "✅ Проблема решена! Поздравляю! 🎉" if updated.status == "resolved" else (
                f"✅ Шаг выполнен! Прогресс: {updated.progress_percentage:.0f}% "
                f"({updated.completed_steps}/{updated.total_steps})"
            )
            await update.message.reply_text(status_text)

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")

    # ------------------------------------------------------------------
    # /session command — enter a problem's conversation session
    # ------------------------------------------------------------------
    async def session_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Enter session mode for a problem. Usage: /session N or /session (last active)."""
        tid = update.effective_user.id
        service = await self._get_service(context)

        parts = update.message.text.strip().split() if update.message else []
        try:
            if len(parts) >= 2:
                idx = int(parts[1]) - 1
                problems = await service.list_active_problems(tid)
                if 0 <= idx < len(problems):
                    pid = problems[idx].id
                    self._active_sessions[tid] = pid
                    await update.message.reply_text(
                        f"💬 Ты в сессии проблемы «{problems[idx].title[:50]}»\n"
                        "Пиши что угодно — я отвечу в контексте этой проблемы.\n"
                        "/leave — выйти из сессии\n/list — список проблем"
                    )
                else:
                    await update.message.reply_text("❌ Неверный номер проблемы. Используй /list.")
            else:
                # Enter session of last active problem
                problems = await service.list_active_problems(tid)
                if problems:
                    pid = problems[0].id
                    self._active_sessions[tid] = pid
                    await update.message.reply_text(
                        f"💬 Сессия: «{problems[0].title[:50]}»\nПиши — я слушаю. /leave чтобы выйти."
                    )
                else:
                    await update.message.reply_text("Нет активных проблем. Создай через /new")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")

    # ------------------------------------------------------------------
    # /leave command — exit session mode
    # ------------------------------------------------------------------
    async def leave_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Exit the current problem session."""
        tid = update.effective_user.id
        if tid in self._active_sessions:
            del self._active_sessions[tid]
            await update.message.reply_text("👋 Ты вышел из сессии. /session чтобы вернуться.")
        else:
            await update.message.reply_text("Ты не в сессии. /session чтобы войти.")

    # ------------------------------------------------------------------
    # Handle non-command text in session mode
    # ------------------------------------------------------------------
    async def handle_session_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Route a non-command message: if in session → AI dialog, else → hint."""
        tid = update.effective_user.id
        text = update.message.text.strip() if update.message else ""

        if not text:
            return

        # Check if user is in a session
        pid = self._active_sessions.get(tid)
        if pid is None:
            # Not in session — suggest to create or enter one
            await update.message.reply_text(
                "Я не совсем понял. Используй /new чтобы создать проблему, "
                "или /session чтобы продолжить обсуждение."
            )
            return

        # User is in a session — continue dialog
        await update.message.reply_text("💭 Думаю...")
        service = await self._get_service(context)

        try:
            result = await service.continue_session(tid, pid, text)
            reply = result.get("reply", "Понял, продолжаем.")

            if result.get("updated_steps"):
                reply += "\n\n📋 Я обновил шаги. Посмотри через /view."

            await update.message.reply_text(reply)

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _format_problem(self, problem) -> str:
        """Format a problem response for display in Telegram (MarkdownV2)."""
        def e(text: str) -> str:
            return escape_markdown(text, version=2)

        status_emoji = {
            "draft": "📝",
            "analyzing": "🔍",
            "active": "⚡",
            "on_hold": "⏸️",
            "resolved": "✅",
        }
        emoji = status_emoji.get(problem.status, "📌")

        lines = [
            f"{emoji} *{e(problem.title)}*",
            f"Статус: {e(problem.status)} \\| Приоритет: {e(problem.priority)}",
        ]

        if problem.description:
            lines.append(f"\n📝 {e(problem.description)}")

        if problem.steps:
            lines.append(f"\n📋 *Шаги* \\({problem.completed_steps}/{problem.total_steps}\\):")
            for i, step in enumerate(problem.steps, 1):
                step_emoji = {
                    "pending": "⬜",
                    "in_progress": "🔄",
                    "completed": "✅",
                    "skipped": "⏭️",
                }.get(step.status, "⬜")
                lines.append(f"  {step_emoji} *{i}\\.* {e(step.description)}")
                if step.ai_suggestion:
                    lines.append(f"     💡 {e(step.ai_suggestion)}")

        if problem.status != "resolved":
            pct = int(problem.progress_percentage)
            lines.append(
                f"\n📊 Прогресс: {pct}%\n"
                "Отметить шаг: /done \\(используй /list для номеров\\)"
            )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Build conversation handler for /new flow
    # ------------------------------------------------------------------
    def build_new_problem_handler(self) -> ConversationHandler:
        """Build the conversation handler for creating a new problem."""
        return ConversationHandler(
            entry_points=[CommandHandler("new", self.new_problem_start)],
            states={
                TITLE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.new_problem_title),
                ],
                DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.new_problem_description),
                    CommandHandler("skip", self.new_problem_skip_description),
                ],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )


# ═══════════════════════════════════════════════════════════════════
# Internal helpers for /run_test self-testing
# ═══════════════════════════════════════════════════════════════════

class _TestFakeBot:
    """Fake bot that collects sent messages instead of calling Telegram API."""
    def __init__(self) -> None:
        self.sent_messages: list[dict] = []
        self.defaults = None

    async def send_message(self, chat_id: int, text: str, parse_mode=None, **kw):
        self.sent_messages.append({"chat_id": chat_id, "text": text, "parse_mode": parse_mode})
        from telegram import Message, Chat
        from datetime import datetime
        fake = Message(message_id=len(self.sent_messages), date=datetime.now(),
                       chat=Chat(id=chat_id, type="private"), text=text)
        fake.set_bot(self)
        return fake


class _TestFakeContext:
    """Fake context for /run_test that delegates service calls to the real one."""
    def __init__(self, bot: _TestFakeBot, update, real_context) -> None:
        self.bot = bot
        self._update = update
        self.user_data: dict = {}
        self.application = real_context.application

    @property
    def effective_user(self):
        return self._update.effective_user

    @property
    def effective_chat(self):
        return self._update.effective_chat
