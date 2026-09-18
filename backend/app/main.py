from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.reference import router as reference_router
from app.api.routes.reports import router as reports_router
from app.api.routes.tickets import router as tickets_router
from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.models import Base
from app.models.department import Department
from app.services.sla import ensure_default_policies

logger = logging.getLogger(__name__)

DEFAULT_DEPARTMENTS = [
    ("RH", "Ressources Humaines"),
    ("FIN", "Finance"),
    ("REC", "Recouvrement"),
    ("IT", "Informatique"),
    ("COM", "Commercialisation"),
    ("OPS", "Operations"),
    ("DIR", "Direction"),
]


def _seed_departments() -> None:
    with SessionLocal() as db:
        existing_codes = {item.code for item in db.scalars(select(Department)).all()}
        for code, name in DEFAULT_DEPARTMENTS:
            if code in existing_codes:
                continue
            db.add(Department(code=code, name=name, is_active=True))
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
        _seed_departments()
        with SessionLocal() as db:
            ensure_default_policies(db)
        logger.info("Database ready (auto_create_tables enabled)")
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(tickets_router, prefix=settings.api_v1_prefix)
app.include_router(reference_router, prefix=settings.api_v1_prefix)
app.include_router(reports_router, prefix=settings.api_v1_prefix)
app.include_router(admin_router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

