from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class BookingAlreadyPostedError(AppError):
    status_code = 422
    code = "BOOKING_ALREADY_POSTED"

    def __init__(self) -> None:
        super().__init__("Cannot modify a posted booking. Use reversal instead.")


class PeriodLockedError(AppError):
    status_code = 422
    code = "PERIOD_LOCKED"

    def __init__(self) -> None:
        super().__init__("The accounting period is locked or archived.")


class AccountNotEditableError(AppError):
    status_code = 422
    code = "ACCOUNT_NOT_EDITABLE"

    def __init__(self) -> None:
        super().__init__(
            "Seed accounts are read-only except for private_share_percent and is_active."
        )


class InvoiceImmutableError(AppError):
    status_code = 403
    code = "INVOICE_IMMUTABLE"

    def __init__(self) -> None:
        super().__init__("Issued or cancelled invoices are immutable (GoBD §14).")


class InvalidInvoiceStateError(AppError):
    status_code = 400
    code = "INVALID_INVOICE_STATE"


class EmailSendError(AppError):
    status_code = 502
    code = "EMAIL_SEND_FAILED"


class AccountLookupError(AppError):
    status_code = 500
    code = "ACCOUNT_LOOKUP_FAILED"


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )
