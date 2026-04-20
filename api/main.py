"""FastAPI server pentru PhotoBackup — expus pe :8080 pentru app-ul iOS."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import backup, notifications, sessions, status, sync, thumbnails, wifi

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

app = FastAPI(title="PhotoBackup API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(status.router)
app.include_router(wifi.router)
app.include_router(backup.router)
app.include_router(sync.router)
app.include_router(sessions.router)
app.include_router(thumbnails.router)
app.include_router(notifications.router)


@app.get("/api/ping")
def ping() -> dict:
    return {"ok": True, "service": "photobackup-api"}


@app.on_event("startup")
async def on_startup():
    log.info("PhotoBackup API pornit")
