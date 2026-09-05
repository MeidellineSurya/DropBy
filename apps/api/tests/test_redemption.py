import pytest

from app.services.redemption import sign_venue_qr, verify_venue_qr


def test_sign_and_verify_venue_qr_roundtrip() -> None:
    token = sign_venue_qr("drop-123", "business-456")

    claims = verify_venue_qr(token)

    assert claims == {"drop_id": "drop-123", "business_id": "business-456"}


def test_verify_venue_qr_rejects_tampered_signature() -> None:
    token = sign_venue_qr("drop-123", "business-456")
    drop_id, _business_id, iat, nonce, signature = token.split(":")
    tampered = f"{drop_id}:attacker-business:{iat}:{nonce}:{signature}"

    with pytest.raises(ValueError, match="invalid QR signature"):
        verify_venue_qr(tampered)


def test_verify_venue_qr_rejects_malformed_token() -> None:
    with pytest.raises(ValueError, match="malformed QR token"):
        verify_venue_qr("not-a-real-token")


def test_repeated_signing_produces_independently_valid_tokens() -> None:
    """Re-fetching the QR (get_venue_qr) any number of times must never
    invalidate a copy already printed/displayed by the business."""
    first = sign_venue_qr("drop-123", "business-456")
    second = sign_venue_qr("drop-123", "business-456")

    assert first != second
    assert verify_venue_qr(first) == verify_venue_qr(second)
