import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import AsyncSessionLocal
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
from app.routers import setup as setup_router

logger = logging.getLogger(__name__)

_VALID_SKR_VARIANTS = {"skr03", "skr04", "skr07"}


async def _run_env_bootstrap() -> None:
    """Bootstrap the first admin user from environment variables if configured."""
    email = settings.bootstrap_admin_email
    password = settings.bootstrap_admin_password

    if not email or not password:
        return

    skr_variant = settings.bootstrap_skr_variant
    if skr_variant not in _VALID_SKR_VARIANTS:
        logger.warning(
            "Bootstrap skipped — invalid skr_variant %r (must be one of %s)",
            skr_variant,
            ", ".join(sorted(_VALID_SKR_VARIANTS)),
        )
        return

    from app.services.bootstrap import bootstrap_first_admin, system_needs_bootstrap

    async with AsyncSessionLocal() as session:
        try:
            needs = await system_needs_bootstrap(session)
            if not needs:
                logger.info("Bootstrap skipped — users already exist")
                return

            await bootstrap_first_admin(
                session,
                email=email,
                password=password,
                mandant_name=settings.bootstrap_mandant_name,
                skr_variant=skr_variant,
            )
            await session.commit()
            logger.info("Bootstrap complete: %s", email)
        except IntegrityError:
            # Race condition: another replica already bootstrapped.
            logger.info("Bootstrap skipped — concurrent bootstrap detected")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await _run_env_bootstrap()
    yield


app = FastAPI(title="WebBuchhaltung API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)

app.include_router(setup_router.router, prefix="")
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
