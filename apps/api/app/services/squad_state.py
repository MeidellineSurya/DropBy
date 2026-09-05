"""Discovery module — Group ("Squad") state machine.

forming -> (count >= min_required) -> ready -> (venue QR scan) -> checked_in
        -> (business confirms) -> completed
forming/ready -> expired/cancelled (timeout, Drop expiry, leader/business cancel)

Entering "ready" must atomically reserve capacity via
services.drop_lifecycle.reserve_capacity(); if that fails (another Group
raced the last spots), move this Group to "cancelled" and notify members
instead of "ready".
"""


def create_group(drop_id: str, created_by_user_id: str) -> str:
    raise NotImplementedError


def join_group(group_id: str, user_id: str) -> None:
    """Add a member, recompute status, broadcast group.state_update, and
    transition to "ready" (with capacity reservation) if the threshold is met."""
    raise NotImplementedError
