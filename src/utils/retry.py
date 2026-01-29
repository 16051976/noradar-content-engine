"""
Retry automatique avec backoff exponentiel pour les appels API.
"""

import time
import functools
from rich.console import Console

console = Console()


def with_retry(exceptions=(Exception,)):
    """
    Décorateur retry avec backoff exponentiel.
    Lit retry_enabled, retry_max_attempts, retry_backoff_seconds depuis config.
    Si retry_enabled=False, exécute la fonction normalement (zéro impact).
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from src.config import settings

            if not settings.retry_enabled:
                return func(*args, **kwargs)

            max_attempts = settings.retry_max_attempts
            backoff = settings.retry_backoff_seconds
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        console.print(
                            f"[red]✗ {func.__name__} : échec après {max_attempts} tentatives[/red]"
                        )
                        raise
                    delay = backoff * (2 ** (attempt - 1))
                    console.print(
                        f"[yellow]⚠ {func.__name__} : tentative {attempt}/{max_attempts} "
                        f"échouée ({type(e).__name__}), retry dans {delay:.1f}s...[/yellow]"
                    )
                    time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator
