"""Unit tests for PromptService — classification, seeding, and routing."""

from unittest.mock import AsyncMock

import pytest

from solver.application.prompt_service import PromptService, SEED_PROMPTS
from solver.domain.prompts import PromptTemplate


@pytest.fixture
def prompt_repo():
    return AsyncMock()


@pytest.fixture
def service(prompt_repo):
    return PromptService(prompt_repo)


class TestKeywordClassification:
    """Tests for keyword-based problem classification."""

    @pytest.mark.parametrize("text,expected", [
        ("Хочу найти новую работу и сменить карьеру", "career"),
        ("Конфликт с коллегой на работе", "career"),  # "коллег" wins first
        ("Поссорился с партнёром, обида", "conflict"),
        ("Болит спина и голова, постоянный стресс", "health"),
        ("Хочу путёвку в Турцию, нужен отель", "travel"),
        ("Как приготовить борщ?", "general"),
        ("", "general"),
    ])
    def test_classify(self, text, expected):
        assert PromptService._classify_by_keywords(text, "") == expected

    def test_classify_uses_description_too(self):
        # Title is vague, description reveals it's travel
        result = PromptService._classify_by_keywords("Помоги", "нужен тур на море")
        assert result == "travel"

    def test_classify_case_insensitive(self):
        assert PromptService._classify_by_keywords("РАБОТА", "") == "career"


class TestSeeding:
    """Tests for seed_if_empty."""

    @pytest.mark.asyncio
    async def test_seeds_when_empty(self, service, prompt_repo):
        prompt_repo.get_active.return_value = []
        prompt_repo.add.return_value = None

        await service.seed_if_empty()

        assert prompt_repo.add.call_count == len(SEED_PROMPTS)
        categories = {call.args[0].category for call in prompt_repo.add.call_args_list}
        assert {"general", "career", "conflict", "health", "travel"} == categories

    @pytest.mark.asyncio
    async def test_does_not_seed_when_has_templates(self, service, prompt_repo):
        prompt_repo.get_active.return_value = [PromptTemplate("general", "G", "p")]

        await service.seed_if_empty()

        prompt_repo.add.assert_not_called()


class TestGetPromptForProblem:
    """Tests for get_prompt_for_problem routing."""

    @pytest.mark.asyncio
    async def test_returns_template_and_increments_usage(self, service, prompt_repo):
        template = PromptTemplate(
            category="travel", title="Travel", system_prompt="TRAVEL_PROMT"
        )
        prompt_repo.get_by_category.return_value = template
        prompt_repo.update.return_value = template

        result = await service.get_prompt_for_problem(
            "Хочу путёвку в Турцию", "", base_prompt="BASE"
        )

        assert result == "TRAVEL_PROMT"
        assert template.usage_count == 1
        prompt_repo.update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_falls_back_when_no_template(self, service, prompt_repo):
        prompt_repo.get_by_category.return_value = None

        result = await service.get_prompt_for_problem(
            "Как приготовить борщ", "", base_prompt="BASE_PROMPT"
        )

        assert result == "BASE_PROMPT"

    @pytest.mark.asyncio
    async def test_falls_back_when_inactive(self, service, prompt_repo):
        template = PromptTemplate(
            category="travel", title="T", system_prompt="X", is_active=False
        )
        prompt_repo.get_by_category.return_value = template

        result = await service.get_prompt_for_problem(
            "путёвка", "", base_prompt="BASE"
        )

        assert result == "BASE"
        # inactive template must not be counted
        assert template.usage_count == 0


class TestSeedPromptsIntegrity:
    """Sanity checks on the built-in seed prompts."""

    def test_all_have_required_fields(self):
        for p in SEED_PROMPTS:
            assert p.category
            assert p.title
            assert p.system_prompt
            assert "JSON" in p.system_prompt or "json" in p.system_prompt

    def test_unique_categories(self):
        cats = [p.category for p in SEED_PROMPTS]
        assert len(cats) == len(set(cats))
