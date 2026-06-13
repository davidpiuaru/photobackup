"""FastAPI server pentru PhotoBackup — expus pe :8080 pentru app-ul iOS."""
import logging
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import backup, notifications, rating, sessions, status, sync, thumbnails, wifi
from .services.auth import require_token

LOG_FILE = Path("/var/log/photobackup-api.log")


def _setup_logging() -> None:
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(RotatingFileHandler(LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=3))
    except OSError:
        pass
    for h in handlers:
        h.setFormatter(fmt)
    logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)


_setup_logging()
log = logging.getLogger("photobackup.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("PhotoBackup API pornit")
    yield


app = FastAPI(title="PhotoBackup API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Token optional (dezactivat daca nu exista fisierul de token) pe toate rutele
# de date/control. /api/ping ramane deschis pentru discovery.
_auth = [Depends(require_token)]
app.include_router(status.router, dependencies=_auth)
app.include_router(wifi.router, dependencies=_auth)
app.include_router(backup.router, dependencies=_auth)
app.include_router(sync.router, dependencies=_auth)
app.include_router(sessions.router, dependencies=_auth)
app.include_router(thumbnails.router, dependencies=_auth)
app.include_router(thumbnails.preview_router, dependencies=_auth)
app.include_router(notifications.router, dependencies=_auth)
app.include_router(rating.router, dependencies=_auth)


@app.get("/api/ping")
def ping() -> dict:
    return {"ok": True, "service": "photobackup-api"}
