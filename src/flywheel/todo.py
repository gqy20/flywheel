"""Todo item model."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


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
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
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

        # Validate optional field types
        description = data.get("description", "")
        if not isinstance(description, str):
            raise ValueError(f"Field 'description' must be str, got {type(description).__name__}")

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
        if due_date is not None and not isinstance(due_date, str):
            raise ValueError(f"Field 'due_date' must be str or None, got {type(due_date).__name__}")

        created_at = data.get("created_at")
        if created_at is not None and not isinstance(created_at, str):
            raise ValueError(f"Field 'created_at' must be str or None, got {type(created_at).__name__}")

        completed_at = data.get("completed_at")
        if completed_at is not None and not isinstance(completed_at, str):
            raise ValueError(f"Field 'completed_at' must be str or None, got {type(completed_at).__name__}")

        tags = data.get("tags")
        if tags is not None and not isinstance(tags, list):
            raise ValueError(f"Field 'tags' must be list, got {type(tags).__name__}")
        # Validate all tags are strings
        if tags is not None and not all(isinstance(tag, str) for tag in tags):
            raise ValueError("All items in 'tags' must be str")

        return cls(
            id=data["id"],
            title=data["title"],
            description=description,
            status=status,
            priority=priority,
            due_date=due_date,
            created_at=created_at,
            completed_at=completed_at,
            tags=tags if tags is not None else [],
        )
