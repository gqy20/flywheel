"""Core Todo data model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from re import fullmatch


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _validate_iso_date(date_str: str | None) -> None:
    """Validate that date_str is a valid ISO date format (YYYY-MM-DD).

    Args:
        date_str: The date string to validate.

    Raises:
        ValueError: If date_str is not a valid ISO date format.
    """
    if date_str is None:
        return
    # ISO 8601 date format: YYYY-MM-DD
    if not fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
        raise ValueError(
            f"Invalid value for 'due_date': {date_str!r}. "
            "'due_date' must be in ISO 8601 format (YYYY-MM-DD)."
    )
    # Additional validation: try to parse the date
    try:
        datetime.fromisoformat(date_str)
    except ValueError as e:
        raise ValueError(
            f"Invalid value for 'due_date': {date_str!r}. "
            "'due_date' must be a valid date in ISO 8601 format (YYYY-MM-DD)."
        ) from e


@dataclass(slots=True)
class Todo:
    """Simple todo item."""

    id: int
    text: str
    done: bool = False
    due_date: str | None = None
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

        # Validate 'due_date' if present
        raw_due_date = data.get("due_date")
        if raw_due_date is not None and raw_due_date != "":
            _validate_iso_date(str(raw_due_date))
            due_date = str(raw_due_date)
        else:
            due_date = None

        return cls(
            id=todo_id,
            text=data["text"],
            done=done,
            due_date=due_date,
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )
