"""The pending-approval store."""

from __future__ import annotations

import datetime

from app import approvals
from app.approvals import ApprovalStore


def store(**kwargs) -> ApprovalStore:
    base = {"ttl_seconds": 3600, "max_pending": 10}
    base.update(kwargs)
    return ApprovalStore(**base)


def add(s: ApprovalStore, client_id: str = "c"):
    return s.add(client_id=client_id, reason="r", content="text", state={"full": "state"})


class TestBasics:
    def test_added_items_are_listed_in_order(self):
        s = store()
        first = add(s, "a")
        second = add(s, "b")
        assert [item.approval_id for item in s.list()] == [first.approval_id, second.approval_id]

    def test_pop_removes_the_item(self):
        s = store()
        item = add(s)
        assert s.pop(item.approval_id) is item
        assert s.pop(item.approval_id) is None
        assert len(s) == 0

    def test_ids_are_unguessable_and_unique(self):
        s = store()
        ids = {add(s).approval_id for _ in range(5)}
        assert len(ids) == 5
        assert all(len(i) == 32 for i in ids)

    def test_the_summary_excludes_the_graph_state(self):
        item = add(store())
        assert "full" not in str(item.summary())
        assert set(item.summary()) == {
            "approval_id",
            "client_id",
            "reason",
            "content",
            "created_at",
        }


class TestExpiry:
    def test_old_items_expire(self, monkeypatch):
        s = store(ttl_seconds=60)
        item = add(s)
        later = item.created_at + datetime.timedelta(seconds=61)
        monkeypatch.setattr(approvals, "_now", lambda: later)
        assert s.list() == []
        assert s.pop(item.approval_id) is None

    def test_fresh_items_do_not(self, monkeypatch):
        s = store(ttl_seconds=60)
        item = add(s)
        monkeypatch.setattr(
            approvals, "_now", lambda: item.created_at + datetime.timedelta(seconds=59)
        )
        assert len(s) == 1


class TestBound:
    def test_the_oldest_item_is_dropped_at_capacity(self):
        s = store(max_pending=2)
        first = add(s, "first")
        add(s, "second")
        add(s, "third")
        assert len(s) == 2
        assert s.pop(first.approval_id) is None
