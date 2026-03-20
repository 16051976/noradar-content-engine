"""
Détection de doublons de scripts via Redis.
"""

import hashlib
import redis
from rich.console import Console

from src.config import settings
from src.models import Script

console = Console()

REDIS_KEY_PREFIX = "noradar:script:"
SCRIPT_TTL_SECONDS = 30 * 24 * 3600  # 30 jours


def _get_redis() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def _script_fingerprint(script: Script) -> str:
    """Hash du hook normalisé pour détecter les doublons."""
    normalized = script.hook.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def is_duplicate_script(script: Script) -> bool:
    """
    Vérifie si un script avec un hook similaire a déjà été produit.
    Enregistre le script dans Redis s'il est nouveau.

    Returns:
        True si le hook est un doublon, False sinon.
    """
    try:
        r = _get_redis()
        fingerprint = _script_fingerprint(script)
        key = f"{REDIS_KEY_PREFIX}{fingerprint}"

        if r.exists(key):
            console.print(f"[yellow]⚠ Doublon détecté (hook: {script.hook[:50]}...)[/yellow]")
            return True

        r.setex(key, SCRIPT_TTL_SECONDS, script.hook)
        return False

    except redis.ConnectionError:
        console.print("[dim]Redis indisponible, vérification doublon ignorée[/dim]")
        return False
