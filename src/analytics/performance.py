"""
Scoring de performance par format vidéo à partir des analytics TikTok/Instagram.
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from src.config import settings

PERFORMANCE_PATH = settings.output_dir / "performance.json"


class PerformanceData(BaseModel):
    """Scores de performance par format et thèmes gagnants/perdants."""

    scores: dict[str, float] = Field(
        default_factory=dict,
        description="Score composite normalisé 0-1 par format (clé = VideoFormat.value)",
    )
    winning_themes: list[str] = Field(
        default_factory=list,
        description="Thèmes/hooks des 5 vidéos les plus performantes",
    )
    losing_themes: list[str] = Field(
        default_factory=list,
        description="Thèmes/hooks des 5 vidéos les moins performantes",
    )
    computed_at: datetime = Field(default_factory=datetime.now)


def save_performance(data: PerformanceData) -> Path:
    """Écrit les données de performance dans outputs/performance.json."""
    PERFORMANCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PERFORMANCE_PATH.write_text(data.model_dump_json(indent=2), encoding="utf-8")
    return PERFORMANCE_PATH


def load_performance() -> Optional[PerformanceData]:
    """Lit outputs/performance.json. Retourne None si absent ou corrompu."""
    if not PERFORMANCE_PATH.exists():
        return None
    try:
        raw = PERFORMANCE_PATH.read_text(encoding="utf-8")
        return PerformanceData.model_validate_json(raw)
    except (json.JSONDecodeError, ValueError):
        return None


def _detect_format(title: str) -> Optional[str]:
    """Heuristique simple : détecte le format à partir du titre/description."""
    from src.models import VideoFormat

    lower = title.lower()
    for fmt in VideoFormat:
        if fmt.value in lower:
            return fmt.value
    return None


def compute_scores(
    tiktok_videos: list[dict],
    insta_videos: list[dict],
) -> PerformanceData:
    """
    Calcule un score composite par format :
        vues × 0.4 + partages × 0.4 + likes × 0.2
    Normalisé 0-1 par rapport au max observé.
    """
    all_videos = tiktok_videos + insta_videos

    if not all_videos:
        return PerformanceData()

    # Scores bruts par format
    format_totals: dict[str, list[float]] = defaultdict(list)

    for v in all_videos:
        fmt = _detect_format(v.get("title", ""))
        if not fmt:
            continue
        raw = v.get("views", 0) * 0.4 + v.get("shares", 0) * 0.4 + v.get("likes", 0) * 0.2
        format_totals[fmt].append(raw)

    # Moyenne par format
    format_avg = {fmt: sum(vals) / len(vals) for fmt, vals in format_totals.items()}

    # Normaliser 0-1
    max_score = max(format_avg.values()) if format_avg else 1.0
    scores = {fmt: round(avg / max_score, 3) for fmt, avg in format_avg.items()}

    # Thèmes gagnants / perdants (top 5 / bottom 5 par score brut)
    scored_videos = []
    for v in all_videos:
        raw = v.get("views", 0) * 0.4 + v.get("shares", 0) * 0.4 + v.get("likes", 0) * 0.2
        scored_videos.append((raw, v.get("title", "")))

    scored_videos.sort(key=lambda x: x[0], reverse=True)
    winning = [title for _, title in scored_videos[:5] if title]
    losing = [title for _, title in scored_videos[-5:] if title]

    return PerformanceData(scores=scores, winning_themes=winning, losing_themes=losing)
