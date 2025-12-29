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

    id: int
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
        """Create from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            status=Status(data.get("status", "todo")),
            priority=Priority(data.get("priority", "medium")),
            due_date=data.get("due_date"),
            created_at=data.get("created_at"),
            completed_at=data.get("completed_at"),
            tags=data.get("tags", []),
        )
