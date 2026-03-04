"""Core Todo data model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _is_valid_iso_timestamp(ts: str) -> bool:
    """Check if a string is a valid ISO 8601 timestamp.

    Accepts formats like:
    - 2024-01-15T10:30:00+00:00 (with timezone offset)
    - 2024-01-15T10:30:00Z (with Z suffix)
    - 2024-01-15T10:30:00.123456+00:00 (with microseconds)
    """
    if not ts:
        return False
    try:
        # Handle Z suffix by replacing with +00:00 for parsing
        ts_to_parse = ts.replace("Z", "+00:00")
        datetime.fromisoformat(ts_to_parse)
        return True
    except ValueError:
        return False


@dataclass(slots=True)
class Todo:
    """Simple todo item."""

    id: int
    text: str
    done: bool = False
    created_at: str = ""
    updated_at: str = ""

    def __repr__(self) -> str:
        """Return a concise, debug-friendly representation of the Todo.

        Shows only the essential fields (id, text, done) and truncates long text.
        Timestamps are excluded to keep the output concise and useful in debuggers.
        """
        # Truncate text if longer than 50 characters
        display_text = self.text
        if len(display_text) > 50:
            display_text = display_text[:47] + "..."

        return f"Todo(id={self.id}, text={display_text!r}, done={self.done})"

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
        text = text.strip()
        if not text:
            raise ValueError("Todo text cannot be empty")
        self.text = text
        self.updated_at = _utc_now_iso()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Todo:
        # Validate required fields with clear error messages
        if "id" not in data:
            raise ValueError("Missing required field 'id' in todo data")
        if "text" not in data:
            raise ValueError("Missing required field 'text' in todo data")

        # Validate 'id' is an integer (or can be converted to one)
        try:
            todo_id = int(data["id"])
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Invalid value for 'id': {data['id']!r}. 'id' must be an integer."
            ) from e

        # Validate 'text' is a string
        if not isinstance(data["text"], str):
            raise ValueError(
                f"Invalid value for 'text': {data['text']!r}. 'text' must be a string."
            )

        # Validate 'done' is a proper boolean value
        # Accept: True, False, 0, 1
        # Reject: other integers (2, -1), strings, or other types
        raw_done = data.get("done", False)
        if isinstance(raw_done, bool):
            done = raw_done
        elif isinstance(raw_done, int) and raw_done in (0, 1):
            done = bool(raw_done)
        else:
            raise ValueError(
                f"Invalid value for 'done': {raw_done!r}. "
                "'done' must be a boolean (true/false) or 0/1."
            )

        # Validate timestamp formats if provided
        created_at_raw = data.get("created_at")
        updated_at_raw = data.get("updated_at")

        created_at = str(created_at_raw or "")
        updated_at = str(updated_at_raw or "")

        # Only validate if a non-empty string was explicitly provided
        if created_at_raw is not None and created_at and not _is_valid_iso_timestamp(created_at):
            raise ValueError(
                f"Invalid timestamp format for 'created_at': {created_at!r}. "
                "Expected ISO 8601 format (e.g., 2024-01-15T10:30:00+00:00)."
            )
        if updated_at_raw is not None and updated_at and not _is_valid_iso_timestamp(updated_at):
            raise ValueError(
                f"Invalid timestamp format for 'updated_at': {updated_at!r}. "
                "Expected ISO 8601 format (e.g., 2024-01-15T10:30:00+00:00)."
            )

        return cls(
            id=todo_id,
            text=data["text"],
            done=done,
            created_at=created_at,
            updated_at=updated_at,
        )
