"""Core Todo data model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _sanitize_for_repr(text: str) -> str:
    """Escape control characters for safe display in repr output.

    Replaces ASCII control characters (0x00-0x1f), DEL (0x7f), and
    C1 control characters (0x80-0x9f) with their escaped representations.
    Also escapes backslashes to prevent collision with escape sequences.
    """
    # First: Escape backslash to prevent collision with escape sequences
    text = text.replace("\\", "\\\\")

    # Common control characters - replace with readable escapes
    replacements = [
        ("\n", "\\n"),
        ("\r", "\\r"),
        ("\t", "\\t"),
    ]
    for char, escaped in replacements:
        text = text.replace(char, escaped)

    # Other control characters (0x00-0x1f excluding \n, \r, \t), DEL (0x7f), and C1 (0x80-0x9f)
    # Replace with \\xNN escape sequences
    result = []
    for char in text:
        code = ord(char)
        if (0 <= code <= 0x1F and char not in ("\n", "\r", "\t")) or 0x7F <= code <= 0x9F:
            result.append(f"\\x{code:02x}")
        else:
            result.append(char)
    return "".join(result)


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
        Control characters in text are escaped for safe debugger display.
        """
        # Sanitize text to escape control characters (newlines, tabs, etc.)
        # before truncation to ensure consistent single-line output
        display_text = _sanitize_for_repr(self.text)
        if len(display_text) > 50:
            display_text = display_text[:47] + "..."

        return f"Todo(id={self.id}, text='{display_text}', done={self.done})"

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

        return cls(
            id=todo_id,
            text=data["text"],
            done=done,
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )
