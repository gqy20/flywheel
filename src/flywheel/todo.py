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
    # Using str.translate() to prevent ReDoS vulnerabilities (O(n) guaranteed)
    invisible_chars_map = {
        # Zero-width characters (U+200B-U+200F, U+2060, U+FEFF)
        0x200B: None,  # Zero Width Space
        0x200C: None,  # Zero Width Non-Joiner
        0x200D: None,  # Zero Width Joiner
        0x200E: None,  # Left-to-Right Mark
        0x200F: None,  # Right-to-Left Mark
        0x2060: None,  # Word Joiner
        0xFEFF: None,  # Zero Width No-Break Space (BOM)
        # Soft hyphen and other invisible format characters
        0x00AD: None,  # Soft Hyphen
        0x034F: None,  # Combining Grapheme Joiner
        # General punctuation and invisible separators
        0x2028: None,  # Line Separator
        0x2029: None,  # Paragraph Separator
        # Invisible mathematical operators
        0x2061: None,  # Function Application
        0x2062: None,  # Invisible Times
        0x2063: None,  # Invisible Separator
        0x2064: None,  # Invisible Plus
        # Arabic and other script-specific invisible chars
        0x0600: None,  # Arabic Number Sign
        0x0601: None,  # Arabic Sign Sanah
        0x0602: None,  # Arabic Footnote Marker
        0x0603: None,  # Arabic Sign Safha
        0x06DD: None,  # Arabic End of Ayah
        # Mongolian and other script separators
        0x180B: None,  # Mongolian Free Variation Selector One
        0x180C: None,  # Mongolian Free Variation Selector Two
        0x180D: None,  # Mongolian Free Variation Selector Three
        0x180E: None,  # Mongolian Vowel Separator
        # Variation Selectors
        0xFE00: None,  # Variation Selector-1
        0xFE01: None,  # Variation Selector-2
        0xFE02: None,  # Variation Selector-3
        0xFE03: None,  # Variation Selector-4
        0xFE04: None,  # Variation Selector-5
        0xFE05: None,  # Variation Selector-6
        0xFE06: None,  # Variation Selector-7
        0xFE07: None,  # Variation Selector-8
        0xFE08: None,  # Variation Selector-9
        0xFE09: None,  # Variation Selector-10
        0xFE0A: None,  # Variation Selector-11
        0xFE0B: None,  # Variation Selector-12
        0xFE0C: None,  # Variation Selector-13
        0xFE0D: None,  # Variation Selector-14
        0xFE0E: None,  # Variation Selector-15
        0xFE0F: None,  # Variation Selector-16
        # Tag characters (invisible, used for language tagging)
        0xE0000: None,  # Tag Space
        0xE0001: None,  # Tag Character
        # Combining characters that can be invisible
        0x034F: None,  # Combining Grapheme Joiner (duplicate, already set above)
        # Deprecated/invisible characters
        0x0091: None,  # Private Use 1 (part of control chars range, but handled here for safety)
        0x0092: None,  # Private Use 2
    }
    text = text.translate(invisible_chars_map)

    # Normalize whitespace: convert tabs and newlines to single space
    # Using manual iteration instead of str.split() to explicitly prevent
    # any potential memory issues with large inputs (even though str.split()
    # without arguments is already safe, this makes the intent crystal clear)
    # This is O(n) and uses minimal memory
    result = []
    in_whitespace = False
    for c in text:
        if c in (' ', '\t', '\n', '\r'):
            if not in_whitespace:
                result.append(' ')
                in_whitespace = True
        else:
            result.append(c)
            in_whitespace = False
    text = ''.join(result)

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
    description: str | None = None
    status: Status = Status.TODO
    priority: Priority = Priority.MEDIUM
    due_date: str | None = None
    created_at: str | None = None
    completed_at: str | None = None
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Generate created_at timestamp if not provided.

        This ensures each instance gets a unique timestamp at creation time,
        not at class definition time (fixes issue #1585).

        Also sanitizes title and description to remove control characters
        and normalize whitespace (fixes issue #1705).
        """
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

        # Sanitize title
        self.title = _sanitize_text(self.title).strip()

        # Sanitize description if present
        if self.description is not None:
            self.description = _sanitize_text(self.description).strip()
            # Convert empty/whitespace-only strings to None for type consistency
            if not self.description:
                self.description = None

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
        description = data.get("description")
        if description is not None and not isinstance(description, str):
            raise ValueError(f"Field 'description' must be str or None, got {type(description).__name__}")

        # Sanitize and validate description
        if description is not None:
            description = _sanitize_text(description).strip()
            # Convert empty/whitespace-only strings to None for type consistency
            if not description:
                description = None
            elif len(description) > 5000:
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

        # Sanitize each tag to remove control characters
        if tags is not None:
            tags = [_sanitize_text(tag).strip() for tag in tags]
            # Remove empty tags that result from sanitization
            tags = [tag for tag in tags if tag]

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
