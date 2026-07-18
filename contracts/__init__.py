"""Nexus shared contracts — the single source of truth for the DecisionRecord schema."""

from .schema import (
    SCHEMA_VERSION,
    DecisionRecord,
    from_dict,
    from_json,
    to_dict,
    to_json,
)

__all__ = [
    "SCHEMA_VERSION",
    "DecisionRecord",
    "from_dict",
    "from_json",
    "to_dict",
    "to_json",
]
