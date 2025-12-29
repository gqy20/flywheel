"""Todo storage backend."""

import json
import logging
from pathlib import Path

from flywheel.todo import Todo

logger = logging.getLogger(__name__)


class Storage:
    """File-based todo storage."""

    def __init__(self, path: str = "~/.flywheel/todos.json"):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._todos: list[Todo] = []
        self._load()

    def _load(self) -> None:
        """Load todos from file."""
        if not self.path.exists():
            self._todos = []
            return

        try:
            data = json.loads(self.path.read_text())
            if not isinstance(data, list):
                logger.warning(f"Invalid data format in {self.path}: expected list, got {type(data).__name__}")
                self._todos = []
                return

            todos = []
            for i, item in enumerate(data):
                try:
                    todo = Todo.from_dict(item)
                    todos.append(todo)
                except (ValueError, TypeError, KeyError) as e:
                    # Skip invalid todo items but continue loading valid ones
                    logger.warning(f"Skipping invalid todo at index {i}: {e}")
            self._todos = todos
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in {self.path}: {e}")
            self._todos = []
        except Exception as e:
            logger.warning(f"Failed to load todos: {e}")
            self._todos = []

    def _save(self) -> None:
        """Save todos to file."""
        self.path.write_text(json.dumps([t.to_dict() for t in self._todos], indent=2))

    def add(self, todo: Todo) -> Todo:
        """Add a new todo."""
        self._todos.append(todo)
        self._save()
        return todo

    def list(self, status: str | None = None) -> list[Todo]:
        """List all todos."""
        if status:
            return [t for t in self._todos if t.status == status]
        return self._todos

    def get(self, todo_id: int) -> Todo | None:
        """Get a todo by ID."""
        for todo in self._todos:
            if todo.id == todo_id:
                return todo
        return None

    def update(self, todo: Todo) -> Todo | None:
        """Update a todo."""
        for i, t in enumerate(self._todos):
            if t.id == todo.id:
                self._todos[i] = todo
                self._save()
                return todo
        return None

    def delete(self, todo_id: int) -> bool:
        """Delete a todo."""
        for i, t in enumerate(self._todos):
            if t.id == todo_id:
                del self._todos[i]
                self._save()
                return True
        return False

    def get_next_id(self) -> int:
        """Get next available ID."""
        if not self._todos:
            return 1
        return max(t.id for t in self._todos) + 1
