"""Core Todo data model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from re import fullmatch


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _validate_iso_date(date_str: str) -> bool:
    """Validate that a string is in YYYY-MM-DD date format.

    Args:
        date_str: The string to validate.

    Returns:
        True if the string is a valid ISO date (YYYY-MM-DD), False otherwise.
    """
    if not isinstance(date_str, str):
        return False
    # Use regex to validate YYYY-MM-DD format
    # YYYY: 4 digits, MM: 01-12, DD: 01-31
    return fullmatch(r"\d{4}-\d{2}-\d{2}", date_str) is not None


@dataclass(slots=True)
class Todo:
    """Simple todo item."""

    id: int
    text: str
    done: bool = False
    created_at: str = ""
    updated_at: str = ""
    due_date: str | None = None

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

    def set_due_date(self, date: str | None) -> None:
        """Set the due date for this todo.

        Args:
            date: ISO date string in YYYY-MM-DD format, or None/empty string to clear.

        Raises:
            ValueError: If date is not a valid ISO date format or None/empty string.
        """
        # Handle None or empty string as clearing the due date
        if date is None or (isinstance(date, str) and date == ""):
            self.due_date = None
            self.updated_at = _utc_now_iso()
            return

        # Validate ISO date format (YYYY-MM-DD)
        if not _validate_iso_date(date):
            raise ValueError(
                f"Invalid ISO date format: {date!r}. "
                "Expected format: YYYY-MM-DD (e.g., '2025-12-31')."
            )

        self.due_date = date
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

        # Validate and extract due_date if present
        raw_due_date = data.get("due_date")
        due_date: str | None = None
        if (
            raw_due_date is not None
            and raw_due_date != ""
            and isinstance(raw_due_date, str)
            and _validate_iso_date(raw_due_date)
        ):
            due_date = raw_due_date
        # Invalid due_date values are ignored (treated as None)

        return cls(
            id=todo_id,
            text=data["text"],
            done=done,
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
            due_date=due_date,
        )
