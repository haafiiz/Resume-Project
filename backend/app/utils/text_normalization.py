"""
Deterministic text normalization.

Kept separate from AI extraction logic deliberately: normalizing a name
is a mechanical transformation, not a judgment call, so it belongs in
plain, testable code rather than being left to the AI.
"""

import re

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_name(name: str) -> str:
    """Lowercase, trim, and collapse internal whitespace.

    e.g. "  Python  " -> "python", "Node.JS" -> "node.js"
    """
    collapsed = _WHITESPACE_RE.sub(" ", name.strip())
    return collapsed.lower()
