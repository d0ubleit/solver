"""Unit tests for the PromptTemplate entity."""


from solver.domain.prompts import PromptTemplate, PromptTemplateId


class TestPromptTemplateEntity:
    """Tests for PromptTemplate domain entity."""

    def test_create_with_defaults(self):
        t = PromptTemplate(
            category="travel",
            title="Путешествия",
            system_prompt="Ты — эксперт по путешествиям.",
        )
        assert t.category == "travel"
        assert t.title == "Путешествия"
        assert t.system_prompt == "Ты — эксперт по путешествиям."
        assert t.usage_count == 0
        assert t.is_active is True
        assert isinstance(t.id, PromptTemplateId)
        assert t.created_at is not None

    def test_create_with_full_data(self):
        pid = PromptTemplateId.generate()
        t = PromptTemplate(
            id=pid,
            category="health",
            title="Здоровье",
            system_prompt="prompt",
            usage_count=5,
            is_active=False,
        )
        assert t.id == pid
        assert t.usage_count == 5
        assert t.is_active is False

    def test_increment_usage(self):
        t = PromptTemplate(category="general", title="G", system_prompt="p")
        assert t.usage_count == 0
        t.increment_usage()
        t.increment_usage()
        assert t.usage_count == 2

    def test_deactivate(self):
        t = PromptTemplate(category="general", title="G", system_prompt="p")
        assert t.is_active is True
        t.deactivate()
        assert t.is_active is False


class TestPromptTemplateId:
    """Tests for PromptTemplateId value object."""

    def test_generate_unique(self):
        a = PromptTemplateId.generate()
        b = PromptTemplateId.generate()
        assert a != b

    def test_equality(self):
        from uuid import uuid4
        u = uuid4()
        assert PromptTemplateId(u) == PromptTemplateId(u)

    def test_str(self):
        from uuid import uuid4
        u = uuid4()
        assert str(PromptTemplateId(u)) == str(u)
