"""Redemption module — venue QR + check-in/confirm flow.

The QR is venue-facing and per-Drop (not per-user): one HMAC-signed token
{drop_id, business_id, iat, nonce} generated once at Drop activation and
displayed/printed by the business for the Drop's whole lifetime.

Flow:
  1. Group reaches "ready" -> a Redemption row is created (status=pending).
  2. Any member scans the venue QR -> verify(token) -> Redemption/Group -> checked_in,
     pushed to the rest of the squad and to ws:business:{business_id}.
  3. Business staff tap Confirm (optionally correcting headcount) ->
     Redemption/Group -> completed, capacity reconciled, award_xp_for_redemption
     Celery task enqueued.
"""

import hashlib
import hmac
import time
import uuid

from app.core.config import settings


def sign_venue_qr(drop_id: str, business_id: str) -> str:
    nonce = uuid.uuid4().hex
    iat = str(int(time.time()))
    message = f"{drop_id}:{business_id}:{iat}:{nonce}"
    signature = hmac.new(settings.qr_signing_secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"{message}:{signature}"


def verify_venue_qr(token: str) -> dict:
    drop_id, business_id, iat, nonce, signature = token.split(":")
    message = f"{drop_id}:{business_id}:{iat}:{nonce}"
    expected = hmac.new(settings.qr_signing_secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise ValueError("invalid QR signature")
    return {"drop_id": drop_id, "business_id": business_id}


def check_in_group(group_id: str, qr_token: str) -> str:
    """Verify the QR, ensure it matches the Group's Drop, transition to checked_in."""
    raise NotImplementedError


def confirm_redemption(redemption_id: str, confirmed_by_business_user: str, participant_count: int) -> None:
    """Complete the Group, reconcile capacity, enqueue award_xp_for_redemption."""
    raise NotImplementedError
