"""Nexus SDK — capture agent decisions and (optionally) ship them to the server."""

from .tracer import DecisionRecord, record_decision

__all__ = ["DecisionRecord", "record_decision"]
