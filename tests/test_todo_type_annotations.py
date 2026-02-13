"""Test for precise type annotations on Todo.to_dict method.

This test verifies issue #3043: to_dict return type annotation should be
dict[str, Any] instead of bare dict for better type safety with static
type checkers.
"""

from __future__ import annotations

from typing import Any, get_type_hints

from flywheel.todo import Todo


def test_to_dict_return_type_has_generic_parameters() -> None:
    """Verify to_dict returns dict[str, Any] with generic type parameters.

    Regression test for issue #3043: The return type annotation should be
    dict[str, Any] instead of bare dict for better type safety.
    """
    # Get the type hints for the to_dict method
    hints = get_type_hints(Todo.to_dict)

    # The return type should be dict[str, Any], not bare dict
    return_type = hints.get("return")

    # Verify it's a dict with type parameters
    assert return_type is not None, "Return type annotation missing"

    # Check that the return type is dict[str, Any]
    # get_origin gives us dict, get_args gives us (str, Any)
    from typing import get_args, get_origin

    origin = get_origin(return_type)
    args = get_args(return_type)

    # Should be dict (not the bare dict class without parameters)
    assert origin is dict, f"Return type origin should be dict, got {origin}"

    # Should have type parameters [str, Any]
    assert len(args) == 2, f"Expected 2 type arguments, got {len(args)}: {args}"
    assert args[0] is str, f"Key type should be str, got {args[0]}"
    assert args[1] is Any, f"Value type should be Any, got {args[1]}"


def test_to_dict_returns_correct_dict_structure() -> None:
    """Verify to_dict returns a dict with the expected structure."""
    todo = Todo(id=1, text="Test todo", done=True)
    result = todo.to_dict()

    # Verify the result is a dict with string keys
    assert isinstance(result, dict)
    assert all(isinstance(k, str) for k in result.keys())

    # Verify expected keys exist
    assert "id" in result
    assert "text" in result
    assert "done" in result
    assert "created_at" in result
    assert "updated_at" in result
