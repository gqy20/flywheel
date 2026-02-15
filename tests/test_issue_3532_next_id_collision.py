"""Test for issue #3532: next_id() should not return existing IDs.

Bug: next_id() returns max(id) + 1, which is ALWAYS safe from collision
since max(id) + 1 cannot equal any existing ID (it's larger than all of them).

The ACTUAL bug described in the issue is different - it's a misunderstanding.
Let me re-read: "next_id() 会返回已存在的 ID（ID 碰撞），当 JSON 文件中存在非连续或已删除的 ID 时"

Reading again - the issue suggests that with non-contiguous IDs like [1, 3],
the next_id should return 2 (filling the gap) or 4, but NOT collide.

Actually wait - max([1, 3]) + 1 = 4, which is safe. The issue might be referring
to a DIFFERENT scenario that I'm not seeing yet.

Let me check the acceptance criteria:
- 当存在 ID 空洞时（如 [1, 3, 5]），next_id() 返回不存在的 ID（应为 6 或 2，而非 4）
  -> With [1, 3, 5], max+1 = 6, which is correct! Not 4.

Actually I think I misunderstand the bug. Let me trace through what happens:
1. User adds todo with id=1
2. User adds todo with id=2
3. User deletes todo id=2
4. Now we have [1] in storage
5. User adds new todo: next_id([1]) = 2
6. User adds another: next_id([1, 2]) = 3
7. Delete id=2 again
8. Now we have [1, 3]
9. Add new: next_id([1, 3]) = 4

Hmm, there's no collision here. Let me check if the bug is in the suggested
fix's logic or if there's an actual edge case.

Ah! I see it now. The issue says the current code is:
  return (max((todo.id for todo in todos), default=0) + 1) if todos else 1

This is max+1 which is ALWAYS safe. But the suggested fix adds a while loop
to handle the case where max+1 might collide - but that can't happen!

The REAL issue might be:
1. If the JSON file is manually edited to have duplicate IDs
2. Or if there's concurrent access

For now, let's add a regression test that verifies the invariant:
"next_id() should NEVER return an ID that already exists"
"""

from __future__ import annotations

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_next_id_never_collides_with_existing_ids() -> None:
    """Issue #3532: next_id must return an ID that doesn't exist.

    This is the core invariant: whatever next_id returns must not
    already be in the list of existing IDs.
    """
    storage = TodoStorage()

    # Test various ID configurations
    test_cases = [
        [Todo(id=1, text="a")],
        [Todo(id=1, text="a"), Todo(id=2, text="b")],
        [Todo(id=1, text="a"), Todo(id=3, text="b")],  # gap at 2
        [Todo(id=1, text="a"), Todo(id=3, text="b"), Todo(id=5, text="c")],  # gaps
        [Todo(id=5, text="starts high")],
        [Todo(id=1, text="a"), Todo(id=100, text="b")],
    ]

    for todos in test_cases:
        next_id = storage.next_id(todos)
        used_ids = {todo.id for todo in todos}
        assert next_id not in used_ids, (
            f"next_id={next_id} collides with existing IDs {used_ids}"
        )


def test_next_id_empty_list_returns_1() -> None:
    """Issue #3532: empty list should return ID 1."""
    storage = TodoStorage()

    next_id = storage.next_id([])

    assert next_id == 1, "Empty list should return ID 1"


def test_next_id_continuous_sequence() -> None:
    """Issue #3532: continuous IDs [1,2,3] should return 4."""
    storage = TodoStorage()

    todos = [Todo(id=1, text="a"), Todo(id=2, text="b"), Todo(id=3, text="c")]

    next_id = storage.next_id(todos)

    assert next_id == 4, f"Expected next_id=4 for [1,2,3], got {next_id}"


def test_next_id_with_gaps() -> None:
    """Issue #3532: IDs with gaps should return non-colliding ID.

    Acceptance criteria: when IDs have gaps like [1, 3, 5],
    next_id should return a non-existing ID (6 or 2, but not 4).

    Current behavior: max([1, 3, 5]) + 1 = 6, which is correct.
    """
    storage = TodoStorage()

    todos = [Todo(id=1, text="a"), Todo(id=3, text="b"), Todo(id=5, text="c")]

    next_id = storage.next_id(todos)
    used_ids = {todo.id for todo in todos}

    assert next_id not in used_ids, f"next_id={next_id} collides with existing IDs"
    # Current implementation returns 6 (max+1)
    assert next_id == 6, f"Expected next_id=6, got {next_id}"


def test_next_id_after_remove_scenario() -> None:
    """Issue #3532: test the add/remove scenario.

    Scenario from issue:
    1. Create todos [1, 2, 3]
    2. Delete id=2
    3. Add new todo -> should get id=4 (not 3)

    Current behavior: max([1, 3]) + 1 = 4, which is correct.
    """
    storage = TodoStorage()

    # Simulate after removing id=2 from [1, 2, 3]
    todos = [Todo(id=1, text="a"), Todo(id=3, text="c")]

    next_id = storage.next_id(todos)
    used_ids = {todo.id for todo in todos}

    assert next_id not in used_ids, f"next_id={next_id} collides with existing IDs"
    # Should be 4, not 3
    assert next_id == 4, f"Expected next_id=4, got {next_id}"
