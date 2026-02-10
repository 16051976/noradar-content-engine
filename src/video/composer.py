"""
Compositeur vidéo PRO avec :
- Sous-titres : timings Whisper + texte du script (mapping 1:1)
- Banque de vidéos locales ou Pexels
- Style TikTok
"""

import os
import random
import subprocess
import re
from pathlib import Path
from typing import Optional
import httpx
from rich.console import Console

from src.config import settings
from src.models import AudioFile, Script, SubtitleSegment, Subtitles, Video, VideoStatus

console = Console()

# ═══════════════════════════════════════════════════════════════
# CHARTE GRAPHIQUE NORADAR - VIGNETTES
# ═══════════════════════════════════════════════════════════════
NORADAR_GREEN = "#10B981"           # Vert principal (emerald-500)
NORADAR_GREEN_DARK = "#059669"      # Vert secondaire (emerald-600)
NORADAR_WHITE = "#FFFFFF"           # Blanc
THUMBNAIL_DURATION = 1.5            # Durée vignette en secondes

# Couleur FFmpeg (format 0xRRGGBB)
NORADAR_GREEN_FFmpeg = "0x10B981"


LOCAL_VIDEO_CATEGORIES = {
    "scandale": ["road", "highway", "traffic", "radar"],
    "tuto": ["document", "paper", "phone", "desk"],
    "temoignage": ["happy", "relief", "car", "driver"],
    "mythe": ["thinking", "question", "idea"],
    "chiffre_choc": ["money", "euro", "wallet", "cash"],
    "story_pov": ["road", "highway", "car", "driver", "traffic"],
    "debunk": ["thinking", "question", "idea", "road"],
    "cas_reel": ["road", "highway", "traffic", "radar", "car"],
}

# Mots-clés Pexels par format - fonds variés selon le type de contenu
PEXELS_KEYWORDS = {
    "scandale": ["police car", "speed camera", "traffic radar", "highway patrol", "speed trap"],
    "tuto": ["smartphone hand", "typing phone", "mobile app", "document desk", "paperwork"],
    "temoignage": ["happy driver", "car keys", "relieved person", "thumbs up", "success celebration"],
    "mythe": ["question mark", "thinking person", "confused", "lightbulb idea", "mystery"],
    "chiffre_choc": ["money euros", "calculator", "statistics", "numbers screen", "finance graph"],
    "story_pov": ["driving car", "highway road", "car interior", "steering wheel", "road trip"],
    "debunk": ["question mark", "thinking person", "lightbulb idea", "stop sign", "traffic light"],
    "cas_reel": ["speed camera", "traffic radar", "highway road", "police car", "car driving"],
}

GRADIENT_COLORS = {
    "scandale": ("#FF4B4B", "#8B0000"),
    "tuto": ("#4ECDC4", "#1A535C"),
    "temoignage": ("#45B7D1", "#1E3A5F"),
    "mythe": ("#9B59B6", "#4A235A"),
    "chiffre_choc": ("#F39C12", "#7D4E00"),
    "story_pov": ("#10B981", "#059669"),
    "debunk": ("#10B981", "#059669"),
    "cas_reel": ("#10B981", "#059669"),
}


class PexelsClient:
    BASE_URL = "https://api.pexels.com/videos/search"

    def __init__(self):
        self.api_key = settings.pexels_api_key
        if not self.api_key:
            console.print("[yellow]⚠ PEXELS_API_KEY manquante dans .env - vidéos de fond désactivées[/yellow]")
    
    def search_videos(self, query: str, orientation: str = "portrait", per_page: int = 5) -> list[dict]:
        if not self.api_key:
            return []
        try:
            response = httpx.get(
                self.BASE_URL,
                params={"query": query, "orientation": orientation, "per_page": per_page},
                headers={"Authorization": self.api_key},
                timeout=15,
            )
            response.raise_for_status()
            return response.json().get("videos", [])
        except Exception as e:
            console.print(f"[yellow]Pexels error: {e}[/yellow]")
            return []
    
    def download_video(self, video_data: dict, output_path: Path) -> Optional[Path]:
        try:
            video_files = video_data.get("video_files", [])
            best_file = None
            for vf in video_files:
                height = vf.get("height", 0)
                if 600 <= height <= 800:
                    best_file = vf
                    break
            if not best_file and video_files:
                best_file = min(video_files, key=lambda x: x.get("height", 9999))
            if not best_file:
                return None
            url = best_file.get("link")
            console.print(f"[blue]Téléchargement Pexels ({best_file.get('width')}x{best_file.get('height')})...[/blue]")
            response = httpx.get(url, timeout=120, follow_redirects=True)
            response.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            return output_path
        except Exception as e:
            console.print(f"[yellow]Erreur Pexels: {e}[/yellow]")
            return None


class SimpleSubtitleGenerator:
    """
    Générateur de sous-titres SIMPLE et FIABLE.
    
    Méthode :
    1. Whisper transcrit → on récupère les TIMINGS des segments
    2. On découpe le script en phrases
    3. On utilise les timings Whisper avec le texte du script
    
    Résultat : Synchro parfaite + texte sans faute
    """
    
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None
    
    @property
    def model(self):
        if self._model is None:
            console.print(f"[blue]Chargement Whisper ({self.model_size})...[/blue]")
            import whisper
            self._model = whisper.load_model(self.model_size)
        return self._model
    
    def generate(self, audio_path: Path, script: Script) -> Subtitles:
        """Génère les sous-titres synchronisés."""
        console.print(f"[blue]Génération sous-titres synchronisés...[/blue]")
        
        # 1. Transcrire pour obtenir les timings
        result = self.model.transcribe(str(audio_path), language="fr")
        whisper_segments = result.get("segments", [])
        
        # 2. Découper le script en phrases
        script_sentences = self._split_into_sentences(script.full_text)
        
        console.print(f"[dim]Whisper: {len(whisper_segments)} segments, Script: {len(script_sentences)} phrases[/dim]")
        
        # 3. Aligner les phrases du script aux timings Whisper
        aligned = self._align_sentences_to_timings(script_sentences, whisper_segments)
        
        # 4. Sauvegarder
        srt_path = settings.output_dir / "subtitles" / f"{script.id}.srt"
        srt_path.parent.mkdir(parents=True, exist_ok=True)
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(self._to_srt(aligned))
        
        console.print(f"[green]✓ Sous-titres générés : {srt_path}[/green]")
        
        return Subtitles(
            id=script.id,
            audio_id=script.id,
            segments=aligned,
            srt_path=srt_path,
        )
    
    def _split_into_sentences(self, text: str) -> list[str]:
        """Découpe le texte en phrases aux ponctuations."""
        # Découper aux . ! ?
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        # Nettoyer et filtrer
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    
    def _align_sentences_to_timings(
        self, 
        sentences: list[str], 
        whisper_segments: list[dict]
    ) -> list[SubtitleSegment]:
        """
        Aligne les phrases du script aux timings Whisper.
        
        Si même nombre de segments : mapping 1:1
        Sinon : répartition proportionnelle
        """
        if not whisper_segments:
            # Fallback sans Whisper
            total_duration = 30.0
            return self._distribute_evenly(sentences, total_duration)
        
        total_duration = whisper_segments[-1]["end"]
        
        # Cas idéal : même nombre de segments
        if len(sentences) == len(whisper_segments):
            return [
                SubtitleSegment(
                    index=i + 1,
                    start_time=whisper_segments[i]["start"],
                    end_time=whisper_segments[i]["end"],
                    text=sentences[i],
                )
                for i in range(len(sentences))
            ]
        
        # Sinon : répartition proportionnelle basée sur la longueur
        total_chars = sum(len(s) for s in sentences)
        
        aligned = []
        current_time = 0.0
        
        for i, sentence in enumerate(sentences):
            # Durée proportionnelle
            ratio = len(sentence) / total_chars
            duration = ratio * total_duration
            
            # Bornes min/max
            duration = max(1.5, min(6.0, duration))
            
            end_time = min(current_time + duration, total_duration)
            
            # Ajuster au segment Whisper le plus proche si possible
            closest_seg = self._find_closest_segment(current_time, whisper_segments)
            if closest_seg and abs(closest_seg["start"] - current_time) < 1.0:
                start_time = closest_seg["start"]
            else:
                start_time = current_time
            
            aligned.append(SubtitleSegment(
                index=i + 1,
                start_time=start_time,
                end_time=end_time,
                text=sentence,
            ))
            
            current_time = end_time
        
        return aligned
    
    def _find_closest_segment(self, time: float, segments: list[dict]) -> Optional[dict]:
        """Trouve le segment Whisper le plus proche d'un temps donné."""
        closest = None
        min_diff = float('inf')
        for seg in segments:
            diff = abs(seg["start"] - time)
            if diff < min_diff:
                min_diff = diff
                closest = seg
        return closest
    
    def _distribute_evenly(self, sentences: list[str], total_duration: float) -> list[SubtitleSegment]:
        """Répartit uniformément si pas de timings Whisper."""
        duration_per = total_duration / len(sentences) if sentences else 3.0
        return [
            SubtitleSegment(
                index=i + 1,
                start_time=i * duration_per,
                end_time=(i + 1) * duration_per,
                text=s,
            )
            for i, s in enumerate(sentences)
        ]
    
    def _to_srt(self, segments: list[SubtitleSegment]) -> str:
        lines = []
        for seg in segments:
            lines.extend([
                f"{seg.index}",
                f"{self._ts(seg.start_time)} --> {self._ts(seg.end_time)}",
                seg.text,
                "",
            ])
        return "\n".join(lines)
    
    @staticmethod
    def _ts(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


class SubtitleStyler:
    ASS_HEADER = """[Script Info]
Title: NoRadar Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,70,&H00FFFFFF,&H000000FF,&H00000000,&HAA000000,-1,0,0,0,100,100,0,0,1,4,2,2,60,60,400,1
Style: Accent,Arial Black,75,&H0000FFFF,&H000000FF,&H00000000,&HAA000000,-1,0,0,0,100,100,0,0,1,5,2,2,60,60,400,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    @classmethod
    def generate_ass(cls, segments: list[SubtitleSegment], output_path: Path) -> Path:
        lines = [cls.ASS_HEADER]
        for seg in segments:
            start = cls._ass_time(seg.start_time)
            end = cls._ass_time(seg.end_time)
            text = seg.text.strip().upper()
            # Découper lignes longues
            if len(text) > 45:
                words = text.split()
                mid = len(words) // 2
                text = " ".join(words[:mid]) + "\\N" + " ".join(words[mid:])
            style = "Accent" if seg.index % 3 == 1 else "Default"
            lines.append(f"Dialogue: 0,{start},{end},{style},,0,0,0,,{text}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path
    
    @staticmethod
    def _ass_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds % 1) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


class ThumbnailGenerator:
    """
    Génère les vignettes NoRadar au format TikTok/Instagram.

    Format : Fond vert uni #10B981 + texte blanc bold
    """

    def __init__(self):
        self.width = 1080
        self.height = 1920
        self.temp_dir = settings.temp_dir / "thumbnails"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, script: Script, output_path: Path, broll_video: Optional[Path] = None) -> Path:
        """
        Génère une vignette avec :
        1. Première frame du B-roll floutée + overlay noir 40%
        2. Texte 2 lignes (blanc + vert)
        3. noradar.app discret en bas
        """
        console.print("[blue]🖼️ Génération vignette B-roll floutée...[/blue]")

        line1 = script.thumbnail_text.get("line1", "")
        line2 = script.thumbnail_text.get("line2", "")

        if not line1:
            line1 = script.hook[:35].upper()
        if not line2:
            line2 = "NORADAR."

        line1_clean = self._escape_ffmpeg_text(line1.upper())
        line2_clean = self._escape_ffmpeg_text(line2.upper())

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Source : B-roll première frame floutée, ou fallback fond vert
        if broll_video and broll_video.exists():
            input_args = ["-i", str(broll_video)]
            vf_base = (
                f"select=eq(n\\,0),"
                f"scale={self.width}:{self.height}:force_original_aspect_ratio=increase,"
                f"crop={self.width}:{self.height},"
                f"boxblur=5:5,"
                f"drawbox=c=black@0.3:t=fill"
            )
        else:
            input_args = [
                "-f", "lavfi",
                "-i", f"color=c={NORADAR_GREEN_FFmpeg}:s={self.width}x{self.height}:d=1"
            ]
            vf_base = ""

        # Texte : ligne 1 blanc, ligne 2 vert, noradar.app blanc discret
        text_filters = (
            f"drawtext=text='{line1_clean}'"
            f":fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            f":fontsize=85:fontcolor=white"
            f":x=(w-text_w)/2:y=(h/2)-120,"

            f"drawtext=text='{line2_clean}'"
            f":fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            f":fontsize=70:fontcolor=white"
            f":x=(w-text_w)/2:y=(h/2)+20,"

            f"drawtext=text='noradar.app'"
            f":fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            f":fontsize=30:fontcolor=white@0.7"
            f":x=(w-text_w)/2:y=h-150"
        )

        vf = f"{vf_base},{text_filters}" if vf_base else text_filters

        result = subprocess.run([
            "ffmpeg", "-y",
            *input_args,
            "-vf", vf,
            "-frames:v", "1",
            str(output_path)
        ], capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            console.print(f"[yellow]⚠️ Erreur vignette: {result.stderr[:200]}[/yellow]")
            self._create_fallback_thumbnail(output_path)
        else:
            console.print(f"[green]✓ Vignette générée: {output_path.name}[/green]")

        return output_path

    def _create_fallback_thumbnail(self, output_path: Path) -> Path:
        """Crée une vignette de secours (fond vert simple)."""
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c={NORADAR_GREEN_FFmpeg}:s={self.width}x{self.height}:d=1",
            "-frames:v", "1",
            str(output_path)
        ], capture_output=True, timeout=15)
        return output_path

    def generate_video_thumbnail(
        self,
        thumbnail_image: Path,
        output_path: Path,
        duration: float = THUMBNAIL_DURATION,
        reference_video: Optional[Path] = None,
    ) -> Path:
        """Convertit la vignette image en vidéo (1.5s) avec piste audio silencieuse."""
        # Prober la vidéo de référence pour matcher ses paramètres
        fps = "30"
        sample_rate = "44100"
        channels = "stereo"
        profile = "high"
        if reference_video and reference_video.exists():
            import json as _json
            probe = subprocess.run(
                ["ffprobe", "-v", "error",
                 "-show_entries", "stream=r_frame_rate,profile,sample_rate,channels,codec_type",
                 "-of", "json", str(reference_video)],
                capture_output=True, text=True, timeout=10)
            if probe.returncode == 0:
                streams = _json.loads(probe.stdout).get("streams", [])
                for s in streams:
                    if s.get("codec_type") == "video":
                        fps = s.get("r_frame_rate", fps)
                        profile = s.get("profile", profile).lower()
                    elif s.get("codec_type") == "audio":
                        sample_rate = s.get("sample_rate", sample_rate)
                        ch = s.get("channels", 2)
                        channels = "mono" if str(ch) == "1" else "stereo"

        cl = channels
        subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(thumbnail_image),
            "-f", "lavfi",
            "-i", f"anullsrc=r={sample_rate}:cl={cl}",
            "-t", str(duration),
            "-vf", f"scale={self.width}:{self.height}",
            "-c:v", "libx264",
            "-profile:v", "baseline" if "baseline" in profile else "high",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-r", fps,
            "-shortest",
            str(output_path)
        ], capture_output=True, timeout=30)

        return output_path

    @staticmethod
    def _escape_ffmpeg_text(text: str) -> str:
        """Échappe les caractères spéciaux pour FFmpeg drawtext."""
        text = text.replace("'", "\u2019")  # Apostrophe courbe
        text = text.replace(":", " ")   # Deux-points
        text = text.replace("\\", "")   # Backslash
        text = text.replace("%", " pourcent ")  # Pourcentage
        return text


class VideoComposerPro:
    def __init__(self):
        self.pexels = PexelsClient()
        self.temp_dir = settings.temp_dir / "video_work"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.backgrounds_dir = settings.assets_dir / "backgrounds"
        self.width = settings.video_width
        self.height = settings.video_height
    
    def get_background_video(self, format_type: str, duration: float, used_backgrounds: Optional[list[str]] = None) -> Path:
        """Sélectionne un fond vidéo en évitant les répétitions du batch."""
        used = set(used_backgrounds or [])

        def _pick_unique(candidates: list[Path]) -> Optional[Path]:
            unused = [c for c in candidates if c.name not in [Path(u).name for u in used]]
            if unused:
                return random.choice(unused)
            return random.choice(candidates) if candidates else None

        # 0. Vidéos locales assets (priorité absolue)
        local_bg_dir = Path("assets/backgrounds")
        if local_bg_dir.exists():
            local_videos = list(local_bg_dir.glob("*.mp4"))
            if local_videos:
                chosen = _pick_unique(local_videos)
                if chosen:
                    console.print(f"[green]✓ Fond local: {chosen.name}[/green]")
                    return chosen

        # 1. Local
        local = self._find_local_video(format_type)
        if local and str(local) not in used:
            console.print(f"[green]✓ Vidéo locale: {local.name}[/green]")
            return local

        # 1.5 Cache Pexels persistant
        if settings.pexels_cache_enabled:
            cached = self._find_cached_pexels(format_type, used)
            if cached:
                console.print(f"[green]✓ Cache Pexels persistant: {cached.name}[/green]")
                return cached

        # 2. Pexels
        if self.pexels.api_key:
            keywords = PEXELS_KEYWORDS.get(format_type, PEXELS_KEYWORDS["tuto"])
            query = random.choice(keywords)
            console.print(f"[blue]Pexels: '{query}'...[/blue]")
            videos = self.pexels.search_videos(query, per_page=10)
            if videos:
                random.shuffle(videos)
                for v in videos[:5]:
                    path = self.temp_dir / f"pexels_{v['id']}.mp4"
                    if str(path) in used or path.name in [Path(u).name for u in used]:
                        continue
                    if path.exists():
                        console.print(f"[green]✓ Cache Pexels: {path.name}[/green]")
                        return path
                    dl = self.pexels.download_video(v, path)
                    if dl:
                        console.print(f"[green]✓ Pexels téléchargé: {path.name}[/green]")
                        self._save_to_pexels_cache(dl, format_type)
                        return dl
            else:
                console.print("[yellow]Pexels: aucune vidéo trouvée[/yellow]")

        # 3. Gradient
        console.print("[yellow]Fond dégradé...[/yellow]")
        return self._make_gradient(format_type, duration)
    
    def _find_local_video(self, format_type: str) -> Optional[Path]:
        if not self.backgrounds_dir.exists():
            return None
        cats = LOCAL_VIDEO_CATEGORIES.get(format_type, [])
        candidates = []
        for f in self.backgrounds_dir.glob("*.mp4"):
            for c in cats:
                if c in f.stem.lower():
                    candidates.append(f)
                    break
        if not candidates:
            candidates = list(self.backgrounds_dir.glob("*.mp4"))
        return random.choice(candidates) if candidates else None
    
    def _make_gradient(self, format_type: str, duration: float) -> Path:
        out = self.temp_dir / f"gradient_{format_type}.mp4"
        c = GRADIENT_COLORS.get(format_type, ("#1a1a2e", "#16213e"))[0].replace("#", "0x")
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c={c}:s={self.width}x{self.height}:d={duration}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)
        ], capture_output=True, timeout=60)
        return out
    
    def _find_cached_pexels(self, format_type: str, used: Optional[set] = None) -> Optional[Path]:
        """Cherche une vidéo dans le cache Pexels persistant par format, en évitant les doublons."""
        cache_dir = settings.pexels_cache_dir / format_type
        if not cache_dir.exists():
            return None
        candidates = list(cache_dir.glob("*.mp4"))
        if not candidates:
            return None
        if used:
            unused = [c for c in candidates if c.name not in [Path(u).name for u in used]]
            if unused:
                return random.choice(unused)
        return random.choice(candidates)

    def _save_to_pexels_cache(self, source: Path, format_type: str) -> None:
        """Copie une vidéo téléchargée dans le cache persistant par format."""
        if not settings.pexels_cache_enabled:
            return
        import shutil
        cache_dir = settings.pexels_cache_dir / format_type
        cache_dir.mkdir(parents=True, exist_ok=True)
        dest = cache_dir / source.name
        if not dest.exists():
            shutil.copy2(source, dest)
        # Nettoyage si trop de vidéos
        cached = sorted(cache_dir.glob("*.mp4"), key=lambda f: f.stat().st_mtime)
        while len(cached) > settings.pexels_cache_max_videos:
            cached.pop(0).unlink()

    def prepare_background(self, bg: Path, duration: float) -> Path:
        out = self.temp_dir / "bg_prepared.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(bg),
            "-t", str(duration),
            "-vf", f"scale={self.width}:{self.height}:force_original_aspect_ratio=increase,crop={self.width}:{self.height},setsar=1",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-an", str(out)
        ], capture_output=True, timeout=300)
        return out
    
    def compose(self, script: Script, audio: AudioFile, subtitles: Subtitles, output_path: Path, background_image: Optional[Path] = None, used_backgrounds: Optional[list[str]] = None) -> Path:
        console.print("[bold blue]🎬 Composition vidéo...[/bold blue]")
        duration = audio.duration + 0.5
        
        # Background
        if background_image and background_image.exists():
            if background_image.suffix == ".mp4":
                bg = background_image
            else:
                bg = self._image_to_video(background_image, duration)
        else:
            bg = self.get_background_video(script.format.value, duration, used_backgrounds=used_backgrounds)
        
        prepared = self.prepare_background(bg, duration)
        
        # ASS subtitles
        ass = self.temp_dir / f"{script.id}.ass"
        SubtitleStyler.generate_ass(subtitles.segments, ass)
        
        # Compose
        output_path.parent.mkdir(parents=True, exist_ok=True)
        ass_esc = str(ass).replace(":", "\\:")
        filter_str = f"[0:v]ass='{ass_esc}'"

        # Watermark si activé
        if settings.watermark_enabled and settings.watermark_text:
            positions = {
                "top_left": ("10", "50"),
                "top_right": ("w-tw-10", "50"),
                "bottom_left": ("10", "h-th-150"),
                "bottom_right": ("w-tw-10", "h-th-150"),
            }
            wx, wy = positions.get(settings.watermark_position, positions["top_right"])
            wm_text = settings.watermark_text.replace("'", "'\\''")
            filter_str += (
                f",drawtext=text='{wm_text}'"
                f":fontsize={settings.watermark_font_size}"
                f":fontcolor=white"
                f":x={wx}:y={wy}"
                f":borderw=2:bordercolor=black"
            )

        filter_str += "[v]"

        result = subprocess.run([
            "ffmpeg", "-y", "-i", str(prepared), "-i", str(audio.path),
            "-filter_complex", filter_str,
            "-map", "[v]", "-map", "1:a",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
            str(output_path)
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            return self._fallback(prepared, audio, subtitles, output_path)
        
        console.print(f"[green]✓ Vidéo: {output_path}[/green]")
        return output_path
    
    def compose_with_thumbnail(
        self,
        script: Script,
        audio: AudioFile,
        subtitles: Subtitles,
        output_path: Path,
        background_image: Optional[Path] = None,
        used_backgrounds: Optional[list[str]] = None,
    ) -> Path:
        """
        Pass-through vers compose() — vignette désactivée.
        La méthode est conservée pour compatibilité.
        """
        return self.compose(script, audio, subtitles, output_path, background_image, used_backgrounds=used_backgrounds)

    def _image_to_video(self, img: Path, duration: float) -> Path:
        out = self.temp_dir / "img_bg.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-i", str(img), "-t", str(duration),
            "-vf", f"scale={self.width}:{self.height}:force_original_aspect_ratio=increase,crop={self.width}:{self.height}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)
        ], capture_output=True, timeout=60)
        return out
    
    def _fallback(self, bg: Path, audio: AudioFile, subs: Subtitles, out: Path) -> Path:
        console.print("[yellow]Fallback SRT...[/yellow]")
        srt_esc = str(subs.srt_path).replace(":", "\\:")
        style = "FontName=Arial Black,FontSize=60,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=4,Shadow=2,MarginV=200"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(bg), "-i", str(audio.path),
            "-vf", f"subtitles='{srt_esc}':force_style='{style}'",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
            str(out)
        ], capture_output=True, timeout=300)
        return out


class VideoPipeline:
    def __init__(self):
        self.subtitle_generator = SimpleSubtitleGenerator()
        self.video_composer = VideoComposerPro()

    def process(
        self,
        script: Script,
        audio: AudioFile,
        background_image: Optional[Path] = None,
        include_thumbnail: bool = True,
        used_backgrounds: Optional[list[str]] = None,
    ) -> Video:
        settings.ensure_directories()

        subtitles = self.subtitle_generator.generate(audio.path, script)

        video_path = settings.output_dir / "videos" / f"noradar_{script.format.value}_{script.id}.mp4"

        if include_thumbnail and script.thumbnail_text.get("line1"):
            self.video_composer.compose_with_thumbnail(
                script, audio, subtitles, video_path, background_image, used_backgrounds=used_backgrounds
            )
            console.print("[cyan]📱 Vignette intégrée (TikTok + Instagram ready)[/cyan]")
        else:
            self.video_composer.compose(script, audio, subtitles, video_path, background_image, used_backgrounds=used_backgrounds)

        video = Video(
            id=script.id, script=script, audio=audio, subtitles=subtitles,
            video_path=video_path, status=VideoStatus.VIDEO_READY,
        )
        console.print(f"[bold green]✓ Vidéo complète: {video.filename}[/bold green]")
        return video
