"""
Modèles de données pour le Content Engine NoRadar.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class VideoFormat(str, Enum):
    """Les formats de contenu NoRadar."""

    # Formats existants (feature-driven)
    SCANDALE = "scandale"  # Viral, polémique
    TUTO = "tuto"  # Éducatif, conversion
    TEMOIGNAGE = "temoignage"  # Preuve sociale
    MYTHE = "mythe"  # Démystification
    CHIFFRE_CHOC = "chiffre_choc"  # Hook rapide
    ULTRA_COURT = "ultra_court"  # Format 15 sec, percutant

    # NOUVEAUX FORMATS (story-driven) - PRIORITAIRES
    STORY_POV = "story_pov"      # "J'ai reçu une amende, voilà ce que j'ai fait"
    DEBUNK = "debunk"            # "3 raisons de ne PAS payer direct"
    CAS_REEL = "cas_reel"        # "Amende de 135€ → contestée. Voici comment"
    VRAI_FAUX = "vrai_faux"      # "VRAI ou FAUX : ..." — engagement interactif


class VideoStatus(str, Enum):
    """Statut de production d'une vidéo."""

    DRAFT = "draft"  # Script généré
    AUDIO_READY = "audio_ready"  # Voix générée
    VIDEO_READY = "video_ready"  # Vidéo montée
    UPLOADED = "uploaded"  # Uploadée sur Google Drive
    PUBLISHED = "published"  # Publiée via Repurpose.io


class Script(BaseModel):
    """Script généré pour une vidéo."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    format: VideoFormat
    title: str
    hook: str = Field(description="Accroche des 3 premières secondes")
    body: str = Field(description="Corps du script")
    cta: str = Field(description="Call-to-action final")
    full_text: str = Field(description="Texte complet pour le TTS")
    duration_estimate: int = Field(description="Durée estimée en secondes")
    hashtags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

    # Texte de la vignette
    thumbnail_text: dict = Field(
        default_factory=lambda: {"line1": "", "line2": ""},
        description="Texte de la vignette (2 lignes max, majuscules)"
    )

    # Caption Facebook
    facebook_caption: str = Field(
        default="",
        description="Caption longue pour Facebook (3-5 phrases + CTA)"
    )

    @property
    def filename(self) -> str:
        return f"{self.format.value}_{self.id}.json"

    @property
    def tracking_id(self) -> str:
        """ID de tracking unique pour cette vidéo."""
        return f"vid_{self.format.value}_{self.id}"

    @property
    def telegram_link(self) -> str:
        """Lien Telegram avec tracking."""
        from src.config import settings
        if settings.tracking_enabled:
            return f"https://t.me/{settings.telegram_bot_username}?start={self.tracking_id}"
        return f"https://t.me/{settings.telegram_bot_username}"


class AudioFile(BaseModel):
    """Fichier audio généré."""

    id: str
    script_id: str
    path: Path
    duration: float = Field(description="Durée en secondes")
    voice_name: str
    created_at: datetime = Field(default_factory=datetime.now)


class SubtitleSegment(BaseModel):
    """Segment de sous-titre avec timing."""

    index: int
    start_time: float  # en secondes
    end_time: float
    text: str


class Subtitles(BaseModel):
    """Sous-titres complets."""

    id: str
    audio_id: str
    segments: list[SubtitleSegment]
    srt_path: Optional[Path] = None


class Video(BaseModel):
    """Vidéo produite."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    script: Script
    audio: Optional[AudioFile] = None
    subtitles: Optional[Subtitles] = None
    video_path: Optional[Path] = None
    thumbnail_path: Optional[Path] = None
    status: VideoStatus = VideoStatus.DRAFT
    gdrive_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    published_at: Optional[datetime] = None

    @property
    def filename(self) -> str:
        return f"noradar_{self.script.format.value}_{self.id}.mp4"


class BatchJob(BaseModel):
    """Job de production par batch."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    videos: list[Video] = Field(default_factory=list)
    total_count: int
    completed_count: int = 0
    failed_count: int = 0
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    @property
    def progress(self) -> float:
        return (self.completed_count / self.total_count) * 100 if self.total_count > 0 else 0


class WeeklyPlan(BaseModel):
    """Plan de production hebdomadaire."""

    week_number: int
    year: int
    target_count: int = 30
    distribution: dict[VideoFormat, int] = Field(
        default_factory=lambda: {
            # STORY-DRIVEN (67% du contenu)
            VideoFormat.STORY_POV: 8,      # ~27% - Format star
            VideoFormat.DEBUNK: 6,         # ~20%
            VideoFormat.CAS_REEL: 6,       # ~20%
            # FEATURE-DRIVEN (33% du contenu)
            VideoFormat.SCANDALE: 4,       # ~13%
            VideoFormat.TUTO: 3,           # ~10%
            VideoFormat.CHIFFRE_CHOC: 3,   # ~10%
            VideoFormat.VRAI_FAUX: 5,       # ~17%
        }
    )
    batches: list[BatchJob] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
