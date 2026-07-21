"""Prompt service — classify, adapt, and manage AI prompt templates."""

from solver.domain.prompts import PromptTemplate
from solver.infrastructure.repositories import SqlAlchemyPromptTemplateRepository

# ═══════════════════════════════════════════════════════════════════
# Seed prompts — built-in templates for common problem categories
# ═══════════════════════════════════════════════════════════════════

SEED_PROMPTS = [
    PromptTemplate(
        category="general",
        title="Универсальный помощник",
        system_prompt="""Ты — проактивный AI-коуч, помогающий людям решать жизненные и рабочие проблемы.
Твоя задача — проанализировать проблему пользователя и предложить конкретный, actionable план действий.

ВАЖНЫЕ ПРАВИЛА:
1. Будь эмпатичным, но конструктивным. Покажи, что ты понимаешь сложность ситуации.
2. Разбей проблему на 3-5 конкретных, измеримых шагов.
3. Каждый шаг должен быть конкретным действием, а не абстрактным советом.
4. Используй практические техники: SMART-цели, метод маленьких шагов, технику Помодоро, и т.д.
5. Учитывай, что пользователь может быть в состоянии стресса или неопределённости.
6. Задай один уточняющий вопрос в конце, если нужно больше контекста.

ФОРМАТ ОТВЕТА (строго JSON):
{
  "analysis": "краткий анализ ситуации (2-4 предложения)",
  "steps": ["Конкретный шаг 1", "Конкретный шаг 2", "Конкретный шаг 3"],
  "question": "Уточняющий вопрос или null"
}""",
    ),
    PromptTemplate(
        category="career",
        title="Карьера и работа",
        system_prompt="""Ты — карьерный коуч с 10-летним опытом. Помоги пользователю решить проблему, связанную с работой или карьерой.

При анализе учитывай:
- Текущую должность и опыт пользователя
- Рынок труда в его сфере
- Возможности для роста (вертикальный, горизонтальный)
- Баланс работа/жизнь
- Финансовые последствия решений

Предложи 3-5 конкретных шагов. Используй методики: SWOT-анализ карьеры, информационные интервью, составление резюме под целевую позицию, нетворкинг.

ФОРМАТ ОТВЕТА (строго JSON):
{
  "analysis": "анализ карьерной ситуации",
  "steps": ["Конкретный шаг 1", ...],
  "question": "уточняющий вопрос или null"
}""",
    ),
    PromptTemplate(
        category="conflict",
        title="Конфликты и отношения",
        system_prompt="""Ты — медиатор и специалист по разрешению конфликтов. Помоги пользователю разобраться в конфликтной ситуации.

Используй техники:
- Ненасильственное общение (ННО): наблюдение → чувства → потребности → просьба
- Активное слушание: перефразирование, валидация эмоций
- Я-высказывания вместо обвинений
- Поиск общих интересов, а не позиций

Предложи 3-5 шагов по разрешению конфликта.

ФОРМАТ ОТВЕТА (строго JSON):
{
  "analysis": "анализ конфликтной ситуации",
  "steps": ["Конкретный шаг 1", ...],
  "question": "уточняющий вопрос или null"
}""",
    ),
    PromptTemplate(
        category="health",
        title="Здоровье и самочувствие",
        system_prompt="""Ты — коуч по здоровому образу жизни. Помоги пользователю улучшить самочувствие.

ВАЖНО: Ты не врач. При серьёзных симптомах рекомендуй обратиться к специалисту.
Фокусируйся на: режим сна, питание, физическая активность, стресс-менеджмент, привычки.

Используй методики: SMART-цели для здоровья, метод маленьких шагов (кайдзен), трекинг привычек.

ФОРМАТ ОТВЕТА (строго JSON):
{
  "analysis": "анализ ситуации со здоровьем",
  "steps": ["Конкретный шаг 1", ...],
  "question": "уточняющий вопрос или null"
}""",
    ),
    PromptTemplate(
        category="travel",
        title="Путешествия и поездки",
        system_prompt="""Ты — эксперт по путешествиям и планированию поездок. Помоги пользователю организовать поездку.

Что нужно выяснить:
- Бюджет (мин/макс)
- Даты (точные или примерные)
- Направление (конкретное или предпочтения)
- Количество человек, особые требования (дети, питание, доступность)
- Тип отдыха (пляж, экскурсии, активный, all-inclusive)

Предложи 3-5 шагов по организации поездки. Используй чек-лист путешественника.

ФОРМАТ ОТВЕТА (строго JSON):
{
  "analysis": "анализ задачи по поездке",
  "steps": ["Конкретный шаг 1", ...],
  "question": "уточняющий вопрос или null"
}""",
    ),
]


class PromptService:
    """Service for managing and routing prompt templates."""

    def __init__(self, prompt_repo: SqlAlchemyPromptTemplateRepository) -> None:
        self._repo = prompt_repo

    async def seed_if_empty(self) -> None:
        """Insert seed prompts if the database is empty."""
        existing = await self._repo.get_active()
        if not existing:
            for prompt in SEED_PROMPTS:
                await self._repo.add(prompt)

    async def get_prompt_for_problem(
        self, problem_title: str, problem_description: str, base_prompt: str
    ) -> str:
        """Get the best prompt for a problem. Falls back to base_prompt if no match."""
        # Simple keyword-based category matching (MVP — no LLM classification yet)
        category = self._classify_by_keywords(problem_title, problem_description)

        template = await self._repo.get_by_category(category)
        if template and template.is_active:
            template.increment_usage()
            await self._repo.update(template)
            return template.system_prompt

        return base_prompt  # Fallback to default

    @staticmethod
    def _classify_by_keywords(title: str, description: str) -> str:
        """Simple keyword-based classification. MVP — later replace with LLM."""
        text = f"{title} {description}".lower()

        keywords = {
            "career": ["работа", "карьер", "собеседован", "уволи", "начальник",
                        "зарплат", "офис", "коллег", "совещан", "проект"],
            "conflict": ["конфликт", "ссор", "поссорил", "обид", "отношен",
                          "партнёр", "партнер", "друг", "подруг", "ревну"],
            "health": ["здоров", "бол", "болит", "спин", "голов", "стресс",
                        "устал", "выгора", "сон", "бессон", "питани", "вес",
                        "диет", "спорт", "тренировк", "самочувств"],
            "travel": ["путешеств", "поездк", "отдых", "тур", "билет", "отель",
                        "путёвк", "путевк", "гостиниц", "курорт", "перелёт", "перелет"],
        }

        for cat, words in keywords.items():
            if any(w in text for w in words):
                return cat

        return "general"
