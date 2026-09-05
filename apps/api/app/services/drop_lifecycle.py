"""Discovery module — Drop state machine.

draft -> scheduled -> active -> {capacity_reached, expired} -> completed
draft/scheduled/active -> cancelled (cascades to in-flight groups)

Only this module writes Drop.status / Drop.reserved_count. Capacity
reservation must be a single atomic UPDATE ... WHERE reserved_count + :n <=
max_capacity_participants RETURNING reserved_count — never a read-then-write,
since two Groups can race to reach "ready" on the same Drop concurrently.
"""


def activate_drop(drop_id: str) -> None:
    """Flip scheduled -> active, generate the venue QR (via services.redemption),
    and schedule the 5-minute countdown warning task."""
    raise NotImplementedError


def reserve_capacity(drop_id: str, count: int) -> bool:
    """Atomically reserve `count` spots; returns False if capacity was already taken."""
    raise NotImplementedError


def release_capacity(drop_id: str, count: int) -> None:
    raise NotImplementedError


def cancel_drop(drop_id: str) -> None:
    raise NotImplementedError
