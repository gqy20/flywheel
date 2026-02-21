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

        def add_todo(todos: list[Todo]) -> Todo:
            todo = Todo(id=self.storage.next_id(todos), text=text)
            todos.append(todo)
            return todo

        return self.storage.atomic_read_modify_write(add_todo)

    def list(self, show_all: bool = True) -> list[Todo]:
        todos = self._load()
        if show_all:
            return todos
        return [todo for todo in todos if not todo.done]

    def mark_done(self, todo_id: int) -> Todo:
        def mark_todo_done(todos: list[Todo]) -> Todo:
            for todo in todos:
                if todo.id == todo_id:
                    todo.mark_done()
                    return todo
            raise ValueError(f"Todo #{todo_id} not found")

        return self.storage.atomic_read_modify_write(mark_todo_done)

    def mark_undone(self, todo_id: int) -> Todo:
        def mark_todo_undone(todos: list[Todo]) -> Todo:
            for todo in todos:
                if todo.id == todo_id:
                    todo.mark_undone()
                    return todo
            raise ValueError(f"Todo #{todo_id} not found")

        return self.storage.atomic_read_modify_write(mark_todo_undone)

    def remove(self, todo_id: int) -> None:
        def remove_todo(todos: list[Todo]) -> None:
            for i, todo in enumerate(todos):
                if todo.id == todo_id:
                    todos.pop(i)
                    return
            raise ValueError(f"Todo #{todo_id} not found")

        self.storage.atomic_read_modify_write(remove_todo)


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
