"""Minimal Todo CLI."""

from __future__ import annotations

import argparse
import sys

from .formatter import TodoFormatter, _sanitize_text
from .storage import TodoStorage
from .todo import Todo


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
        kept = [todo for todo in todos if todo.id != todo_id]
        if len(kept) == len(todos):
            raise ValueError(f"Todo #{todo_id} not found")
        self._save(kept)


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

    p_repair = sub.add_parser("repair", help="Repair corrupted JSON database")
    p_repair.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate without making changes",
    )

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

        if args.command == "repair":
            return _run_repair(args)

        raise ValueError(f"Unsupported command: {args.command}")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _run_repair(args: argparse.Namespace) -> int:
    """Run the repair command.

    Args:
        args: Parsed command-line arguments with --db and --dry-run options.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    storage = TodoStorage(args.db)

    # First validate
    is_valid, error = storage.validate()

    if is_valid:
        print(f"Database '{args.db}' is valid.")
        if storage.path.exists():
            todos = storage.load()
            print(f"Found {len(todos)} todo(s).")
        return 0

    # File is invalid
    if args.dry_run:
        print(f"Database '{args.db}' is INVALID: {error}")
        print("Use 'todo repair --db=path' (without --dry-run) to attempt repair.")
        return 1

    # Attempt repair
    print(f"Database '{args.db}' is INVALID: {error}")
    print("Attempting repair...")

    recovered = storage.repair()

    if recovered > 0:
        todos = storage.load()
        print(f"Repair successful: recovered {recovered} todo(s).")
        print(f"Total todos after repair: {len(todos)}.")
        # Check if backup was created
        backup_path = storage.path.with_suffix(storage.path.suffix + ".recovered.json")
        if backup_path.exists():
            print(f"Backup created: {backup_path}")
        return 0
    else:
        print("Repair complete: no valid todos could be recovered.")
        print("Database file has been reset to an empty state.")
        backup_path = storage.path.with_suffix(storage.path.suffix + ".recovered.json")
        if backup_path.exists():
            print(f"Original corrupted content saved to: {backup_path}")
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_command(args)


if __name__ == "__main__":
    raise SystemExit(main())
