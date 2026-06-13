"""Autentificare optionala prin token partajat.

Tokenul se citeste dintr-un fisier pe Pi (implicit /etc/photobackup/api.token).
Daca fisierul lipseste sau e gol => autentificarea e DEZACTIVATA (comportament
identic cu setup-ul fara token), ca sa nu strice instalarile existente.

Cand e activat, clientul trebuie sa trimita tokenul fie prin header
`X-PhotoBackup-Token`, fie prin query param `?token=...` (necesar pentru
incarcarea thumbnail-urilor cu AsyncImage, care nu poate seta headere).
"""
import os
from pathlib import Path

from fastapi import HTTPException, Request

TOKEN_FILE = Path(os.environ.get("PHOTOBACKUP_TOKEN_FILE", "/etc/photobackup/api.token"))


def _expected_token() -> str | None:
    try:
        token = TOKEN_FILE.read_text().strip()
        return token or None
    except OSError:
        return None


async def require_token(request: Request) -> None:
    expected = _expected_token()
    if not expected:
        return  # auth dezactivat
    provided = request.headers.get("X-PhotoBackup-Token") or request.query_params.get("token")
    if provided != expected:
        raise HTTPException(status_code=401, detail="Token API invalid sau lipsa")
