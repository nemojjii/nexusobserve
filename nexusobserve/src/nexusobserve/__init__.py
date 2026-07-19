"""nexusobserve — instrument AI agents to capture decision records."""

from .schema import DecisionRecord, from_dict, from_json, to_dict, to_json
from .tracer import init, record_decision

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "DecisionRecord",
    "from_dict",
    "from_json",
    "to_dict",
    "to_json",
    "init",
    "record_decision",
]
