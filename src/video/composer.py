"""
Compositeur vidéo avec FFmpeg et Whisper pour les sous-titres.
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import ffmpeg
from rich.console import Console

from src.config import settings
from src.models import AudioFile, Script, SubtitleSegment, Subtitles, Video, VideoStatus

console = Console()


class SubtitleGenerator:
    """Génère les sous-titres avec timing via Whisper."""

    def __init__(self, model_size: str = "base"):
        """
        Args:
            model_size: Taille du modèle Whisper (tiny, base, small, medium, large)
        """
        self.model_size = model_size
        self._model = None

    @property
    def model(self):
        """Lazy loading du modèle Whisper."""
        if self._model is None:
            console.print(f"[blue]Chargement modèle Whisper ({self.model_size})...[/blue]")
            import whisper

            self._model = whisper.load_model(self.model_size)
        return self._model

    def generate(self, audio_path: Path, script_id: str) -> Subtitles:
        """
        Génère les sous-titres avec timing pour un fichier audio.

        Args:
            audio_path: Chemin vers le fichier audio
            script_id: ID du script associé

        Returns:
            Subtitles avec segments timés
        """
        console.print(f"[blue]Transcription Whisper : {audio_path.name}...[/blue]")

        result = self.model.transcribe(
            str(audio_path),
            language="fr",
            word_timestamps=True,
        )

        segments = []
        for i, segment in enumerate(result["segments"]):
            segments.append(
                SubtitleSegment(
                    index=i + 1,
                    start_time=segment["start"],
                    end_time=segment["end"],
                    text=segment["text"].strip(),
                )
            )

        # Génération du fichier SRT
        srt_path = audio_path.parent.parent / "subtitles" / f"{script_id}.srt"
        srt_path.parent.mkdir(parents=True, exist_ok=True)

        srt_content = self._to_srt(segments)
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        console.print(f"[green]✓ Sous-titres générés : {srt_path}[/green]")

        return Subtitles(
            id=script_id,
            audio_id=script_id,
            segments=segments,
            srt_path=srt_path,
        )

    def _to_srt(self, segments: list[SubtitleSegment]) -> str:
        """Convertit les segments en format SRT."""
        lines = []
        for seg in segments:
            start = self._format_timestamp(seg.start_time)
            end = self._format_timestamp(seg.end_time)
            lines.append(f"{seg.index}")
            lines.append(f"{start} --> {end}")
            lines.append(seg.text)
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Formate les secondes en timestamp SRT (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


class VideoComposer:
    """Compose la vidéo finale avec FFmpeg."""

    def __init__(self):
        self.width = settings.video_width
        self.height = settings.video_height
        self.fps = settings.video_fps
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """Vérifie que FFmpeg est installé."""
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("FFmpeg n'est pas installé. Installez-le avec: apt install ffmpeg")

    def compose(
        self,
        audio_path: Path,
        output_path: Path,
        subtitles_path: Optional[Path] = None,
        background_color: str = "#1a1a2e",
        background_image: Optional[Path] = None,
    ) -> Path:
        """
        Compose une vidéo verticale avec audio et sous-titres.

        Args:
            audio_path: Chemin vers l'audio
            output_path: Chemin de sortie
            subtitles_path: Chemin vers le fichier SRT
            background_color: Couleur de fond hex
            background_image: Image de fond optionnelle

        Returns:
            Chemin vers la vidéo générée
        """
        console.print(f"[blue]Composition vidéo...[/blue]")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Obtenir la durée de l'audio
        probe = ffmpeg.probe(str(audio_path))
        duration = float(probe["streams"][0]["duration"])

        # Construction du pipeline FFmpeg
        if background_image and background_image.exists():
            # Avec image de fond
            video_input = ffmpeg.input(
                str(background_image),
                loop=1,
                t=duration,
            ).filter("scale", self.width, self.height)
        else:
            # Fond coloré
            video_input = ffmpeg.input(
                f"color=c={background_color}:s={self.width}x{self.height}:d={duration}",
                f="lavfi",
            )

        audio_input = ffmpeg.input(str(audio_path))

        # Ajout des sous-titres si disponibles
        if subtitles_path and subtitles_path.exists():
            # Style des sous-titres
            subtitle_style = (
                f"FontName={settings.subtitle_font},"
                f"FontSize={settings.subtitle_font_size},"
                f"PrimaryColour=&H00FFFFFF,"  # Blanc
                f"OutlineColour=&H00000000,"  # Noir
                f"Outline={settings.subtitle_outline_width},"
                f"Shadow=1,"
                f"MarginV=100"  # Marge verticale
            )

            video_input = video_input.filter(
                "subtitles",
                str(subtitles_path),
                force_style=subtitle_style,
            )

        # Output
        output = ffmpeg.output(
            video_input,
            audio_input,
            str(output_path),
            vcodec="libx264",
            acodec="aac",
            pix_fmt="yuv420p",
            r=self.fps,
            preset="medium",
            crf=23,
            movflags="+faststart",  # Optimisation streaming
        ).overwrite_output()

        # Exécution
        try:
            output.run(capture_stdout=True, capture_stderr=True)
            console.print(f"[green]✓ Vidéo générée : {output_path}[/green]")
            return output_path
        except ffmpeg.Error as e:
            console.print(f"[red]Erreur FFmpeg : {e.stderr.decode()}[/red]")
            raise

    def add_text_overlay(
        self,
        input_path: Path,
        output_path: Path,
        text: str,
        position: str = "top",
        font_size: int = 40,
    ) -> Path:
        """Ajoute un texte en overlay (titre, hashtags, etc.)."""
        y_position = {
            "top": 50,
            "center": f"(h-text_h)/2",
            "bottom": f"h-text_h-100",
        }.get(position, 50)

        video = ffmpeg.input(str(input_path))

        video = video.drawtext(
            text=text,
            fontsize=font_size,
            fontcolor="white",
            x="(w-text_w)/2",
            y=y_position,
            borderw=2,
            bordercolor="black",
        )

        output = ffmpeg.output(video, str(output_path)).overwrite_output()
        output.run(capture_stdout=True, capture_stderr=True)

        return output_path

    def add_logo(
        self,
        input_path: Path,
        output_path: Path,
        logo_path: Path,
        position: str = "top_right",
        scale: float = 0.15,
    ) -> Path:
        """Ajoute un logo/watermark à la vidéo."""
        positions = {
            "top_left": ("10", "10"),
            "top_right": (f"W-w-10", "10"),
            "bottom_left": ("10", f"H-h-10"),
            "bottom_right": (f"W-w-10", f"H-h-10"),
        }
        x, y = positions.get(position, positions["top_right"])

        video = ffmpeg.input(str(input_path))
        logo = ffmpeg.input(str(logo_path)).filter(
            "scale",
            f"iw*{scale}",
            f"ih*{scale}",
        )

        output = ffmpeg.overlay(video, logo, x=x, y=y)
        output = ffmpeg.output(output, str(output_path)).overwrite_output()
        output.run(capture_stdout=True, capture_stderr=True)

        return output_path


class VideoPipeline:
    """Pipeline complet : audio → sous-titres → vidéo."""

    def __init__(self):
        self.subtitle_generator = SubtitleGenerator()
        self.video_composer = VideoComposer()

    def process(
        self,
        script: Script,
        audio: AudioFile,
        background_image: Optional[Path] = None,
    ) -> Video:
        """
        Traite un script/audio complet jusqu'à la vidéo finale.

        Args:
            script: Script source
            audio: Audio généré
            background_image: Image de fond optionnelle

        Returns:
            Video avec tous les chemins
        """
        settings.ensure_directories()

        # 1. Générer les sous-titres
        subtitles = self.subtitle_generator.generate(audio.path, script.id)

        # 2. Composer la vidéo
        video_path = settings.output_dir / "videos" / f"noradar_{script.format.value}_{script.id}.mp4"

        self.video_composer.compose(
            audio_path=audio.path,
            output_path=video_path,
            subtitles_path=subtitles.srt_path,
            background_image=background_image,
        )

        # 3. Créer l'objet Video
        video = Video(
            id=script.id,
            script=script,
            audio=audio,
            subtitles=subtitles,
            video_path=video_path,
            status=VideoStatus.VIDEO_READY,
        )

        console.print(f"[bold green]✓ Vidéo complète : {video.filename}[/bold green]")
        return video
