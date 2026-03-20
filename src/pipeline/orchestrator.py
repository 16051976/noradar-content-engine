"""
Orchestrateur du pipeline de production video.
"""

import random
from datetime import datetime
from pathlib import Path
from typing import Optional
from rich.console import Console

from src.config import settings
from src.models import BatchJob, Script, Video, VideoFormat, VideoStatus, WeeklyPlan
from src.scripts.generator import ScriptGenerator
from src.pipeline.validator import ScriptValidator
from src.storage.content_store import is_duplicate_script

console = Console()

# Voix naturelles de qualité pour rotation en batch
BATCH_VOICES = [
    "fr-FR-Neural2-B",   # Homme naturel 1
    "fr-FR-Neural2-D",   # Homme naturel 2
    "fr-FR-Wavenet-B",   # Homme wavenet
    "fr-FR-Neural2-A",   # Femme naturel 1
    "fr-FR-Neural2-C",   # Femme naturel 2
    "fr-FR-Wavenet-A",   # Femme wavenet
]


class ContentOrchestrator:

    def __init__(self):
        self.script_generator = ScriptGenerator()
        self._script_validator = None
        self._voice_generator = None
        self._video_pipeline = None
        self._gdrive = None
        self._used_backgrounds: list[str] = []

    @property
    def script_validator(self):
        if self._script_validator is None:
            self._script_validator = ScriptValidator()
        return self._script_validator

    @property
    def voice_generator(self):
        if self._voice_generator is None:
            from src.voice.generator import VoiceGenerator
            self._voice_generator = VoiceGenerator()
        return self._voice_generator

    @property
    def video_pipeline(self):
        if self._video_pipeline is None:
            from src.video.composer import VideoPipeline
            self._video_pipeline = VideoPipeline()
        return self._video_pipeline

    @property
    def gdrive(self):
        if self._gdrive is None:
            from src.storage.gdrive import GoogleDriveSync
            self._gdrive = GoogleDriveSync()
        return self._gdrive

    def script_only(self, format, theme=None):
        script = self.script_generator.generate(format, theme)
        self.script_generator.save_script(script)
        console.print(f"\n[bold]Script genere :[/bold]")
        console.print(f"[yellow]HOOK:[/yellow] {script.hook}")
        console.print(f"[yellow]BODY:[/yellow] {script.body[:200]}...")
        console.print(f"[yellow]CTA:[/yellow] {script.cta}")
        if settings.tracking_enabled:
            console.print(f"[cyan]🔗 Lien trackable : {script.telegram_link}[/cyan]")
        return script

    def produce_video(self, format, theme=None, background_image=None, upload=False, voice_engine="google", voice_name=None):
        script = self.script_generator.generate(format, theme)
        self.script_generator.save_script(script)
        if settings.tracking_enabled:
            console.print(f"[cyan]🔗 Lien trackable : {script.telegram_link}[/cyan]")

        # Validation qualité + anti-doublon
        validation = self.script_validator.validate(script)
        is_dup = is_duplicate_script(script)

        if not validation.passed or is_dup:
            reason = "doublon" if is_dup else f"score {validation.overall_score}/10"
            console.print(f"[yellow]Script rejeté ({reason}), régénération...[/yellow]")
            script = self.script_generator.generate(format, theme)
            self.script_generator.save_script(script)
            validation = self.script_validator.validate(script)
            is_dup = is_duplicate_script(script)
            if not validation.passed or is_dup:
                reason = "doublon" if is_dup else f"score {validation.overall_score}/10"
                raise RuntimeError(
                    f"Script rejeté 2 fois ({reason}). "
                    f"Derniers problèmes : {validation.issues}. Publication annulée."
                )

        audio = self.voice_generator.generate_from_script(script, engine=voice_engine, voice_name=voice_name)
        video = self.video_pipeline.process(script, audio, background_image, used_backgrounds=self._used_backgrounds)
        if video.video_path:
            self._used_backgrounds.append(str(video.video_path))
        if upload:
            self.gdrive.upload_video(video)
        return video

    def produce_batch(self, distribution, theme=None, upload=False):
        total = sum(distribution.values())
        batch = BatchJob(total_count=total)

        # Construire une liste plate de formats puis mélanger l'ordre
        format_list = []
        for fmt, count in distribution.items():
            format_list.extend([fmt] * count)
        random.shuffle(format_list)

        # Rotation des voix (garantie différence consécutive)
        voice_pool = list(BATCH_VOICES)
        random.shuffle(voice_pool)

        voices_for_batch = []
        used_in_batch = set()

        for i in range(len(format_list)):
            if i == 0:
                # Première vidéo : voix aléatoire du pool
                voice = voice_pool[0]
                voices_for_batch.append(voice)
                used_in_batch.add(voice)
            else:
                # Trouver une voix différente de la précédente ET pas déjà utilisée si possible
                candidates = [v for v in voice_pool if v != voices_for_batch[-1]]

                # Prioriser les voix non utilisées
                unused = [v for v in candidates if v not in used_in_batch]
                if unused:
                    voice = random.choice(unused)
                else:
                    voice = random.choice(candidates)

                voices_for_batch.append(voice)
                used_in_batch.add(voice)

        for video_number, fmt in enumerate(format_list, 1):
            voice = voices_for_batch[video_number - 1]

            console.print(f"\n[bold]═══ Vidéo {video_number}/{total} [{fmt.value}] voix={voice.split('-')[-1]} ═══[/bold]")

            try:
                video = self.produce_video(format=fmt, theme=theme, upload=upload, voice_name=voice)
                batch.videos.append(video)
                batch.completed_count += 1
            except Exception as e:
                batch.failed_count += 1
                console.print(f"[red]✗ Échec vidéo {video_number}: {e}[/red]")

        # Résumé diversité
        console.print(f"\n[bold green]{'═' * 50}[/bold green]")
        console.print(f"[bold green]Batch terminé : {batch.completed_count}/{total} réussies, {batch.failed_count} échecs[/bold green]")
        hooks = [v.script.hook for v in batch.videos]
        unique_hooks = set(h.strip().lower() for h in hooks)
        if len(unique_hooks) < len(hooks):
            console.print(f"[yellow]⚠ {len(hooks) - len(unique_hooks)} hooks en doublon détectés[/yellow]")
        else:
            console.print(f"[green]✓ {len(unique_hooks)} scripts uniques sur {len(hooks)}[/green]")

        return batch

    def produce_weekly(self, upload=False):
        """
        Produit une semaine complète de contenu (30 vidéos).
        Distribution optimale des formats.
        """
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]   PRODUCTION WEEKLY - 30 VIDÉOS      [/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
        
        # Distribution hebdomadaire (basée sur settings.weekly_target)
        total = settings.weekly_target
        
        distribution = {
            VideoFormat.STORY_POV: int(total * 0.27),    # 27% = 8 vidéos
            VideoFormat.DEBUNK: int(total * 0.20),        # 20% = 6 vidéos
            VideoFormat.CAS_REEL: int(total * 0.20),      # 20% = 6 vidéos
            VideoFormat.SCANDALE: int(total * 0.13),      # 13% = 4 vidéos
            VideoFormat.TUTO: int(total * 0.10),          # 10% = 3 vidéos
            VideoFormat.TEMOIGNAGE: int(total * 0.05),    # 5% = 2 vidéos
            VideoFormat.MYTHE: int(total * 0.05),         # 5% = 1 vidéo
        }
        
        # Ajuster pour atteindre exactement le total
        current_sum = sum(distribution.values())
        if current_sum < total:
            # Ajouter les vidéos manquantes au format le plus performant
            distribution[VideoFormat.STORY_POV] += (total - current_sum)
        
        console.print("[bold]Distribution hebdomadaire :[/bold]")
        for fmt, count in distribution.items():
            console.print(f"  {fmt.value}: {count}")
        console.print(f"\n[bold]Total : {sum(distribution.values())} vidéos[/bold]\n")
        
        return self.produce_batch(distribution, upload=upload)

    # ══════════════════════════════════════════════════════
    # CARROUSELS
    # ══════════════════════════════════════════════════════

    def produce_carousel(self, format, theme=None, platforms=None, upload=False):
        """Produit un carrousel : génération contenu + rendu PNG multi-plateforme."""
        from src.carousel.generator import CarouselGenerator
        from src.carousel.renderer import render_carousel
        from src.models import Platform

        generator = CarouselGenerator()
        carousel = generator.generate(format, theme)
        generator.save_carousel(carousel)

        # Rendu PNG par plateforme
        carousel_dir = settings.output_dir / "carousels" / f"{carousel.format.value}_{carousel.id}"
        paths = render_carousel(carousel, carousel_dir, platforms)
        carousel.output_paths = {k: [str(p) for p in v] for k, v in paths.items()}

        console.print(f"\n[bold green]Carrousel produit : {carousel.title}[/bold green]")
        for plat, imgs in paths.items():
            console.print(f"  [green]✓[/green] {plat} : {len(imgs)} slides")

        if upload:
            self._upload_carousel(carousel)

        return carousel

    def _upload_carousel(self, carousel):
        """Upload les PNG d'un carrousel vers Google Drive."""
        for platform, img_paths in carousel.output_paths.items():
            for img_path in img_paths:
                path = Path(img_path)
                if path.exists():
                    try:
                        self.gdrive.upload_file(path)
                    except Exception as e:
                        console.print(f"[red]Upload échoué ({path.name}): {e}[/red]")

    def produce_carousel_batch(self, distribution, theme=None, platforms=None, upload=False):
        """Produit un batch de carrousels selon une distribution de formats."""
        from src.models import CarouselFormat

        total = sum(distribution.values())
        console.print(f"\n[bold cyan]═══ Batch carrousels : {total} à produire ═══[/bold cyan]")

        carousels = []
        completed = 0
        failed = 0

        for fmt, count in distribution.items():
            for i in range(count):
                console.print(f"\n[bold]═══ Carrousel {completed + failed + 1}/{total} [{fmt.value}] ═══[/bold]")
                try:
                    carousel = self.produce_carousel(
                        format=fmt, theme=theme, platforms=platforms, upload=upload
                    )
                    carousels.append(carousel)
                    completed += 1
                except Exception as e:
                    failed += 1
                    console.print(f"[red]✗ Échec carrousel : {e}[/red]")

        console.print(f"\n[bold green]{'═' * 50}[/bold green]")
        console.print(f"[bold green]Batch terminé : {completed}/{total} réussis, {failed} échecs[/bold green]")
        return carousels

    def produce_weekly_v2(self, upload=True):
        """
        Produit une semaine : 7 blocs de 4 vidéos + 1 carrousel.
        Total : 28 vidéos + 7 carrousels = 35 pièces.
        Formatés séquentiellement pour repurpose dans l'ordre.
        Jamais 2 formats vidéo identiques consécutifs.
        """
        from src.models import CarouselFormat

        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]   PRODUCTION WEEKLY V2 — 35 PIÈCES   [/bold cyan]")
        console.print("[bold cyan]   28 vidéos + 7 carrousels            [/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")

        # Distribution vidéos (28 au total)
        video_formats = [
            VideoFormat.STORY_POV,
            VideoFormat.STORY_POV,
            VideoFormat.STORY_POV,
            VideoFormat.STORY_POV,
            VideoFormat.STORY_POV,
            VideoFormat.STORY_POV,
            VideoFormat.STORY_POV,
            VideoFormat.DEBUNK,
            VideoFormat.DEBUNK,
            VideoFormat.DEBUNK,
            VideoFormat.DEBUNK,
            VideoFormat.DEBUNK,
            VideoFormat.CAS_REEL,
            VideoFormat.CAS_REEL,
            VideoFormat.CAS_REEL,
            VideoFormat.CAS_REEL,
            VideoFormat.CAS_REEL,
            VideoFormat.SCANDALE,
            VideoFormat.SCANDALE,
            VideoFormat.SCANDALE,
            VideoFormat.TUTO,
            VideoFormat.TUTO,
            VideoFormat.TUTO,
            VideoFormat.TEMOIGNAGE,
            VideoFormat.TEMOIGNAGE,
            VideoFormat.MYTHE,
            VideoFormat.MYTHE,
            VideoFormat.MYTHE,
        ]

        # Mélanger en évitant 2 formats identiques consécutifs
        import random
        random.shuffle(video_formats)
        for _ in range(100):
            has_consecutive = any(
                video_formats[i] == video_formats[i + 1]
                for i in range(len(video_formats) - 1)
            )
            if not has_consecutive:
                break
            random.shuffle(video_formats)

        # Distribution carrousels (7 au total, formats variés)
        carousel_formats = [
            CarouselFormat.MYTHE_VS_FAIT,
            CarouselFormat.CHECKLIST,
            CarouselFormat.AVANT_APRES,
            CarouselFormat.PROCESS,
            CarouselFormat.DO_DONT,
            CarouselFormat.FAQ,
            CarouselFormat.STORY_CAS,
        ]
        random.shuffle(carousel_formats)

        # Construction séquentielle : 4 vidéos + 1 carrousel × 7
        sequence = []
        for i in range(7):
            for j in range(4):
                sequence.append(("video", video_formats[i * 4 + j]))
            sequence.append(("carousel", carousel_formats[i]))

        console.print(f"[bold]Séquence de production ({len(sequence)} pièces) :[/bold]")
        for idx, (kind, fmt) in enumerate(sequence, 1):
            icon = "🎬" if kind == "video" else "📱"
            console.print(f"  {idx:02d}. {icon} {fmt.value}")
        console.print()

        completed = 0
        failed = 0

        for idx, (kind, fmt) in enumerate(sequence, 1):
            prefix = f"{idx:02d}"
            if kind == "video":
                console.print(f"\n[bold]═══ {prefix} — Vidéo [{fmt.value}] ═══[/bold]")
                try:
                    video = self.produce_video(fmt, upload=False)
                    if video.video_path and upload:
                        # Renommer avec préfixe séquentiel pour Drive
                        new_name = f"{prefix}_{video.video_path.name}"
                        new_path = video.video_path.parent / new_name
                        video.video_path.rename(new_path)
                        video.video_path = new_path
                        self.gdrive.upload_video(video)
                    completed += 1
                except Exception as e:
                    failed += 1
                    console.print(f"[red]✗ Échec vidéo {prefix} : {e}[/red]")
            else:
                console.print(f"\n[bold]═══ {prefix} — Carrousel [{fmt.value}] ignoré ═══[/bold]")
                continue

        console.print(f"\n[bold green]{'═' * 50}[/bold green]")
        console.print(f"[bold green]Weekly V2 terminé : {completed}/{len(sequence)} réussis, {failed} échecs[/bold green]")

    def _upload_carousel_prefixed(self, carousel, prefix: str):
        """Upload les PNG d'un carrousel avec préfixe séquentiel."""
        from src.models import Platform
        instagram_paths = carousel.output_paths.get(Platform.INSTAGRAM.value, [])
        for img_path in instagram_paths:
            path = Path(img_path)
            if path.exists():
                new_name = f"{prefix}_{path.name}"
                new_path = path.parent / new_name
                path.rename(new_path)
                try:
                    pdf_path = self._build_carousel_pdf(carousel, prefix)
                    title = f"{prefix}_carousel_{carousel.format.value}"
                    self.gdrive.upload_image(pdf_path, file_title=title, folder_name="NoRadar-Videos")
                except Exception as e:
                    console.print(f"[red]Upload échoué ({new_path.name}): {e}[/red]")

    def _build_carousel_pdf(self, carousel, prefix: str) -> Path:
        from PIL import Image

        carousel_dir = next(Path("outputs/carousels").glob(f"*{carousel.id}")) / "instagram"
        if not carousel_dir.exists():
            raise FileNotFoundError(f"Dossier instagram introuvable : {carousel_dir}")

        png_files = sorted(carousel_dir.glob("*.png"))
        if not png_files:
            raise ValueError(f"Aucun PNG trouvé dans {carousel_dir}")

        images = [Image.open(p).convert("RGB") for p in png_files]
        pdf_path = Path("outputs/carousels") / f"{prefix}_carousel_{carousel.format.value}.pdf"
        images[0].save(pdf_path, save_all=True, append_images=images[1:])
        return pdf_path
