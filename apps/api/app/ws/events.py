"""Re-exports the frozen WS event contract from packages/ws-contracts so the
API layer never redefines event shapes locally. See packages/ws-contracts/ws_contracts/events.py
for the canonical definitions consumed by both frontends.
"""

from ws_contracts.events import (  # noqa: F401
    BadgeUnlocked,
    DropCapacityReached,
    DropCountdownWarning,
    DropExpired,
    DropStageUpdate,
    GroupMemberJoined,
    GroupReady,
    GroupStateUpdate,
    RedemptionCheckedIn,
    RedemptionConfirmed,
)
