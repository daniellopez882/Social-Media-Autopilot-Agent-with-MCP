"""
Pending human approvals.

The previous store was ``PENDING_APPROVALS = {}`` at module level in
``main.py``: no expiry, no bound, no way to list what was in it. The dashboard
could only show approvals created in the same browser session, because there
was no ``GET`` for them; a page reload orphaned every pending item on the
server, where it then lived until the process died.

This is still process memory -- a restart loses pending items, and two
replicas would not share them. That is stated in the README rather than hidden
behind a database import that nothing used (``sqlalchemy`` was in
requirements.txt and imported by nothing).
"""

from __future__ import annotations

import datetime
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


@dataclass
class PendingApproval:
    approval_id: str
    client_id: str
    reason: str
    content: str
    state: dict[str, Any]
    created_at: datetime.datetime = field(default_factory=_now)

    def summary(self) -> dict[str, Any]:
        """What the dashboard needs. The full graph state stays server-side."""
        return {
            "approval_id": self.approval_id,
            "client_id": self.client_id,
            "reason": self.reason,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
        }


class ApprovalStore:
    def __init__(self, *, ttl_seconds: int, max_pending: int) -> None:
        self._ttl = datetime.timedelta(seconds=ttl_seconds)
        self._max = max_pending
        self._items: dict[str, PendingApproval] = {}
        self._lock = threading.Lock()

    def _expire(self) -> None:
        cutoff = _now() - self._ttl
        for key in [k for k, v in self._items.items() if v.created_at < cutoff]:
            del self._items[key]

    def add(
        self, *, client_id: str, reason: str, content: str, state: dict[str, Any]
    ) -> PendingApproval:
        with self._lock:
            self._expire()
            if len(self._items) >= self._max:
                # Drop the oldest rather than refuse: an approval queue that
                # rejects new items under load hides the newest problems.
                oldest = min(self._items.values(), key=lambda item: item.created_at)
                del self._items[oldest.approval_id]
            item = PendingApproval(
                approval_id=uuid.uuid4().hex,
                client_id=client_id,
                reason=reason,
                content=content,
                state=state,
            )
            self._items[item.approval_id] = item
            return item

    def pop(self, approval_id: str) -> PendingApproval | None:
        with self._lock:
            self._expire()
            return self._items.pop(approval_id, None)

    def list(self) -> list[PendingApproval]:
        with self._lock:
            self._expire()
            return sorted(self._items.values(), key=lambda item: item.created_at)

    def __len__(self) -> int:
        with self._lock:
            self._expire()
            return len(self._items)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
