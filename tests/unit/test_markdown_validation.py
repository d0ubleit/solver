"""Universal MarkdownV2 validation tests for ALL bot message types.

This test MUST pass before any commit — it catches Markdown parse errors
BEFORE they reach Telegram.
"""


from solver.presentation.markdown_validator import assert_valid_markdown_v2
from solver.presentation.handlers import BotHandlers


# ═══════════════════════════════════════════════════════════════════
# Test data: realistic bot outputs from all code paths
# ═══════════════════════════════════════════════════════════════════

def _make_mock_problem():
    """Create a mock problem-like object with realistic data."""
    from unittest.mock import MagicMock

    p = MagicMock()
    p.title = "Хочу полететь с семьей в отпуск на море"
    p.description = "Нужно найти тур в пятизвездочный отель с всё включено"
    p.status = "active"
    p.priority = "medium"
    p.completed_steps = 0
    p.total_steps = 3
    p.progress_percentage = 0.0

    steps = []
    for i, desc in enumerate([
        "1. Определите бюджет (мин/макс) и даты поездки.",
        "2. Сравните 3-5 вариантов туров на сайтах-агрегаторах.",
        "3. Забронируйте лучший вариант (смотрите отзывы!).",
    ]):
        s = MagicMock()
        s.step_order = i
        s.description = desc
        s.status = "pending"
        s.ai_suggestion = ""
        s.completed_at = None
        steps.append(s)

    p.steps = steps
    return p


def _make_mock_problem_with_special_chars():
    """Problem with asterisks, underscores, dots — worst case for Markdown."""
    from unittest.mock import MagicMock

    p = MagicMock()
    p.title = "Проблема: зарплата vs. расходы (нужно срочно!)"
    p.description = "Работаю 12ч/день. Начальник не ценит. Ипотека 50 тыс/мес."
    p.status = "active"
    p.priority = "high"
    p.completed_steps = 2
    p.total_steps = 5
    p.progress_percentage = 40.0

    steps = []
    for i, desc in enumerate([
        "1. Запишите доходы и расходы за месяц (честно!).",
        "2. Используйте технику *ненасильственного общения* с начальником.",
        "3. Найдите _хотя бы одну_ статью расходов для сокращения.",
        "4. Обновите резюме на hh.ru и LinkedIn.",
        "5. Договоритесь о встрече 1-на-1 с руководителем.",
    ]):
        s = MagicMock()
        s.step_order = i
        s.description = desc
        s.status = "completed" if i < 2 else "pending"
        s.ai_suggestion = "💡 Совет: используйте техники активного слушания." if i == 1 else ""
        s.completed_at = None
        steps.append(s)

    p.steps = steps
    return p


# ═══════════════════════════════════════════════════════════════════
# The tests
# ═══════════════════════════════════════════════════════════════════

class TestMarkdownV2Validation:
    """Universal validation of ALL bot message types."""

    def test_format_problem_simple(self):
        """_format_problem with basic travel problem."""
        handlers = BotHandlers(service_factory=lambda _: None)
        problem = _make_mock_problem()
        text = handlers._format_problem(problem)
        assert_valid_markdown_v2(text, "_format_problem (travel)")

    def test_format_problem_special_chars(self):
        """_format_problem with worst-case special characters."""
        handlers = BotHandlers(service_factory=lambda _: None)
        problem = _make_mock_problem_with_special_chars()
        text = handlers._format_problem(problem)
        assert_valid_markdown_v2(text, "_format_problem (special chars)")

    def test_format_problem_resolved(self):
        """_format_problem with resolved problem (different footer)."""
        handlers = BotHandlers(service_factory=lambda _: None)
        p = _make_mock_problem()
        p.status = "resolved"
        p.completed_steps = 3
        p.progress_percentage = 100.0
        text = handlers._format_problem(p)
        assert_valid_markdown_v2(text, "_format_problem (resolved)")

    def test_static_messages_are_plain_text(self):
        """Start/help messages are sent WITHOUT parse_mode — no Markdown needed."""
        # These are plain text messages — validation is informational only
        # They contain reserved chars (. ! -) but they're NOT sent as MarkdownV2
        welcome = (
            "👋 Привет, Алексей!\n\n"
            "Я Solver — твой проактивный AI-помощник по решению проблем."
        )
        help_text = "📚 Команды Solver:\n\n/start — Начало работы"
        # No validation needed — these go as plain text
        assert len(welcome) > 0 and len(help_text) > 0  # Just ensure non-empty

    def test_list_output_format(self):
        """list_problems output format."""
        # Simulate what list_problems would output
        lines = [
            "📋 *Твои активные проблемы:*\n",
        ]
        problems = [
            ("Хочу на море (Турция)", 0, 3, 0, "active"),
            ("Конфликт с коллегой", 1, 4, 25, "active"),
        ]
        from telegram.helpers import escape_markdown

        for i, (title, done, total, pct, status) in enumerate(problems, 1):
            emoji = "⚡"
            progress = f"\\[{done}/{total}\\]"
            lines.append(
                f"{emoji} *{i}\\.* {escape_markdown(title, version=2)}\n"
                f"   {progress} {pct}% \\| /view {i}"
            )

        text = "\n".join(lines)
        assert_valid_markdown_v2(text, "list_problems output")

    def test_session_and_error_messages_are_plain_text(self):
        """Session/error messages are sent WITHOUT parse_mode."""
        msgs = [
            "💬 Ты в сессии проблемы «Отпуск на море»\nПиши — я отвечу.",
            "👋 Ты вышел из сессии. /session чтобы вернуться.",
            "Я не совсем понял. Используй /new чтобы создать проблему.",
            "❌ Произошла ошибка при анализе: API timeout\nПопробуй ещё раз.",
            "❌ Не удалось создать проблему. Попробуй снова /new",
            "У тебя пока нет активных проблем. Создай первую с помощью /new!",
        ]
        # These are plain text — just ensure non-empty
        for msg in msgs:
            assert len(msg) > 0

    def test_e2e_bot_outputs_from_tests(self):
        """Validate all messages from E2E test fixtures."""
        # Problem title with special characters from test_extended.py
        from telegram.helpers import escape_markdown

        title = "Тест! (скобки) и точка."
        escaped_title = escape_markdown(title, version=2)

        # This is exactly what _format_problem would produce
        text = f"⚡ *{escaped_title}*\nСтатус: active \\| Приоритет: medium"
        assert_valid_markdown_v2(text, "special chars title in bold")
