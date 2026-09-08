"""
Normalization for the matching engine.

This is deliberately stricter and more conservative than
app/utils/text_normalization.py's generic normalize_name(). That
function just lowercases/trims/collapses whitespace - fine for
requirement bookkeeping, but not enough to recognize that "REST API",
"REST APIs", and "RESTful API" all mean the same thing.

The temptation with that kind of problem is to reach for a generic
stemmer or fuzzy string similarity. This module deliberately does NOT do
that, because a generic algorithm can't tell the difference between
"two spellings of the same thing" and "two different things that happen
to look similar" - and the cost of getting that wrong is a false
positive that could tell someone they're qualified for something they
aren't. So:

- CANONICAL_ALIASES is an explicit, hand-maintained allow-list. Only
  pairs listed here are ever treated as the same normalized term.
  Nothing is merged by algorithmic similarity.
- Partial/related matching (see matcher.py) works on whole-word tokens,
  never substrings - so "Java" can never accidentally match inside
  "JavaScript" the way a naive `in` check would.

Adding a new alias should be a deliberate, reviewed decision, not
something a matching run can infer on its own.
"""

import re

from app.utils.text_normalization import normalize_name

# Explicit, controlled equivalence classes for common formatting
# variants of the *same* technology/term. Every key must map to a
# canonical value; the canonical value should also map to itself.
#
# CRITICAL: never add pairs here for genuinely different technologies,
# even if they're related or often confused (e.g. Java/JavaScript,
# Selenium/Playwright, AWS/Azure, React/Angular must NEVER appear here).
CANONICAL_ALIASES: dict[str, str] = {
    # REST API formatting variants
    "rest api": "rest api",
    "rest apis": "rest api",
    "restful api": "rest api",
    "restful apis": "rest api",
    # JavaScript
    "javascript": "javascript",
    "js": "javascript",
    # Node.js
    "node.js": "node.js",
    "nodejs": "node.js",
    "node js": "node.js",
    "node": "node.js",
    # TypeScript
    "typescript": "typescript",
    "ts": "typescript",
    # Kubernetes
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    # PostgreSQL
    "postgresql": "postgresql",
    "postgres": "postgresql",
    # CI/CD
    "ci/cd": "ci cd",
    "ci cd": "ci cd",
    "cicd": "ci cd",
    "continuous integration continuous deployment": "ci cd",
    "continuous integration continuous delivery": "ci cd",
    # Amazon Web Services (kept distinct from "aws lambda" etc. - see
    # matcher.py's partial-match logic for compound-term handling)
    "aws": "aws",
    "amazon web services": "aws",
    # CSS
    "css": "css",
    "css3": "css",
    # HTML
    "html": "html",
    "html5": "html",
}

# Minimal stopword list for freetext token-overlap matching
# (responsibilities, experience, education, domain, keywords, soft
# skills - see matcher.py). Deliberately small: the goal is to strip
# grammatical noise, not to be a general-purpose NLP stopword list.
STOPWORDS: frozenset[str] = frozenset(
    {
        "a", "an", "the", "of", "in", "on", "at", "to", "for", "and", "or",
        "with", "is", "are", "be", "as", "by", "this", "that", "will",
        "you", "your", "our", "we", "years", "year",
    }
)

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9+.#/-]*")


def normalize_skill_name(name: str) -> str:
    """Normalize a skill/technology name for equivalence comparison.

    Applies base normalization (lowercase/trim/collapse whitespace) and
    then looks the result up in the explicit alias table. If the result
    isn't a known alias, it's returned unchanged - normalization never
    guesses.
    """
    base = normalize_name(name)
    return CANONICAL_ALIASES.get(base, base)


def tokenize(text: str) -> set[str]:
    """Split text into lowercase word tokens for overlap-based matching,
    stripping stopwords. Used for compound/partial skill matching and
    freetext category matching (responsibilities, experience, education,
    domain, keywords, soft skills) - never for the exact/normalized/
    related skill-name comparisons, which compare whole normalized
    strings, not token sets, to avoid accidental partial overlaps like
    "java" matching inside "javascript"."""
    words = _WORD_RE.findall(text.lower())
    return {word for word in words if word not in STOPWORDS and len(word) > 1}
