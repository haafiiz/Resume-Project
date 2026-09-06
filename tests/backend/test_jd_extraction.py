import pytest

from app.core.ai.base import AIProvider, AIProviderResponseError, AIProviderUnavailableError
from app.core.ai.jd_extraction import extract_requirements
from app.utils.text_normalization import normalize_name


class FakeProvider(AIProvider):
    """A minimal AIProvider test double that returns a canned response
    (or raises, to simulate an unavailable provider) - proves
    extract_requirements() works against the AIProvider interface alone,
    with no dependency on Ollama or any network access."""

    def __init__(self, response: str | None = None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.last_prompt: str | None = None
        self.last_system: str | None = None

    def generate(self, prompt: str, system: str | None = None) -> str:
        self.last_prompt = prompt
        self.last_system = system
        if self.error:
            raise self.error
        assert self.response is not None
        return self.response


GOOD_RESPONSE = """{"requirements": [
  {"requirement_type": "required_skill", "name": "Python", "importance": "required", "description": null, "source_text": "Must have Python experience"},
  {"requirement_type": "preferred_skill", "name": "Kubernetes", "importance": "preferred", "description": null, "source_text": "Kubernetes experience preferred"}
]}"""


class TestExtractRequirements:
    def test_parses_valid_response(self):
        provider = FakeProvider(response=GOOD_RESPONSE)

        result = extract_requirements(provider, "some JD text")

        assert len(result.requirements) == 2
        assert result.requirements[0].name == "Python"
        assert result.requirements[0].requirement_type.value == "required_skill"
        assert result.requirements[1].importance.value == "preferred"

    def test_strips_markdown_code_fences(self):
        fenced = f"```json\n{GOOD_RESPONSE}\n```"
        provider = FakeProvider(response=fenced)

        result = extract_requirements(provider, "some JD text")

        assert len(result.requirements) == 2

    def test_accepts_explicit_empty_requirements_list(self):
        provider = FakeProvider(response='{"requirements": []}')

        result = extract_requirements(provider, "a very short JD")

        assert result.requirements == []

    def test_passes_the_jd_description_and_a_system_prompt(self):
        provider = FakeProvider(response=GOOD_RESPONSE)

        extract_requirements(provider, "the exact job description text")

        assert "the exact job description text" in provider.last_prompt
        assert provider.last_system is not None
        assert "never invent" in provider.last_system.lower() or "invent" in provider.last_system.lower()


class TestMalformedResponses:
    def test_non_json_response_raises_response_error(self):
        provider = FakeProvider(response="this is not json at all")

        with pytest.raises(AIProviderResponseError):
            extract_requirements(provider, "jd text")

    def test_json_missing_requirements_key_raises_response_error(self):
        provider = FakeProvider(response='{"foo": "bar"}')

        with pytest.raises(AIProviderResponseError):
            extract_requirements(provider, "jd text")

    def test_invalid_requirement_type_raises_response_error(self):
        provider = FakeProvider(
            response='{"requirements": [{"requirement_type": "not_a_real_type", "name": "X"}]}'
        )

        with pytest.raises(AIProviderResponseError):
            extract_requirements(provider, "jd text")

    def test_missing_required_name_field_raises_response_error(self):
        provider = FakeProvider(
            response='{"requirements": [{"requirement_type": "required_skill"}]}'
        )

        with pytest.raises(AIProviderResponseError):
            extract_requirements(provider, "jd text")

    def test_empty_string_response_raises_response_error(self):
        provider = FakeProvider(response="")

        with pytest.raises(AIProviderResponseError):
            extract_requirements(provider, "jd text")


class TestProviderUnavailable:
    def test_provider_connection_failure_propagates_as_unavailable(self):
        provider = FakeProvider(error=AIProviderUnavailableError("connection refused"))

        with pytest.raises(AIProviderUnavailableError):
            extract_requirements(provider, "jd text")


class TestNormalization:
    def test_lowercases_and_trims(self):
        assert normalize_name("  Python  ") == "python"

    def test_collapses_internal_whitespace(self):
        assert normalize_name("Machine   Learning") == "machine learning"

    def test_preserves_meaningful_punctuation(self):
        assert normalize_name("Node.JS") == "node.js"

    def test_different_casings_normalize_to_the_same_value(self):
        assert normalize_name("PYTHON") == normalize_name("python") == normalize_name("Python")
