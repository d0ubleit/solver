"""AI service interfaces and implementations."""

from abc import ABC, abstractmethod

from solver.application.dtos import AIAnalysisRequestDTO, AIAnalysisResponseDTO


class AIAnalysisService(ABC):
    """Abstract interface for AI-powered problem analysis."""

    @abstractmethod
    async def analyze(self, request: AIAnalysisRequestDTO) -> AIAnalysisResponseDTO:
        """Analyze a problem and return recommended steps or clarifying questions."""
        ...

    @abstractmethod
    async def continue_dialog(
        self,
        problem_title: str,
        problem_description: str,
        steps_summary: str,
        conversation_history: list[dict[str, str]],
        user_message: str,
    ) -> dict:
        """Continue a conversation about an existing problem.

        Returns:
            {"reply": str, "updated_steps": list[str] | None}
        """
        ...

    @abstractmethod
    async def check_in(
        self,
        problem_title: str,
        steps_status: list[dict[str, str]],
        conversation_history: list[dict[str, str]],
    ) -> str:
        """Generate a personalized check-in message for the user."""
        ...


class OpenAIAnalysisService(AIAnalysisService):
    """OpenAI-based implementation of AI analysis service."""

    SYSTEM_PROMPT = """Ты — проактивный AI-коуч, помогающий людям решать жизненные и рабочие проблемы.
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
}"""

    CHECK_IN_PROMPT = """Ты — проактивный AI-коуч. Пользователь работает над проблемой: "{problem_title}"

Текущий статус шагов:
{steps_status}

Напиши короткое, мотивирующее сообщение-чекин (2-4 предложения), которое:
1. Отметит прогресс пользователя (даже небольшой)
2. Мягко спросит о текущем статусе
3. Предложит помощь, если пользователь застрял
4. Будет звучать по-дружески, а не как automated message

НЕ ИСПОЛЬЗУЙ эмодзи. Будь искренним и конкретным."""

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._client = None

    def _get_client(self):
        """Lazy initialization of OpenAI-compatible client (OpenAI, DeepSeek, etc.)."""
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )
        return self._client

    async def analyze(self, request: AIAnalysisRequestDTO, system_prompt: str = "") -> AIAnalysisResponseDTO:
        """Analyze a problem using OpenAI API. Accepts optional system_prompt override."""
        import json

        client = self._get_client()
        prompt = system_prompt or self.SYSTEM_PROMPT

        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": f"Проблема: {request.problem_title}\n\nОписание: {request.problem_description}",
            },
        ]

        # Include conversation history if available
        if request.conversation_history:
            messages = [messages[0]] + request.conversation_history + [messages[1]]

        response = await client.chat.completions.create(
            model=self._model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=1000,
        )

        content = response.choices[0].message.content or "{}"
        result = json.loads(content)

        return AIAnalysisResponseDTO(
            analysis=result.get("analysis", ""),
            steps=result.get("steps", []),
            tokens_used=response.usage.total_tokens if response.usage else 0,
        )

    async def check_in(
        self,
        problem_title: str,
        steps_status: list[dict[str, str]],
        conversation_history: list[dict[str, str]],
    ) -> str:
        """Generate a personalized check-in message."""
        client = self._get_client()

        status_text = "\n".join(
            f"- {s['description']}: {s['status']}" for s in steps_status
        )

        prompt = self.CHECK_IN_PROMPT.format(
            problem_title=problem_title,
            steps_status=status_text or "Шаги ещё не определены",
        )

        messages = [{"role": "system", "content": prompt}]
        if conversation_history:
            messages = [messages[0]] + conversation_history[-4:]  # Last 4 messages

        response = await client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.8,
            max_tokens=300,
        )

        return response.choices[0].message.content or "Как продвигается работа над проблемой?"

    async def continue_dialog(
        self,
        problem_title: str,
        problem_description: str,
        steps_summary: str,
        conversation_history: list[dict[str, str]],
        user_message: str,
    ) -> dict:
        """Continue a conversation about an existing problem. Returns reply and optional step updates."""
        import json

        client = self._get_client()

        system_prompt = f"""Ты — AI-коуч. Пользователь работает над проблемой: "{problem_title}"
Описание: {problem_description}
Текущие шаги: {steps_summary}

Твоя задача — ответить на сообщение пользователя в контексте этой проблемы.
Если пользователь просит уточнить, скорректировать или добавить шаги — сделай это.
ФОРМАТ ОТВЕТА (строго JSON):
{{
  "reply": "твой ответ пользователю (2-5 предложений)",
  "updated_steps": ["Шаг 1 (обновлённый)", "Шаг 2", ...] или null если шаги не менялись
}}"""

        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages += conversation_history[-10:]  # Last 10 messages for context
        messages.append({"role": "user", "content": user_message})

        response = await client.chat.completions.create(
            model=self._model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=800,
        )

        content = response.choices[0].message.content or "{}"
        return json.loads(content)
