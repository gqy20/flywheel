"""Command-line interface for todo CLI."""

import argparse
import logging
import sys
from datetime import datetime

from flywheel.formatter import Formatter, FormatType
from flywheel.storage import Storage
from flywheel.todo import Priority, Status, Todo

logger = logging.getLogger(__name__)


class CLI:
    """Todo CLI application."""

    def __init__(self):
        self.storage = Storage()

    def add(self, args: argparse.Namespace) -> None:
        """Add a new todo."""
        todo = Todo(
            id=None,  # Let storage.generate ID atomically
            title=args.title,
            description=args.description or "",
            priority=Priority(args.priority) if args.priority else Priority.MEDIUM,
            due_date=args.due_date,
            tags=(args.tags or []).split(",") if args.tags else [],
        )

        added_todo = self.storage.add(todo)
        print(f"✓ Added todo #{added_todo.id}: {added_todo.title}")

    def list(self, args: argparse.Namespace) -> None:
        """List todos."""
        status_filter = args.status

        if args.all:
            todos = self.storage.list()
        elif status_filter:
            todos = self.storage.list(status_filter)
        else:
            # By default, show only incomplete todos
            todos = [t for t in self.storage.list() if t.status != Status.DONE]

        # Sort by priority
        priority_order = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
        todos.sort(key=lambda t: (priority_order.get(t.priority, 99), t.id))

        formatter = Formatter(FormatType(args.format) if args.format else FormatType.TABLE)
        print(formatter.format(todos))

    def complete(self, args: argparse.Namespace) -> None:
        """Mark a todo as complete."""
        todo = self.storage.get(args.id)
        if not todo:
            print(f"✗ Todo #{args.id} not found")
            sys.exit(1)

        todo.status = Status.DONE
        todo.completed_at = datetime.now().isoformat()
        self.storage.update(todo)
        print(f"✓ Completed todo #{args.id}: {todo.title}")

    def delete(self, args: argparse.Namespace) -> None:
        """Delete a todo."""
        if self.storage.delete(args.id):
            print(f"✓ Deleted todo #{args.id}")
        else:
            print(f"✗ Todo #{args.id} not found")
            sys.exit(1)

    def update(self, args: argparse.Namespace) -> None:
        """Update a todo."""
        todo = self.storage.get(args.id)
        if not todo:
            print(f"✗ Todo #{args.id} not found")
            sys.exit(1)

        if args.title:
            todo.title = args.title
        if args.description is not None:
            todo.description = args.description
        if args.status:
            todo.status = Status(args.status)
        if args.priority:
            todo.priority = Priority(args.priority)

        self.storage.update(todo)
        print(f"✓ Updated todo #{args.id}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="AI Flywheel Todo CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new todo")
    add_parser.add_argument("title", help="Todo title")
    add_parser.add_argument("-d", "--description", help="Todo description")
    add_parser.add_argument("-p", "--priority", choices=["low", "medium", "high"])
    add_parser.add_argument("--due-date", help="Due date (ISO format)")
    add_parser.add_argument("-t", "--tags", help="Comma-separated tags")

    # List command
    list_parser = subparsers.add_parser("list", help="List todos")
    list_parser.add_argument("-a", "--all", action="store_true", help="Show all todos")
    list_parser.add_argument("-s", "--status", choices=["todo", "in_progress", "done"])
    list_parser.add_argument("-f", "--format", choices=["table", "json", "compact"])

    # Complete command
    complete_parser = subparsers.add_parser("complete", help="Mark todo as complete")
    complete_parser.add_argument("id", type=int, help="Todo ID")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a todo")
    delete_parser.add_argument("id", type=int, help="Todo ID")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update a todo")
    update_parser.add_argument("id", type=int, help="Todo ID")
    update_parser.add_argument("-t", "--title", help="New title")
    update_parser.add_argument("-d", "--description", help="New description")
    update_parser.add_argument("-s", "--status", choices=["todo", "in_progress", "done"])
    update_parser.add_argument("-p", "--priority", choices=["low", "medium", "high"])

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cli = CLI()
    command = getattr(cli, args.command)
    command(args)


if __name__ == "__main__":
    main()
