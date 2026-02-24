"""Minimal Todo CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import filelock

from .formatter import TodoFormatter, _sanitize_text
from .storage import TodoStorage
from .todo import Todo

# Default timeout for lock acquisition (in seconds)
DEFAULT_LOCK_TIMEOUT = 30.0


class TodoApp:
    """Simple in-process todo application with file-based locking.

    Uses filelock to prevent race conditions when multiple processes
    access the same todo file concurrently. The lock ensures that
    load-modify-save operations are atomic.
    """

    def __init__(
        self, db_path: str | None = None, lock_timeout: float = DEFAULT_LOCK_TIMEOUT
    ) -> None:
        self.storage = TodoStorage(db_path)
        self._lock_timeout = lock_timeout
        # Lock file is stored alongside the database file
        lock_path = Path(self.storage.path).with_suffix(self.storage.path.suffix + ".lock")
        self._lock = filelock.FileLock(str(lock_path))

    def _with_lock(self, operation: str) -> filelock.FileLock:
        """Get the file lock for the given operation.

        Returns the lock context manager for use in 'with' statements.
        """
        return self._lock

    def add(self, text: str) -> Todo:
        text = text.strip()
        if not text:
            raise ValueError("Todo text cannot be empty")

        with self._lock.acquire(timeout=self._lock_timeout):
            todos = self.storage.load()
            todo = Todo(id=self.storage.next_id(todos), text=text)
            todos.append(todo)
            self.storage.save(todos)
        return todo

    def list(self, show_all: bool = True) -> list[Todo]:
        # Read operations also need locking to ensure consistency
        # with concurrent write operations
        with self._lock.acquire(timeout=self._lock_timeout):
            todos = self.storage.load()
        if show_all:
            return todos
        return [todo for todo in todos if not todo.done]

    def mark_done(self, todo_id: int) -> Todo:
        with self._lock.acquire(timeout=self._lock_timeout):
            todos = self.storage.load()
            for todo in todos:
                if todo.id == todo_id:
                    todo.mark_done()
                    self.storage.save(todos)
                    return todo
        raise ValueError(f"Todo #{todo_id} not found")

    def mark_undone(self, todo_id: int) -> Todo:
        with self._lock.acquire(timeout=self._lock_timeout):
            todos = self.storage.load()
            for todo in todos:
                if todo.id == todo_id:
                    todo.mark_undone()
                    self.storage.save(todos)
                    return todo
        raise ValueError(f"Todo #{todo_id} not found")

    def remove(self, todo_id: int) -> None:
        with self._lock.acquire(timeout=self._lock_timeout):
            todos = self.storage.load()
            for i, todo in enumerate(todos):
                if todo.id == todo_id:
                    todos.pop(i)
                    self.storage.save(todos)
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
    app = TodoApp(db_path=args.db)

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
