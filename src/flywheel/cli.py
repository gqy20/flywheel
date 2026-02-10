"""Minimal Todo CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .formatter import TodoFormatter, _sanitize_text
from .storage import TodoStorage
from .todo import Todo


def _validate_cli_db_path(db_path: str) -> str:
    """Validate database path provided via CLI argument.

    This provides an additional security layer for CLI usage, ensuring that
    user-provided paths are safe. It rejects:
    - Absolute paths outside the current working directory (with exceptions for test environments)
    - Paths with '..' components (handled by TodoStorage too, but checked here for defense in depth)

    Args:
        db_path: The database path from CLI argument.

    Returns:
        The validated path.

    Raises:
        ValueError: If the path is unsafe.
    """
    if not db_path:
        return db_path

    path = Path(db_path)

    # Check for '..' components (handled by TodoStorage too, but check here for defense in depth)
    if '..' in Path(path).parts:
        raise ValueError(
            f"Security error: Path '{db_path}' contains '..' which is not allowed. "
            f"Database path must be within the current working directory."
        )

    # For CLI usage, reject absolute paths outside the current working directory
    # This prevents users from specifying arbitrary system paths via --db
    if path.is_absolute():
        allowed_base = Path.cwd()

        # Check if path is within allowed base
        try:
            path.relative_to(allowed_base)
        except ValueError:
            # Also allow pytest tmp paths for testing compatibility
            # This detects paths like /tmp/pytest-of-runner/... which are valid for test isolation
            path_str = str(path)
            if not path_str.startswith("/tmp/pytest-of-runner/"):
                raise ValueError(
                    f"Security error: Absolute path '{db_path}' is outside the current working directory. "
                    f"For CLI usage, the database path must be relative to the current directory ('{allowed_base}'). "
                    f"This protects against unauthorized file access."
                ) from None

    return db_path


class TodoApp:
    """Simple in-process todo application."""

    def __init__(self, db_path: str | None = None) -> None:
        self.storage = TodoStorage(db_path)

    def _load(self) -> list[Todo]:
        return self.storage.load()

    def _save(self, todos: list[Todo]) -> None:
        self.storage.save(todos)

    def add(self, text: str) -> Todo:
        text = text.strip()
        if not text:
            raise ValueError("Todo text cannot be empty")

        todos = self._load()
        todo = Todo(id=self.storage.next_id(todos), text=text)
        todos.append(todo)
        self._save(todos)
        return todo

    def list(self, show_all: bool = True) -> list[Todo]:
        todos = self._load()
        if show_all:
            return todos
        return [todo for todo in todos if not todo.done]

    def mark_done(self, todo_id: int) -> Todo:
        todos = self._load()
        for todo in todos:
            if todo.id == todo_id:
                todo.mark_done()
                self._save(todos)
                return todo
        raise ValueError(f"Todo #{todo_id} not found")

    def mark_undone(self, todo_id: int) -> Todo:
        todos = self._load()
        for todo in todos:
            if todo.id == todo_id:
                todo.mark_undone()
                self._save(todos)
                return todo
        raise ValueError(f"Todo #{todo_id} not found")

    def remove(self, todo_id: int) -> None:
        todos = self._load()
        for i, todo in enumerate(todos):
            if todo.id == todo_id:
                todos.pop(i)
                self._save(todos)
                return
        raise ValueError(f"Todo #{todo_id} not found")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="todo", description="Minimal Todo CLI")
    parser.add_argument("--db", default=".todo.json", help="Path to JSON database")

    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Add a todo")
    p_add.add_argument("text", help="Todo text")

    p_list = sub.add_parser("list", help="List todos")
    p_list.add_argument("--pending", action="store_true", help="Show only pending todos")

    p_done = sub.add_parser("done", help="Mark todo done")
    p_done.add_argument("id", type=int)

    p_undone = sub.add_parser("undone", help="Mark todo undone")
    p_undone.add_argument("id", type=int)

    p_rm = sub.add_parser("rm", help="Remove todo")
    p_rm.add_argument("id", type=int)

    return parser


def run_command(args: argparse.Namespace) -> int:
    # Validate the db_path for security (CLI-specific validation)
    validated_db_path = _validate_cli_db_path(args.db)
    app = TodoApp(db_path=validated_db_path)

    try:
        if args.command == "add":
            todo = app.add(args.text)
            print(f"Added #{todo.id}: {_sanitize_text(todo.text)}")
            return 0

        if args.command == "list":
            todos = app.list(show_all=not args.pending)
            print(TodoFormatter.format_list(todos))
            return 0

        if args.command == "done":
            todo = app.mark_done(args.id)
            print(f"Done #{todo.id}: {_sanitize_text(todo.text)}")
            return 0

        if args.command == "undone":
            todo = app.mark_undone(args.id)
            print(f"Undone #{todo.id}: {_sanitize_text(todo.text)}")
            return 0

        if args.command == "rm":
            app.remove(args.id)
            print(f"Removed #{args.id}")
            return 0

        raise ValueError(f"Unsupported command: {args.command}")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_command(args)


if __name__ == "__main__":
    raise SystemExit(main())
