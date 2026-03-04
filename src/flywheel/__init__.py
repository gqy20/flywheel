"""Minimal flywheel package."""

from flywheel.cli import TodoApp
from flywheel.formatter import TodoFormatter
from flywheel.storage import TodoStorage
from flywheel.todo import Todo

__all__ = ["Todo", "TodoApp", "TodoFormatter", "TodoStorage", "__version__"]

__version__ = "0.1.0"
