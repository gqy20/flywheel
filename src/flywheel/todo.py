"""Core Todo data model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class Todo:
    """Simple todo item."""

    id: int
    text: str
    done: bool = False
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = _utc_now_iso()
        if not self.updated_at:
            self.updated_at = self.created_at

    def mark_done(self) -> None:
        self.done = True
        self.updated_at = _utc_now_iso()

    def mark_undone(self) -> None:
        self.done = False
        self.updated_at = _utc_now_iso()

    def rename(self, text: str) -> None:
        self.text = text.strip()
        self.updated_at = _utc_now_iso()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Todo:
        # Validate and extract 'id' field
        if "id" not in data:
            raise ValueError("Todo is missing required field 'id'")
        try:
            todo_id = int(data["id"])
        except (TypeError, ValueError):
            raise ValueError(f"Todo field 'id' must be an integer, got {type(data['id']).__name__}") from None

        # Validate and extract 'text' field
        if "text" not in data:
            raise ValueError("Todo is missing required field 'text'")
        if not isinstance(data["text"], str):
            raise ValueError(f"Todo field 'text' must be a string, got {type(data['text']).__name__}")

        return cls(
            id=todo_id,
            text=data["text"],
            done=bool(data.get("done", False)),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )
