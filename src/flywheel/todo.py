"""Todo item model."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


def _sanitize_text(text: str) -> str:
    """Remove control characters and normalize whitespace.

    Args:
        text: Input text to sanitize

    Returns:
        Sanitized text with control characters removed

    Note:
        Uses character iteration instead of regex to prevent ReDoS
        (Regular Expression Denial of Service) vulnerabilities.
        This approach is O(n) and guaranteed not to backtrack.
    """
    # Define control characters to remove (ASCII 0-8, 11-12, 14-31, 127)
    # Excludes \t (9), \n (10), \r (13) which are handled separately
    control_chars = set(
        # ASCII 0-8
        range(0x00, 0x09) |
        # ASCII 11-12 (skip \t=9 and \n=10)
        range(0x0b, 0x0d) |
        # ASCII 14-31 (skip \r=13)
        range(0x0e, 0x20) |
        # ASCII 127 (DEL)
        {0x7f}
    )

    # Remove control characters using list comprehension (non-backtracking)
    # This is O(n) and prevents ReDoS vulnerabilities
    text = ''.join(c for c in text if ord(c) not in control_chars)

    # Remove zero-width spaces and other invisible Unicode characters
    # This regex is safe as it matches fixed character ranges
    text = re.sub(r'[\u200b-\u200d\u2060\ufeff]', '', text)

    # Normalize whitespace: convert tabs and newlines to single space
    # (in case any slipped through before strip)
    # Using split/join instead of regex to prevent ReDoS vulnerabilities
    # This is O(n) and safer than regex alternatives
    text = ' '.join(text.split())

    return text


class Priority(str, Enum):
    """Todo priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Status(str, Enum):
    """Todo status."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


@dataclass
class Todo:
    """A todo item."""

    id: int | None
    title: str
    description: str = ""
    status: Status = Status.TODO
    priority: Priority = Priority.MEDIUM
    due_date: str | None = None
    created_at: str | None = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str | None = None
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "due_date": self.due_date,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Todo":
        """Create from dictionary with strict validation."""
        # Validate input is a dictionary
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data).__name__}")

        # Validate required fields exist and have correct types
        if "id" not in data:
            raise ValueError("Missing required field: 'id'")
        if "title" not in data:
            raise ValueError("Missing required field: 'title'")

        # Validate field types
        if not isinstance(data["id"], int):
            raise ValueError(f"Field 'id' must be int, got {type(data['id']).__name__}")
        if not isinstance(data["title"], str):
            raise ValueError(f"Field 'title' must be str, got {type(data['title']).__name__}")

        # Sanitize and validate title
        title = _sanitize_text(data["title"]).strip()
        if not title:
            raise ValueError("Title cannot be empty or whitespace-only")
        if len(title) > 200:
            raise ValueError(f"Title too long: {len(title)} characters (max 200)")

        # Validate optional field types
        description = data.get("description", "")
        if not isinstance(description, str):
            raise ValueError(f"Field 'description' must be str, got {type(description).__name__}")

        # Sanitize and validate description
        description = _sanitize_text(description).strip()
        if len(description) > 5000:
            raise ValueError(f"Description too long: {len(description)} characters (max 5000)")

        # Validate enum values strictly
        status_value = data.get("status", "todo")
        if not isinstance(status_value, str):
            raise ValueError(f"Field 'status' must be str, got {type(status_value).__name__}")
        try:
            status = Status(status_value)
        except ValueError:
            # Raise error to notify about invalid data
            raise ValueError(
                f"Invalid status value: '{status_value}'. "
                f"Valid values are: {[s.value for s in Status]}"
            )

        priority_value = data.get("priority", "medium")
        if not isinstance(priority_value, str):
            raise ValueError(f"Field 'priority' must be str, got {type(priority_value).__name__}")
        try:
            priority = Priority(priority_value)
        except ValueError:
            # Raise error to notify about invalid data
            raise ValueError(
                f"Invalid priority value: '{priority_value}'. "
                f"Valid values are: {[p.value for p in Priority]}"
            )

        # Validate other optional fields
        due_date = data.get("due_date")
        if due_date is not None:
            if not isinstance(due_date, str):
                raise ValueError(f"Field 'due_date' must be str or None, got {type(due_date).__name__}")
            # Validate ISO 8601 format
            try:
                datetime.fromisoformat(due_date)
            except ValueError:
                raise ValueError(f"Invalid ISO 8601 date format for 'due_date': '{due_date}'")

        created_at = data.get("created_at")
        if created_at is not None:
            if not isinstance(created_at, str):
                raise ValueError(f"Field 'created_at' must be str or None, got {type(created_at).__name__}")
            # Validate ISO 8601 format
            try:
                datetime.fromisoformat(created_at)
            except ValueError:
                raise ValueError(f"Invalid ISO 8601 date format for 'created_at': '{created_at}'")

        completed_at = data.get("completed_at")
        if completed_at is not None:
            if not isinstance(completed_at, str):
                raise ValueError(f"Field 'completed_at' must be str or None, got {type(completed_at).__name__}")
            # Validate ISO 8601 format
            try:
                datetime.fromisoformat(completed_at)
            except ValueError:
                raise ValueError(f"Invalid ISO 8601 date format for 'completed_at': '{completed_at}'")

        tags = data.get("tags")
        if tags is not None and not isinstance(tags, list):
            raise ValueError(f"Field 'tags' must be list, got {type(tags).__name__}")
        # Validate all tags are strings
        if tags is not None and not all(isinstance(tag, str) for tag in tags):
            raise ValueError("All items in 'tags' must be str")

        # Build kwargs dynamically to avoid overriding default_factory
        kwargs = {
            "id": data["id"],
            "title": title,
            "description": description,
            "status": status,
            "priority": priority,
            "due_date": due_date,
        }
        # Only add tags if not None to let default_factory work
        if tags is not None:
            kwargs["tags"] = tags

        # Only add completed_at if not None
        if completed_at is not None:
            kwargs["completed_at"] = completed_at

        # Only add created_at if not None to let default_factory work
        if created_at is not None:
            kwargs["created_at"] = created_at

        return cls(**kwargs)
