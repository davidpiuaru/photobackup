"""Notificari pentru polling din app."""
from fastapi import APIRouter

from ..models import Notification
from ..services import status_reader

router = APIRouter(prefix="/api/notifications")


@router.get("", response_model=list[Notification])
def list_notifications(since_id: int = 0, limit: int = 50) -> list[Notification]:
    notifs = status_reader.read().get("notifications", [])
    filtered = [n for n in notifs if int(n.get("id", 0)) > since_id]
    return [Notification(**n) for n in filtered[-limit:]]
