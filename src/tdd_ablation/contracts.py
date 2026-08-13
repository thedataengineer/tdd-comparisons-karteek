"""Study data contracts: JSON loading, field validation, identifier safety.

Every function raises ContractError on violation. No function modifies
input data or has side effects beyond raising.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class ContractError(ValueError):
    """Raised when study data violates a structural contract."""


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def load_json(path: Path) -> dict[str, Any]:
    """Read and parse a JSON file, wrapping OS and parse errors.

    Returns the parsed dict. Raises ContractError if the file is missing
    or contains invalid JSON.
    """
    if not path.exists():
        raise ContractError(f"{path}: not found")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractError(f"{path}: read failed: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ContractError(f"{path}: invalid JSON: {exc}") from exc
    return data


def require_fields(
    data: dict[str, Any],
    required: set[str],
    context: str,
) -> None:
    """Assert that *data* contains every key in *required*.

    Raises ContractError listing missing field names (sorted) with
    *context* as a prefix for the error message.
    """
    missing = sorted(required - set(data))
    if missing:
        names = ", ".join(missing)
        raise ContractError(f"{context}: missing fields: {names}")


def validate_identifier(value: str, field: str) -> str:
    """Return *value* unchanged if it is a safe filesystem identifier.

    Rejects empty strings, path-traversal components (``..``), slashes,
    and any character outside ``[A-Za-z0-9._-]``.
    """
    if not value:
        raise ContractError(f"{field}: identifier must not be empty")
    if "/" in value or "\\" in value:
        raise ContractError(f"{field}: identifier must not contain path separators: {value!r}")
    if ".." in value:
        raise ContractError(f"{field}: identifier must not contain path traversal: {value!r}")
    if not _SAFE_ID.match(value):
        raise ContractError(f"{field}: identifier contains invalid characters: {value!r}")
    return value
