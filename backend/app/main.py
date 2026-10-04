"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import Base, engine
from app.routers import admin, auth, dashboard, profile, tasks
from app.seed import seed_root_admin_from_settings

# Create tables if they don't exist yet. Alembic (see alembic/) is the source of
# truth for schema migrations in a real deployment; this is a convenience for
# quick local/dev boot and for the test suite.
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_: FastAPI):
    seed_root_admin_from_settings()
    yield


app = FastAPI(
    title="Smart Student Task Manager API",
    description=(
        "Backend for the Smart Student Task Manager: students create tasks "
        "(assignments/exams/projects), the system scores and classifies task "
        "priority, and recommends what to work on next. Admins manage all "
        "users and tasks under /admin."
    ),
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """NFR-07: turn Pydantic's validation errors into clear, readable messages."""
    errors = []
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err["loc"] if loc != "body")
        errors.append({"field": field, "message": err["msg"]})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Please check the highlighted fields.", "errors": errors},
    )


app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(dashboard.router)
app.include_router(profile.router)
app.include_router(admin.router)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
