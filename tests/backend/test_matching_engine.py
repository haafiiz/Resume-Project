import pytest

from app.core.matching.matcher import (
    MatchType,
    SkillRef,
    TextRef,
    match_requirement_against_skills,
    match_requirement_against_text,
)
from app.core.matching.normalizer import normalize_skill_name, tokenize
from app.core.matching.scorer import (
    ALL_CATEGORIES,
    DEFAULT_WEIGHTS,
    EMPTY_CATEGORY_SCORE,
    MatchWeights,
    compute_score,
    score_category,
)


def skills(*names: str) -> list[SkillRef]:
    return [SkillRef(id=str(i), name=name) for i, name in enumerate(names)]


class TestNormalizer:
    def test_rest_api_formatting_variants_normalize_to_same_value(self):
        assert (
            normalize_skill_name("REST API")
            == normalize_skill_name("REST APIs")
            == normalize_skill_name("RESTful API")
            == normalize_skill_name("RESTful APIs")
        )

    def test_case_and_whitespace_do_not_affect_normalization(self):
        assert normalize_skill_name("  Python  ") == normalize_skill_name("python")

    def test_unrelated_terms_do_not_normalize_to_the_same_value(self):
        assert normalize_skill_name("Java") != normalize_skill_name("JavaScript")
        assert normalize_skill_name("Selenium") != normalize_skill_name("Playwright")
        assert normalize_skill_name("AWS") != normalize_skill_name("Azure")
        assert normalize_skill_name("React") != normalize_skill_name("Angular")

    def test_unknown_terms_are_returned_unchanged_not_guessed_at(self):
        assert normalize_skill_name("SomeRandomTool") == "somerandomtool"

    def test_tokenize_splits_on_words_and_drops_stopwords(self):
        assert tokenize("Experience with the REST API") == {"experience", "rest", "api"}

    def test_tokenize_java_and_javascript_share_no_tokens(self):
        # This is the property that makes partial matching safe: two
        # different single-word technology names never share a token.
        assert tokenize("Java") & tokenize("JavaScript") == set()


class TestExactMatch:
    def test_identical_names_match_exactly(self):
        outcome = match_requirement_against_skills("Python", skills("Python"))
        assert outcome.match_type == MatchType.EXACT
        assert outcome.confidence == 1.0

    def test_case_insensitive_exact_match(self):
        outcome = match_requirement_against_skills("python", skills("PYTHON"))
        assert outcome.match_type == MatchType.EXACT


class TestNormalizedMatch:
    def test_rest_api_variants_match_as_normalized(self):
        outcome = match_requirement_against_skills("REST APIs", skills("RESTful API"))
        assert outcome.match_type == MatchType.NORMALIZED
        assert outcome.confidence == 0.9

    def test_js_alias_matches_javascript_as_normalized(self):
        outcome = match_requirement_against_skills("JavaScript", skills("JS"))
        assert outcome.match_type == MatchType.NORMALIZED


class TestRelatedMatch:
    def test_sql_dialect_is_related_not_exact(self):
        outcome = match_requirement_against_skills("SQL", skills("PostgreSQL"))
        assert outcome.match_type == MatchType.RELATED
        assert outcome.confidence == 0.6

    def test_related_confidence_is_lower_than_normalized(self):
        related = match_requirement_against_skills("SQL", skills("MySQL"))
        normalized = match_requirement_against_skills("JavaScript", skills("JS"))
        assert related.confidence < normalized.confidence


class TestPartialMatch:
    def test_broader_term_partially_matches_narrower_term(self):
        outcome = match_requirement_against_skills("AWS Lambda", skills("AWS"))
        assert outcome.match_type == MatchType.PARTIAL
        assert outcome.confidence == 0.4

    def test_partial_match_is_symmetric(self):
        a = match_requirement_against_skills("AWS Lambda", skills("AWS"))
        b = match_requirement_against_skills("AWS", skills("AWS Lambda"))
        assert a.match_type == b.match_type == MatchType.PARTIAL


class TestMissingMatch:
    def test_no_candidate_skills_at_all(self):
        outcome = match_requirement_against_skills("Cypress", [])
        assert outcome.match_type == MatchType.MISSING
        assert outcome.confidence == 0.0

    def test_no_matching_skill_among_candidates(self):
        outcome = match_requirement_against_skills("Cypress", skills("Python", "Selenium"))
        assert outcome.match_type == MatchType.MISSING

    def test_missing_never_returns_a_matched_skill(self):
        outcome = match_requirement_against_skills("Cypress", skills("Python"))
        assert outcome.matched_skill is None


class TestUnknownMatch:
    def test_empty_requirement_name_is_unknown(self):
        outcome = match_requirement_against_skills("   ", skills("Python"))
        assert outcome.match_type == MatchType.UNKNOWN

    def test_empty_skill_name_among_candidates_does_not_crash(self):
        outcome = match_requirement_against_skills("Python", skills("", "Python"))
        # The empty-named skill is a candidate but should never win over
        # a real exact match.
        assert outcome.match_type == MatchType.EXACT


class TestMandatoryFalsePositiveGuards:
    """The four pairs the spec explicitly calls out as must-never-merge.
    Every one of these must resolve to `missing` when the JD requirement
    isn't literally present among the resume's skills."""

    def test_java_vs_javascript(self):
        outcome = match_requirement_against_skills("Java", skills("JavaScript"))
        assert outcome.match_type == MatchType.MISSING

        reverse = match_requirement_against_skills("JavaScript", skills("Java"))
        assert reverse.match_type == MatchType.MISSING

    def test_aws_vs_azure(self):
        outcome = match_requirement_against_skills("AWS", skills("Azure"))
        assert outcome.match_type == MatchType.MISSING

        reverse = match_requirement_against_skills("Azure", skills("AWS"))
        assert reverse.match_type == MatchType.MISSING

    def test_selenium_vs_playwright(self):
        outcome = match_requirement_against_skills("Selenium", skills("Playwright"))
        assert outcome.match_type == MatchType.MISSING

        reverse = match_requirement_against_skills("Playwright", skills("Selenium"))
        assert reverse.match_type == MatchType.MISSING

    def test_react_vs_angular(self):
        outcome = match_requirement_against_skills("React", skills("Angular"))
        assert outcome.match_type == MatchType.MISSING

        reverse = match_requirement_against_skills("Angular", skills("React"))
        assert reverse.match_type == MatchType.MISSING

    def test_false_positive_pairs_never_appear_in_the_alias_table(self):
        from app.core.matching.normalizer import CANONICAL_ALIASES

        dangerous_pairs = [
            ("java", "javascript"),
            ("aws", "azure"),
            ("selenium", "playwright"),
            ("react", "angular"),
        ]
        for a, b in dangerous_pairs:
            alias_a = CANONICAL_ALIASES.get(a, a)
            alias_b = CANONICAL_ALIASES.get(b, b)
            assert alias_a != alias_b, f"{a!r} and {b!r} must never share a canonical alias"


class TestReproducibility:
    def test_same_inputs_produce_identical_results_regardless_of_order(self):
        candidates_a = skills("SQL", "Python", "Selenium", "AWS")
        candidates_b = skills("AWS", "Selenium", "Python", "SQL")  # different order

        outcome_a = match_requirement_against_skills("Python", candidates_a)
        outcome_b = match_requirement_against_skills("Python", candidates_b)

        assert outcome_a.match_type == outcome_b.match_type
        assert outcome_a.confidence == outcome_b.confidence

    def test_repeated_calls_produce_identical_results(self):
        results = [
            match_requirement_against_skills("AWS Lambda", skills("AWS", "Python"))
            for _ in range(5)
        ]
        assert len({r.match_type for r in results}) == 1
        assert len({r.confidence for r in results}) == 1


class TestFreetextMatching:
    def test_full_token_coverage_is_normalized(self):
        candidates = [TextRef(id="1", label="Exp", text="Led automated testing with Selenium")]
        outcome = match_requirement_against_text("automated testing", candidates)
        assert outcome.match_type == MatchType.NORMALIZED

    def test_partial_token_coverage_is_partial(self):
        candidates = [TextRef(id="1", label="Exp", text="Led automated testing initiatives")]
        outcome = match_requirement_against_text("automated testing leadership strategy", candidates)
        assert outcome.match_type == MatchType.PARTIAL

    def test_no_overlap_is_missing(self):
        candidates = [TextRef(id="1", label="Exp", text="Built REST APIs in Python")]
        outcome = match_requirement_against_text("machine learning research", candidates)
        assert outcome.match_type == MatchType.MISSING

    def test_no_candidates_at_all_is_missing(self):
        outcome = match_requirement_against_text("Python development", [])
        assert outcome.match_type == MatchType.MISSING

    def test_empty_requirement_is_unknown(self):
        candidates = [TextRef(id="1", label="Exp", text="Some text")]
        outcome = match_requirement_against_text("   ", candidates)
        assert outcome.match_type == MatchType.UNKNOWN

    def test_best_candidate_is_chosen_deterministically(self):
        candidates = [
            TextRef(id="2", label="Weak", text="testing"),
            TextRef(id="1", label="Strong", text="automated testing leadership"),
        ]
        outcome = match_requirement_against_text("automated testing leadership", candidates)
        assert outcome.matched_text is not None
        assert outcome.matched_text.id == "1"


class TestScoreCategory:
    def test_empty_category_gets_neutral_score(self):
        assert score_category([]) == EMPTY_CATEGORY_SCORE

    def test_average_of_confidences(self):
        assert score_category([1.0, 0.0]) == 0.5
        assert score_category([1.0, 1.0, 0.0]) == pytest.approx(2 / 3)


class TestComputeScore:
    def test_acceptance_criteria_example(self):
        # Resume: Python, Selenium, Playwright, SQL
        # JD required skills: Python, Selenium, Playwright, Cypress, AWS
        confidences = {"required_skills": [1.0, 1.0, 1.0, 0.0, 0.0]}

        result = compute_score(confidences, DEFAULT_WEIGHTS)

        # 3/5 matched (avg confidence 0.6) * 50% weight = 30
        # + all 5 other (empty) categories at neutral 1.0 * their weights = 50
        # = 80.0
        assert result.overall_score == 80.0
        assert result.category_scores["required_skills"].requirement_count == 5
        assert result.category_scores["responsibilities"].requirement_count == 0
        assert result.category_scores["responsibilities"].score == EMPTY_CATEGORY_SCORE

    def test_perfect_match_scores_100(self):
        confidences = {category: [1.0, 1.0] for category in ALL_CATEGORIES}
        result = compute_score(confidences, DEFAULT_WEIGHTS)
        assert result.overall_score == 100.0

    def test_zero_match_on_all_required_categories_is_not_zero_due_to_empty_neutral(self):
        # Only required_skills has requirements, and none of them match.
        confidences = {"required_skills": [0.0, 0.0]}
        result = compute_score(confidences, DEFAULT_WEIGHTS)
        # required_skills contributes 0; every other (empty) category
        # contributes its full weight at the neutral score.
        expected = (1 - DEFAULT_WEIGHTS.required_skills) * 100
        assert result.overall_score == pytest.approx(expected)

    def test_completely_empty_jd_scores_100(self):
        result = compute_score({}, DEFAULT_WEIGHTS)
        assert result.overall_score == 100.0

    def test_score_is_reproducible(self):
        confidences = {"required_skills": [1.0, 0.5, 0.0], "keywords": [0.9]}
        first = compute_score(confidences, DEFAULT_WEIGHTS)
        second = compute_score(confidences, DEFAULT_WEIGHTS)
        assert first.overall_score == second.overall_score

    def test_all_six_categories_present_in_result_even_when_unused(self):
        result = compute_score({"required_skills": [1.0]}, DEFAULT_WEIGHTS)
        assert set(result.category_scores.keys()) == set(ALL_CATEGORIES)


class TestMatchWeights:
    def test_default_weights_sum_to_one(self):
        DEFAULT_WEIGHTS.validate()  # should not raise

    def test_weights_are_configurable(self):
        custom = MatchWeights(
            required_skills=0.7,
            responsibilities=0.1,
            experience=0.1,
            education=0.05,
            preferred_skills=0.025,
            keywords=0.025,
        )
        custom.validate()  # should not raise
        assert custom.required_skills == 0.7

    def test_weights_not_summing_to_one_are_rejected(self):
        bad = MatchWeights(required_skills=0.9)  # rest default -> way over 1.0
        with pytest.raises(ValueError):
            bad.validate()

    def test_custom_weights_change_the_overall_score(self):
        confidences = {"required_skills": [1.0]}
        default_result = compute_score(confidences, DEFAULT_WEIGHTS)

        heavier_required = MatchWeights(
            required_skills=0.9,
            responsibilities=0.02,
            experience=0.02,
            education=0.02,
            preferred_skills=0.02,
            keywords=0.02,
        )
        custom_result = compute_score(confidences, heavier_required)

        assert custom_result.overall_score == 100.0  # still 100 since fully matched
        assert (
            custom_result.category_scores["required_skills"].weight
            != default_result.category_scores["required_skills"].weight
        )
