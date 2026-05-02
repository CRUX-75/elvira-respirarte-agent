import os
from dotenv import load_dotenv
from langsmith import traceable

load_dotenv()


def is_tracing_enabled() -> bool:
    return os.getenv("LANGSMITH_TRACING", "false").lower() == "true"


@traceable(
    name="elvira_process_message",
    run_type="chain",
)
def _traced_process_message(fn, *args, **kwargs):
    """
    Thin wrapper to trace the deterministic Elvira core.

    LangSmith project is resolved from LANGSMITH_PROJECT.
    """
    return fn(*args, **kwargs)


def traced_process_message(fn, *args, **kwargs):
    """
    Public tracing wrapper.

    If LangSmith tracing is disabled, execute the function normally.
    """
    if not is_tracing_enabled():
        return fn(*args, **kwargs)

    return _traced_process_message(fn, *args, **kwargs)