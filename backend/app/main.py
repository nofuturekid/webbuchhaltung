from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.errors import AppError, app_error_handler
from app.routers import accounts as accounts_router
from app.routers import admin as admin_router
from app.routers import auth as auth_router
from app.routers import bookings as bookings_router
from app.routers import mandants as mandants_router
from app.routers import periods as periods_router
from app.routers import customers as customers_router
from app.routers import datev as datev_router
from app.routers import invoice_template as invoice_template_router
from app.routers import invoices as invoices_router
from app.routers import reports as reports_router
from app.routers import tax_keys as tax_keys_router

app = FastAPI(title="WebBuchhaltung API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)

app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(mandants_router.router, prefix="/api/v1")
app.include_router(admin_router.router, prefix="/api/v1")
app.include_router(accounts_router.router, prefix="/api/v1")
app.include_router(tax_keys_router.router, prefix="/api/v1")
app.include_router(bookings_router.router, prefix="/api/v1")
app.include_router(periods_router.router, prefix="/api/v1")
app.include_router(reports_router.router, prefix="/api/v1")
app.include_router(datev_router.router, prefix="/api/v1")
app.include_router(customers_router.router, prefix="/api/v1")
app.include_router(invoices_router.router, prefix="/api/v1")
app.include_router(invoice_template_router.router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
