"""
Calcul de la distribution hebdomadaire des formats vidéo
basée sur les scores de performance analytics.
"""

from typing import Optional

from src.models import VideoFormat

from src.analytics.performance import PerformanceData

# Distribution par défaut (identique au CLAUDE.md / produce_weekly existant)
DEFAULT_RATIOS: dict[VideoFormat, float] = {
    VideoFormat.STORY_POV: 0.27,
    VideoFormat.DEBUNK: 0.20,
    VideoFormat.CAS_REEL: 0.20,
    VideoFormat.SCANDALE: 0.13,
    VideoFormat.TUTO: 0.10,
    VideoFormat.TEMOIGNAGE: 0.05,
    VideoFormat.MYTHE: 0.05,
}

MAX_FORMAT_RATIO = 0.35  # Un format ne peut pas dépasser 35% du total
MIN_FORMAT_RATIO = 0.05  # Un format ne peut pas descendre sous 5%


def compute_distribution(
    total: int,
    performance: Optional[PerformanceData],
) -> dict[VideoFormat, int]:
    """
    Calcule la distribution {VideoFormat: count} pour un total donné.

    Si performance est None ou scores vides : retourne la distribution par défaut.
    Sinon : pondère par les scores, avec clamp min 5% / max 35%.
    """
    formats = list(DEFAULT_RATIOS.keys())

    if performance is None or not performance.scores:
        return _ratios_to_counts(DEFAULT_RATIOS, total)

    # Construire les ratios pondérés par performance
    raw: dict[VideoFormat, float] = {}
    for fmt in formats:
        default = DEFAULT_RATIOS.get(fmt, 0.0)
        score = performance.scores.get(fmt.value, 0.5)
        # Pondération : 50% défaut + 50% performance
        raw[fmt] = default * 0.5 + score * 0.5

    # Normaliser pour que la somme = 1.0
    total_raw = sum(raw.values())
    if total_raw == 0:
        return _ratios_to_counts(DEFAULT_RATIOS, total)

    ratios = {fmt: v / total_raw for fmt, v in raw.items()}

    # Clamp min/max
    ratios = _clamp_ratios(ratios)

    return _ratios_to_counts(ratios, total)


def _clamp_ratios(ratios: dict[VideoFormat, float]) -> dict[VideoFormat, float]:
    """Applique min 5% / max 35% et renormalise."""
    clamped = {fmt: max(MIN_FORMAT_RATIO, min(MAX_FORMAT_RATIO, r)) for fmt, r in ratios.items()}
    total = sum(clamped.values())
    return {fmt: r / total for fmt, r in clamped.items()}


def _ratios_to_counts(ratios: dict[VideoFormat, float], total: int) -> dict[VideoFormat, int]:
    """Convertit des ratios en counts entiers, ajuste pour atteindre le total exact."""
    counts = {fmt: int(total * r) for fmt, r in ratios.items()}

    # Combler le delta sur le format avec le plus gros ratio
    current = sum(counts.values())
    if current < total:
        best = max(ratios, key=ratios.get)
        counts[best] += total - current

    return counts
