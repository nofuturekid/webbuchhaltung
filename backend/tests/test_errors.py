from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.errors import (
    AccountNotEditableError,
    AppError,
    BookingAlreadyPostedError,
    NotFoundError,
    PeriodLockedError,
    app_error_handler,
)

_test_app = FastAPI()
_test_app.add_exception_handler(AppError, app_error_handler)


@_test_app.get("/test-error")
async def _raise_error() -> None:
    raise NotFoundError("Test resource not found")


async def test_not_found_error_returns_json_shape() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=_test_app), base_url="http://test"
    ) as ac:
        response = await ac.get("/test-error")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["message"] == "Test resource not found"
    assert "details" in body["error"]


def test_booking_already_posted_error() -> None:
    err = BookingAlreadyPostedError()
    assert err.status_code == 422
    assert err.code == "BOOKING_ALREADY_POSTED"
    assert "reversal" in err.message.lower()


def test_period_locked_error() -> None:
    err = PeriodLockedError()
    assert err.status_code == 422
    assert err.code == "PERIOD_LOCKED"
    assert "locked" in err.message.lower()


def test_account_not_editable_error() -> None:
    err = AccountNotEditableError()
    assert err.status_code == 422
    assert err.code == "ACCOUNT_NOT_EDITABLE"
    assert "read-only" in err.message.lower()
