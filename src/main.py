"""
CLI du Content Engine NoRadar.

Usage:
    content-engine produce --format scandale
    content-engine batch --count 10
    content-engine weekly
    content-engine sync
"""

import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table

from src.config import settings
from src.models import VideoFormat

app = typer.Typer(
    name="content-engine",
    help="🎬 NoRadar Content Engine - Production automatisée de vidéos marketing",
    add_completion=False,
)
console = Console()


@app.command()
def init():
    """Initialise les dossiers et vérifie la configuration."""
    console.print("[bold blue]Initialisation du Content Engine...[/bold blue]\n")

    # Créer les dossiers
    settings.ensure_directories()
    console.print("[green]✓ Dossiers créés[/green]")

    # Vérifier les credentials
    checks = {
        "GEMINI_API_KEY": bool(settings.gemini_api_key),
        "GOOGLE_CLOUD_PROJECT": bool(settings.google_cloud_project),
        "GDRIVE_FOLDER_ID": bool(settings.gdrive_folder_id),
    }

    table = Table(title="Configuration")
    table.add_column("Variable", style="cyan")
    table.add_column("Status", style="green")

    for var, ok in checks.items():
        status = "✓ Configuré" if ok else "✗ Manquant"
        style = "green" if ok else "red"
        table.add_row(var, f"[{style}]{status}[/{style}]")

    console.print(table)

    if not all(checks.values()):
        console.print("\n[yellow]⚠ Complétez le fichier .env avec vos clés API[/yellow]")


@app.command()
def produce(
    format: str = typer.Option(..., "--format", "-f", help="Format: scandale, tuto, temoignage, mythe, chiffre_choc, ultra_court"),
    theme: Optional[str] = typer.Option(None, "--theme", "-t", help="Thème spécifique"),
    script_only: bool = typer.Option(False, "--script-only", "-s", help="Génère uniquement le script"),
    no_upload: bool = typer.Option(False, "--no-upload", help="Ne pas uploader sur Google Drive"),
    background: Optional[Path] = typer.Option(None, "--background", "-b", help="Image de fond"),
    voice: str = typer.Option("google", "--voice", "-v", help="Moteur vocal: google ou elevenlabs"),
):
    """Produit une vidéo complète."""
    from src.pipeline.orchestrator import ContentOrchestrator

    try:
        video_format = VideoFormat(format.lower())
    except ValueError:
        console.print(f"[red]Format invalide : {format}[/red]")
        console.print(f"Formats disponibles : {', '.join(f.value for f in VideoFormat)}")
        raise typer.Exit(1)

    if voice not in ("google", "elevenlabs"):
        console.print(f"[red]Moteur vocal invalide : {voice}[/red]")
        console.print("Valeurs possibles : google, elevenlabs")
        raise typer.Exit(1)

    orchestrator = ContentOrchestrator()

    if script_only:
        orchestrator.script_only(video_format, theme)
    else:
        orchestrator.produce_video(
            format=video_format,
            theme=theme,
            background_image=background,
            upload=not no_upload,
            voice_engine=voice,
        )


@app.command()
def batch(
    count: int = typer.Option(10, "--count", "-c", help="Nombre total de vidéos"),
    theme: Optional[str] = typer.Option(None, "--theme", "-t", help="Thème spécifique"),
    no_upload: bool = typer.Option(False, "--no-upload", help="Ne pas uploader"),
):
    """Produit un batch de vidéos avec distribution automatique."""
    from src.pipeline.orchestrator import ContentOrchestrator

    # Distribution proportionnelle
    distribution = {
        VideoFormat.SCANDALE: max(1, int(count * 0.22)),
        VideoFormat.TUTO: max(1, int(count * 0.22)),
        VideoFormat.TEMOIGNAGE: max(1, int(count * 0.18)),
        VideoFormat.MYTHE: max(1, int(count * 0.10)),
        VideoFormat.CHIFFRE_CHOC: max(1, int(count * 0.10)),
        VideoFormat.VRAI_FAUX: max(1, int(count * 0.18)),
    }

    # Ajuster pour atteindre le total exact
    current_total = sum(distribution.values())
    if current_total < count:
        distribution[VideoFormat.SCANDALE] += count - current_total

    console.print("[bold]Distribution du batch :[/bold]")
    for fmt, n in distribution.items():
        console.print(f"  {fmt.value}: {n}")

    orchestrator = ContentOrchestrator()
    orchestrator.produce_batch(distribution, theme=theme, upload=not no_upload)


@app.command()
def weekly(
    no_upload: bool = typer.Option(False, "--no-upload", help="Ne pas uploader"),
):
    """Produit le contenu d'une semaine (30 vidéos)."""
    from src.pipeline.orchestrator import ContentOrchestrator

    orchestrator = ContentOrchestrator()
    orchestrator.produce_weekly(upload=not no_upload)


@app.command()
def sync():
    """Synchronise les vidéos vers Google Drive."""
    from src.storage.gdrive import sync_ready_videos

    urls = sync_ready_videos()
    if urls:
        console.print(f"\n[green]✓ {len(urls)} vidéos synchronisées[/green]")


@app.command()
def voices():
    """Liste les voix françaises disponibles."""
    from src.voice.generator import VoiceGenerator, FRENCH_VOICES

    console.print("[bold]Voix françaises recommandées :[/bold]\n")

    table = Table()
    table.add_column("Alias", style="cyan")
    table.add_column("Nom complet", style="green")
    table.add_column("Type")

    for alias, name in FRENCH_VOICES.items():
        voice_type = "Wavenet" if "Wavenet" in name else "Neural2" if "Neural2" in name else "Standard"
        table.add_row(alias, name, voice_type)

    console.print(table)
    console.print(f"\n[dim]Voix actuelle : {settings.tts_voice_name}[/dim]")


@app.command()
def formats():
    """Affiche les formats de contenu disponibles."""
    from src.scripts.generator import FORMAT_PROMPTS

    for fmt in VideoFormat:
        console.print(f"\n[bold cyan]═══ {fmt.value.upper()} ═══[/bold cyan]")
        prompt = FORMAT_PROMPTS[fmt]
        # Afficher les premières lignes
        lines = prompt.strip().split("\n")[:6]
        for line in lines:
            console.print(f"  {line}")
        console.print("  ...")


@app.command()
def status():
    """Affiche le statut de production."""
    from pathlib import Path

    dirs = {
        "Scripts": settings.output_dir / "scripts",
        "Audio": settings.output_dir / "audio",
        "Vidéos": settings.output_dir / "videos",
        "Ready (pour Repurpose)": settings.output_dir / "ready",
        "Uploadés": settings.output_dir / "uploaded",
    }

    table = Table(title="Statut de production")
    table.add_column("Dossier", style="cyan")
    table.add_column("Fichiers", justify="right")

    for name, path in dirs.items():
        if path.exists():
            count = len(list(path.glob("*")))
            table.add_row(name, str(count))
        else:
            table.add_row(name, "[dim]0[/dim]")

    console.print(table)


@app.command()
def clean(
    all: bool = typer.Option(False, "--all", "-a", help="Supprime tout (y compris uploaded)"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Confirme sans demander"),
):
    """Nettoie les fichiers temporaires."""
    import shutil

    dirs_to_clean = ["scripts", "audio", "videos", "ready", "temp"]
    if all:
        dirs_to_clean.append("uploaded")

    if not confirm:
        confirm = typer.confirm("Supprimer tous les fichiers de production ?")

    if confirm:
        for dir_name in dirs_to_clean:
            dir_path = settings.output_dir / dir_name
            if dir_path.exists():
                shutil.rmtree(dir_path)
                dir_path.mkdir()
                console.print(f"[green]✓ Nettoyé : {dir_name}/[/green]")

        console.print("\n[bold green]Nettoyage terminé[/bold green]")


@app.command()
def hybrid_test():
    """POC: Test rendu hybride avatar + B-roll"""
    from src.video.hybrid_composer import create_hybrid_test
    create_hybrid_test()


@app.command()
def seo(
    page: Optional[str] = typer.Option(None, "--page", "-p", help="Slug d'une page spécifique"),
    pillar_only: bool = typer.Option(False, "--pillar-only", help="Uniquement les pages piliers"),
    articles_only: bool = typer.Option(False, "--articles-only", help="Uniquement les articles"),
):
    """Génère les pages SEO du site NoRadar."""
    from src.seo.builder import SEOSiteBuilder

    builder = SEOSiteBuilder()
    output_dir = settings.output_dir / "seo"

    if page:
        builder.build_single(page, output_dir)
    elif pillar_only:
        builder.build_pillars(output_dir)
    elif articles_only:
        builder.build_articles(output_dir)
    else:
        builder.build_all(output_dir)


@app.command()
def carousel(
    format: str = typer.Option(..., "--format", "-f", help="Format: mythe_vs_fait, checklist, chiffre_choc, avant_apres, process, do_dont, faq, story_cas"),
    theme: Optional[str] = typer.Option(None, "--theme", "-t", help="Thème spécifique"),
    platform: Optional[str] = typer.Option(None, "--platform", "-p", help="Plateforme: instagram, tiktok, x (défaut: toutes)"),
    count: int = typer.Option(1, "--count", "-c", help="Nombre de carrousels à produire"),
    no_upload: bool = typer.Option(False, "--no-upload", help="Ne pas uploader sur Google Drive"),
):
    """Produit un ou plusieurs carrousels (slides PNG multi-plateforme)."""
    from src.models import CarouselFormat, Platform
    from src.pipeline.orchestrator import ContentOrchestrator

    try:
        carousel_format = CarouselFormat(format.lower())
    except ValueError:
        console.print(f"[red]Format invalide : {format}[/red]")
        console.print(f"Formats disponibles : {', '.join(f.value for f in CarouselFormat)}")
        raise typer.Exit(1)

    platforms = None
    if platform:
        try:
            platforms = [Platform(platform.lower())]
        except ValueError:
            console.print(f"[red]Plateforme invalide : {platform}[/red]")
            console.print(f"Plateformes disponibles : {', '.join(p.value for p in Platform)}")
            raise typer.Exit(1)

    orchestrator = ContentOrchestrator()

    if count == 1:
        orchestrator.produce_carousel(
            format=carousel_format, theme=theme, platforms=platforms, upload=not no_upload
        )
    else:
        distribution = {carousel_format: count}
        orchestrator.produce_carousel_batch(
            distribution, theme=theme, platforms=platforms, upload=not no_upload
        )


if __name__ == "__main__":
    app()
