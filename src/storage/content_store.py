"""
Détection de doublons de scripts via Redis (SHA-256 sur full_text).
"""

import hashlib
import redis
from rich.console import Console

from src.config import settings

console = Console()

REDIS_KEY_PREFIX = "content:scripts:"
SCRIPT_TTL_SECONDS = 30 * 24 * 3600  # 30 jours


def _get_redis() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def is_duplicate_script(full_text: str) -> bool:
    """
    Vérifie si un script identique a déjà été produit via SHA-256 du full_text.
    Enregistre le hash dans Redis s'il est nouveau (TTL 30 jours).

    Returns:
        True si le script est un doublon, False sinon.
    """
    try:
        r = _get_redis()
        text_hash = hashlib.sha256(full_text.encode()).hexdigest()
        key = f"{REDIS_KEY_PREFIX}{text_hash}"

        if r.exists(key):
            console.print(f"[yellow]Doublon détecté (hash: {text_hash[:12]}...)[/yellow]")
            return True

        r.setex(key, SCRIPT_TTL_SECONDS, "1")
        return False

    except redis.ConnectionError:
        console.print("[dim]Redis indisponible, vérification doublon ignorée[/dim]")
        return False
