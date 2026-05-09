from app.errors import (
    NotFoundError,
    BookingAlreadyPostedError,
    PeriodLockedError,
)


async def test_not_found_error_returns_json_shape(client) -> None:
    """Test that NotFoundError returns correct JSON structure."""
    from app.main import app

    @app.get("/test-error")
    async def raise_error() -> None:
        raise NotFoundError("Test resource not found")

    response = await client.get("/test-error")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["message"] == "Test resource not found"
    assert "details" in body["error"]


def test_booking_already_posted_error() -> None:
    """Test BookingAlreadyPostedError has correct status and message."""
    err = BookingAlreadyPostedError()
    assert err.status_code == 422
    assert err.code == "BOOKING_ALREADY_POSTED"
    assert "reversal" in err.message.lower()


def test_period_locked_error() -> None:
    """Test PeriodLockedError has correct status and message."""
    err = PeriodLockedError()
    assert err.status_code == 422
    assert err.code == "PERIOD_LOCKED"
    assert "locked" in err.message.lower()
