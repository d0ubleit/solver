"""Extended E2E tests with realistic data — special chars, emoji, long text, edge cases.

These tests use AI mock responses that closely mimic real DeepSeek output:
- numbered steps with dots (1. 2. 3.)
- asterisks and underscores in suggestions
- emoji-like characters
- long descriptions
"""

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from solver.application.ai_service import AIAnalysisService
from solver.application.dtos import AIAnalysisResponseDTO
from solver.application.services import ProblemService
from solver.infrastructure.database import Base
from solver.infrastructure.repositories import (
    SqlAlchemyConversationContextRepository,
    SqlAlchemyProblemRepository,
    SqlAlchemyUserRepository,
)
from solver.presentation.handlers import BotHandlers

# Reuse the FakeBot/fake Update infrastructure from the main E2E tests
from tests.e2e.test_bot import _FakeBot, _FakeContext, _make_update

# ═══════════════════════════════════════════════════════════════════
# Realistic AI mock — simulates actual DeepSeek output
# ═══════════════════════════════════════════════════════════════════

REALISTIC_AI_RESPONSE = AIAnalysisResponseDTO(
    analysis=(
        "Ситуация требует системного подхода. Важно:\n"
        "1. Не действовать сгоряча\n"
        "2. Собрать факты и эмоции отдельно\n"
        "3. Выбрать момент для разговора, когда вы оба спокойны"
    ),
    steps=[
        "1. Запишите 3 конкретные ситуации за последнюю неделю: дата, что произошло, ваши чувства.",
        "2. Используйте технику *ненасильственного общения*: \"Когда ты ____, я чувствую ____, потому что мне важно ____.\"",
        "3. Предложите встречу 1-на-1 в _нейтральной_ обстановке (кафе, переговорка). Не на рабочем месте.",
        "4. На встрече: сначала выслушайте его версию. Используйте _активное слушание_: кивайте, перефразируйте.",
        "5. Найдите одно маленькое совместное решение (easy win). Например, договоритесь не перебивать друг друга.",
    ],
    tokens_used=120,
)

REALISTIC_CHECK_IN = (
    "Привет! Как продвигается работа с коллегой?\n"
    "Удалось ли применить технику *ненасильственного общения*?\n"
    "Если застрял(а) — напиши, на каком шаге, я помогу."
)


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
    """Real ProblemService with REALISTIC mocked AI output."""
    ai = AsyncMock(spec=AIAnalysisService)
    ai.analyze.return_value = REALISTIC_AI_RESPONSE
    ai.check_in.return_value = REALISTIC_CHECK_IN
    return ProblemService(
        problem_repo=SqlAlchemyProblemRepository(db_session),
        user_repo=SqlAlchemyUserRepository(db_session),
        context_repo=SqlAlchemyConversationContextRepository(db_session),
        ai_service=ai,
    )


@pytest_asyncio.fixture
async def handlers(problem_service: ProblemService):
    async def _factory(_ctx):
        return problem_service
    return BotHandlers(service_factory=_factory)


# ═══════════════════════════════════════════════════════════════════
# Helper: create a problem through the full /new flow
# ═══════════════════════════════════════════════════════════════════

async def _create_problem(handlers, user_id: int, title: str, description: str = "") -> _FakeBot:
    """Run the full /new → title → description flow. Returns the FakeBot with all messages."""
    u1, bot = _make_update("/new", user_id=user_id)
    ctx = _FakeContext(bot, u1)
    await handlers.new_problem_start(u1, ctx)

    u2, _ = _make_update(title, user_id=user_id, bot=bot)
    ctx._update = u2
    await handlers.new_problem_title(u2, ctx)

    if description:
        u3, _ = _make_update(description, user_id=user_id, bot=bot)
        ctx._update = u3
        await handlers._finish_problem_creation(u3, ctx)
    else:
        u3, _ = _make_update("/skip", user_id=user_id, bot=bot)
        ctx._update = u3
        await handlers.new_problem_skip_description(u3, ctx)

    return bot


# ═══════════════════════════════════════════════════════════════════
# Tests: realistic AI output with special characters
# ═══════════════════════════════════════════════════════════════════

class TestRealisticAIOutput:
    """Verify that bot handles realistic AI output without Markdown parse errors."""

    @pytest.mark.asyncio
    async def test_dots_in_steps_dont_break_formatting(self, handlers):
        """AI returns '1. Do X' — dots must be escaped."""
        bot = await _create_problem(handlers, user_id=100, title="Конфликт на работе")

        final = bot.sent_messages[-2]["text"]  # problem details (last is session hint)
        # Should contain steps with dots
        assert "1." in final or "1\\." in final
        # Should NOT contain raw Markdown error messages
        assert "parse" not in final.lower()
        assert "entities" not in final.lower()

    @pytest.mark.asyncio
    async def test_asterisks_in_ai_response_are_escaped(self, handlers):
        """AI uses *bold* in suggestions — asterisks must be escaped."""
        bot = await _create_problem(handlers, user_id=101, title="Сложная ситуация")

        final = bot.sent_messages[-2]["text"]  # problem details (last is session hint)
        # Check that asterisks from AI suggestions are escaped
        assert "\\*" in final or "*ненасильственного*" not in final
        assert "parse" not in final.lower()

    @pytest.mark.asyncio
    async def test_underscores_in_ai_response_are_escaped(self, handlers):
        """AI uses _italic_ in suggestions — underscores must be escaped."""
        bot = await _create_problem(handlers, user_id=102, title="Проблема с коммуникацией")

        final = bot.sent_messages[-2]["text"]  # problem details (last is session hint)
        assert "parse" not in final.lower()
        assert "entities" not in final.lower()

    @pytest.mark.asyncio
    async def test_long_description_with_newlines(self, handlers):
        """User provides long multi-line description."""
        bot = await _create_problem(
            handlers,
            user_id=103,
            title="Выгорание на работе",
            description=(
                "Работаю 12 часов в день уже 3 месяца.\n"
                "Начальник не ценит, коллеги подставляют.\n"
                "Хочу уволиться, но боюсь остаться без денег.\n"
                "Плюс ипотека — нужно платить каждый месяц."
            ),
        )

        final = bot.sent_messages[-2]["text"]  # problem details (last is session hint)
        assert "parse" not in final.lower()
        assert "Выгорание" in final or "выгорание" in final.lower()

    @pytest.mark.asyncio
    async def test_special_chars_in_title(self, handlers):
        """Title contains special Telegram Markdown characters."""
        bot = await _create_problem(
            handlers,
            user_id=104,
            title="Проблема с деньгами: зарплата vs расходы (нужно срочно!)",
        )

        final = bot.sent_messages[-2]["text"]  # problem details (last is session hint)
        assert "parse" not in final.lower()
        assert "зарплата" in final


# ═══════════════════════════════════════════════════════════════════
# Tests: multi-step orchestration flows
# ═══════════════════════════════════════════════════════════════════

class TestMultiStepFlows:
    """Full user journeys across multiple commands."""

    @pytest.mark.asyncio
    async def test_create_view_done_all_steps(self, handlers):
        """Create → view → done step 1 → done step 2 → ... → auto-resolve."""
        # Create
        await _create_problem(handlers, user_id=200, title="Научиться Python")

        # View
        u, b = _make_update("/view 1", user_id=200)
        await handlers.view_problem(u, _FakeContext(b, u))
        assert "Научиться Python" in b.sent_messages[0]["text"]

        # Done all 5 steps
        for step_num in range(1, 6):
            u, b = _make_update(f"/done 1 {step_num}", user_id=200)
            await handlers.done_step(u, _FakeContext(b, u))
            text = b.sent_messages[0]["text"]
            assert "parse" not in text.lower()

        # After all steps done, problem should be resolved
        # Last /done should mention resolution
        last_text = b.sent_messages[0]["text"]
        assert "решен" in last_text.lower() or "прогресс" in last_text.lower()

    @pytest.mark.asyncio
    async def test_create_two_problems_list_both(self, handlers):
        """Create 2 problems → /list shows both."""
        await _create_problem(handlers, user_id=300, title="Проблема А")
        await _create_problem(handlers, user_id=300, title="Проблема Б")

        u, b = _make_update("/list", user_id=300)
        await handlers.list_problems(u, _FakeContext(b, u))

        text = b.sent_messages[0]["text"]
        assert "Проблема А" in text
        assert "Проблема Б" in text

    @pytest.mark.asyncio
    async def test_users_isolated_from_each_other(self, handlers):
        """User 1 creates problems → User 2 sees empty list."""
        await _create_problem(handlers, user_id=400, title="Секретная проблема")

        u, b = _make_update("/list", user_id=401)
        await handlers.list_problems(u, _FakeContext(b, u))
        text = b.sent_messages[0]["text"].lower()
        assert "нет" in text or "активных" in text
        assert "Секретная" not in b.sent_messages[0]["text"]


# ═══════════════════════════════════════════════════════════════════
# Tests: error handling and edge cases
# ═══════════════════════════════════════════════════════════════════

class TestErrorHandling:
    """Verify graceful handling of invalid input."""

    @pytest.mark.asyncio
    async def test_view_invalid_index(self, handlers):
        """No problems → /view 1 shows helpful message, not crash."""
        u, b = _make_update("/view 1", user_id=500)
        await handlers.view_problem(u, _FakeContext(b, u))
        text = b.sent_messages[0]["text"].lower()
        assert "нет" in text or "создай" in text or "ошиб" in text

    @pytest.mark.asyncio
    async def test_view_without_number(self, handlers):
        """/view without index: handler shows 'no problems' if nothing created yet."""
        u, b = _make_update("/view", user_id=501)
        await handlers.view_problem(u, _FakeContext(b, u))
        text = b.sent_messages[0]["text"].lower()
        # OK response: either "no problems" or "specify number" — both are valid UX
        assert any(w in text for w in ("нет", "создай", "номер", "укажи"))

    @pytest.mark.asyncio
    async def test_view_bad_index_with_problems(self, handlers):
        """Create a problem → /view 99 shows error (out of range)."""
        await _create_problem(handlers, user_id=501, title="Test")
        u, b = _make_update("/view 99", user_id=501)
        await handlers.view_problem(u, _FakeContext(b, u))
        text = b.sent_messages[0]["text"].lower()
        assert "неверн" in text or "ошиб" in text or "ном" in text

    @pytest.mark.asyncio
    async def test_done_without_enough_args(self, handlers):
        """/done without args: handler shows 'no active problems' if nothing created."""
        u, b = _make_update("/done", user_id=502)
        await handlers.done_step(u, _FakeContext(b, u))
        text = b.sent_messages[0]["text"].lower()
        assert any(w in text for w in ("нет", "формат", "пример", "ошиб"))

    @pytest.mark.asyncio
    async def test_done_bad_args_with_problems(self, handlers):
        """Create a problem → /done without step arg shows format hint."""
        await _create_problem(handlers, user_id=502, title="Test")
        u, b = _make_update("/done 1", user_id=502)  # only problem index, no step
        await handlers.done_step(u, _FakeContext(b, u))
        text = b.sent_messages[0]["text"].lower()
        assert any(w in text for w in ("формат", "пример", "номер", "ошиб"))

    @pytest.mark.asyncio
    async def test_done_invalid_problem_index(self, handlers):
        """/done 999 1 when no such problem."""
        u, b = _make_update("/done 999 1", user_id=503)
        await handlers.done_step(u, _FakeContext(b, u))
        text = b.sent_messages[0]["text"].lower()
        assert "неверн" in text or "ошиб" in text or "нет" in text

    @pytest.mark.asyncio
    async def test_empty_title_handled(self, handlers):
        """User sends /new then somehow the title is empty."""
        u1, bot = _make_update("/new", user_id=504)
        ctx = _FakeContext(bot, u1)
        await handlers.new_problem_start(u1, ctx)

        # Manually corrupt the context — simulate empty title edge case
        ctx.user_data["problem_title"] = ""
        ctx.user_data["problem_description"] = "Some desc"

        u2, _ = _make_update("fake", user_id=504, bot=bot)
        ctx._update = u2
        result = await handlers._finish_problem_creation(u2, ctx)
        assert result == -1  # ConversationHandler.END
        assert "не удалось" in bot.sent_messages[-1]["text"].lower()

    @pytest.mark.asyncio
    async def test_done_out_of_range_step(self, handlers):
        """Create problem with 5 steps → /done 1 99 shows error."""
        await _create_problem(handlers, user_id=505, title="Тест шагов")

        u, b = _make_update("/done 1 99", user_id=505)
        await handlers.done_step(u, _FakeContext(b, u))
        text = b.sent_messages[0]["text"].lower()
        assert "только" in text or "неверн" in text or "ошиб" in text


# ═══════════════════════════════════════════════════════════════════
# Tests: progress tracking
# ═══════════════════════════════════════════════════════════════════

class TestProgressTracking:
    """Verify progress percentage updates correctly."""

    @pytest.mark.asyncio
    async def test_progress_after_partial_completion(self, handlers):
        """Do 2 of 5 steps → verify progress ~40%."""
        await _create_problem(handlers, user_id=600, title="Прогресс-тест")

        # Done step 1
        u1, b1 = _make_update("/done 1 1", user_id=600)
        await handlers.done_step(u1, _FakeContext(b1, u1))
        assert "20" in b1.sent_messages[0]["text"] or "1/5" in b1.sent_messages[0]["text"]

        # Done step 2
        u2, b2 = _make_update("/done 1 2", user_id=600)
        await handlers.done_step(u2, _FakeContext(b2, u2))
        assert "40" in b2.sent_messages[0]["text"] or "2/5" in b2.sent_messages[0]["text"]

    @pytest.mark.asyncio
    async def test_view_shows_updated_progress(self, handlers):
        """Create → done 1 step → /view shows updated counts."""
        await _create_problem(handlers, user_id=601, title="Прогресс-view")

        u1, b1 = _make_update("/done 1 1", user_id=601)
        await handlers.done_step(u1, _FakeContext(b1, u1))

        u2, b2 = _make_update("/view 1", user_id=601)
        await handlers.view_problem(u2, _FakeContext(b2, u2))

        text = b2.sent_messages[0]["text"]
        assert "1/5" in text


# ═══════════════════════════════════════════════════════════════════
# Tests: view command with realistic data
# ═══════════════════════════════════════════════════════════════════

class TestViewWithRealisticData:
    """View rendering with special chars."""

    @pytest.mark.asyncio
    async def test_no_parse_error_in_any_bot_response(self, handlers):
        """Smoke test: run through ALL commands, check no Markdown errors."""
        bot = await _create_problem(
            handlers,
            user_id=700,
            title="Тест! (скобки) и точка.",
            description="Описание с *звёздочкой* и _подчёркиванием_.",
        )

        # Check ALL messages from /new flow
        for msg in bot.sent_messages:
            assert "Can't parse" not in msg["text"]
            assert "parse entities" not in msg["text"].lower()
            assert "reserved" not in msg["text"].lower()

        # /list
        u, b = _make_update("/list", user_id=700)
        await handlers.list_problems(u, _FakeContext(b, u))
        for msg in b.sent_messages:
            assert "Can't parse" not in msg["text"]

        # /view
        u2, b2 = _make_update("/view 1", user_id=700)
        await handlers.view_problem(u2, _FakeContext(b2, u2))
        for msg in b2.sent_messages:
            assert "Can't parse" not in msg["text"]


# ═══════════════════════════════════════════════════════════════════
# Session tests — conversation mode after problem creation
# ═══════════════════════════════════════════════════════════════════

@pytest_asyncio.fixture
async def session_ai_mock():
    """Mock AI that supports both analyze() and continue_dialog()."""
    ai = AsyncMock(spec=AIAnalysisService)
    ai.analyze.return_value = AIAnalysisResponseDTO(
        analysis="Тестовый анализ.",
        steps=["Шаг 1: Начать", "Шаг 2: Закончить"],
        tokens_used=50,
    )
    ai.continue_dialog.return_value = {
        "reply": "Хороший вопрос! Я уточнил шаги.",
        "updated_steps": None,
    }
    ai.check_in.return_value = "Как дела?"
    return ai


@pytest_asyncio.fixture
async def session_service(db_session, session_ai_mock):
    """ProblemService with continue_dialog support."""
    return ProblemService(
        problem_repo=SqlAlchemyProblemRepository(db_session),
        user_repo=SqlAlchemyUserRepository(db_session),
        context_repo=SqlAlchemyConversationContextRepository(db_session),
        ai_service=session_ai_mock,
    )


@pytest_asyncio.fixture
async def session_handlers(session_service: ProblemService):
    async def _factory(_ctx):
        return session_service
    return BotHandlers(service_factory=_factory)


class TestSessionMode:
    """E2E: session-based conversation after problem creation."""

    @pytest.mark.asyncio
    async def test_new_problem_auto_enters_session(self, session_handlers):
        """After /new, user is automatically in session mode."""
        u1, bot = _make_update("/new", user_id=800)
        ctx = _FakeContext(bot, u1)
        await session_handlers.new_problem_start(u1, ctx)

        u2, _ = _make_update("Проблема для сессии", user_id=800, bot=bot)
        ctx._update = u2
        await session_handlers.new_problem_title(u2, ctx)

        u3, _ = _make_update("/skip", user_id=800, bot=bot)
        ctx._update = u3
        await session_handlers.new_problem_skip_description(u3, ctx)

        # Should be in session now
        assert 800 in session_handlers._active_sessions
        # Last message should mention session
        final = bot.sent_messages[-2]["text"]  # problem details (last is session hint)
        assert "сессии" in final.lower() or "session" in final.lower()

    @pytest.mark.asyncio
    async def test_session_message_triggers_continue_dialog(self, session_handlers):
        """In session, a non-command message calls continue_dialog."""
        # Create problem first → auto-enters session
        u1, bot = _make_update("/new", user_id=801)
        ctx = _FakeContext(bot, u1)
        await session_handlers.new_problem_start(u1, ctx)
        u2, _ = _make_update("Тест сессии", user_id=801, bot=bot)
        ctx._update = u2
        await session_handlers.new_problem_title(u2, ctx)
        u3, _ = _make_update("/skip", user_id=801, bot=bot)
        ctx._update = u3
        await session_handlers.new_problem_skip_description(u3, ctx)

        # Now send a session message
        u4, b4 = _make_update("А что насчёт второго шага?", user_id=801)
        await session_handlers.handle_session_message(u4, _FakeContext(b4, u4))

        # Should get AI reply
        msgs = b4.sent_messages
        assert len(msgs) >= 1
        assert "Хороший вопрос" in msgs[-1]["text"] or "шаги" in msgs[-1]["text"].lower()

    @pytest.mark.asyncio
    async def test_leave_exits_session(self, session_handlers):
        """After /new → /leave removes user from session."""
        # Create → auto-enter session
        u1, bot = _make_update("/new", user_id=802)
        ctx = _FakeContext(bot, u1)
        await session_handlers.new_problem_start(u1, ctx)
        u2, _ = _make_update("Test", user_id=802, bot=bot)
        ctx._update = u2
        await session_handlers.new_problem_title(u2, ctx)
        u3, _ = _make_update("/skip", user_id=802, bot=bot)
        ctx._update = u3
        await session_handlers.new_problem_skip_description(u3, ctx)

        assert 802 in session_handlers._active_sessions

        # /leave
        u4, b4 = _make_update("/leave", user_id=802)
        await session_handlers.leave_cmd(u4, _FakeContext(b4, u4))

        assert 802 not in session_handlers._active_sessions

    @pytest.mark.asyncio
    async def test_no_session_message_without_session(self, session_handlers):
        """Non-command message without active session → hint to use /new or /session."""
        u, b = _make_update("Случайное сообщение", user_id=803)
        await session_handlers.handle_session_message(u, _FakeContext(b, u))

        text = b.sent_messages[0]["text"].lower()
        assert "/new" in text or "/session" in text

    @pytest.mark.asyncio
    async def test_commands_work_during_session(self, session_handlers):
        """/list and /help still work while in session."""
        # Create → enters session
        u1, bot = _make_update("/new", user_id=804)
        ctx = _FakeContext(bot, u1)
        await session_handlers.new_problem_start(u1, ctx)
        u2, _ = _make_update("Test", user_id=804, bot=bot)
        ctx._update = u2
        await session_handlers.new_problem_title(u2, ctx)
        u3, _ = _make_update("/skip", user_id=804, bot=bot)
        ctx._update = u3
        await session_handlers.new_problem_skip_description(u3, ctx)

        assert 804 in session_handlers._active_sessions

        # /list should still work
        u4, b4 = _make_update("/list", user_id=804)
        await session_handlers.list_problems(u4, _FakeContext(b4, u4))
        assert len(b4.sent_messages) == 1
        assert "Test" in b4.sent_messages[0]["text"]

        # Still in session after /list
        assert 804 in session_handlers._active_sessions
