"""Validare cai impotriva path traversal pentru endpoint-urile cu input de client."""
from pathlib import Path


def safe_join(base: Path, *parts: str) -> Path | None:
    """Uneste `parts` sub `base` si verifica ca rezultatul ramane in `base`.

    Intoarce calea rezolvata (care poate inca sa nu existe) sau None daca ar
    evada `base` (ex: '..', cale absoluta, sau symlink in afara).
    """
    base_resolved = base.resolve()
    try:
        candidate = base_resolved.joinpath(*parts).resolve()
    except (OSError, RuntimeError, ValueError):
        return None
    if candidate == base_resolved or candidate.is_relative_to(base_resolved):
        return candidate
    return None


def valid_session_id(session_id: str) -> bool:
    """Un session_id e o singura componenta de cale (fara separatori sau '..')."""
    return bool(session_id) and not {"/", "\\"} & set(session_id) and ".." not in session_id
