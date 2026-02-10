"""
Orchestrateur de génération de pages SEO.
"""

from datetime import datetime
from pathlib import Path
from rich.console import Console

from src.seo.keywords import PILLAR_PAGES, LONG_TAIL_ARTICLES
from src.seo.generator import SEOPageGenerator

console = Console()

BASE_URL = "https://noradar.app"


class SEOSiteBuilder:
    """Génère toutes les pages SEO du site NoRadar."""

    def __init__(self):
        self.generator = SEOPageGenerator()

    def build_all(self, output_dir: Path):
        """Génère toutes les pages piliers + articles + sitemap + robots."""
        console.print("[bold blue]Génération complète du site SEO NoRadar[/bold blue]\n")

        self.build_pillars(output_dir)
        self.build_articles(output_dir)
        self.generate_sitemap(output_dir)
        self.generate_robots(output_dir)

        total = len(PILLAR_PAGES) + len(LONG_TAIL_ARTICLES)
        console.print(f"\n[bold green]Terminé : {total} pages + sitemap + robots.txt[/bold green]")

    def build_pillars(self, output_dir: Path):
        """Génère toutes les pages piliers."""
        console.print("[bold]Pages piliers[/bold]")
        for page in PILLAR_PAGES:
            self._build_page(page, output_dir, is_pillar=True)

    def build_articles(self, output_dir: Path):
        """Génère tous les articles longue traîne."""
        console.print("[bold]Articles longue traîne[/bold]")
        for article in LONG_TAIL_ARTICLES:
            self._build_page(article, output_dir, is_pillar=False)

    def build_single(self, slug: str, output_dir: Path):
        """Génère une seule page (pilier ou article) par slug."""
        for page in PILLAR_PAGES:
            if page["slug"] == slug:
                self._build_page(page, output_dir, is_pillar=True)
                return

        for article in LONG_TAIL_ARTICLES:
            if article["slug"] == slug:
                self._build_page(article, output_dir, is_pillar=False)
                return

        console.print(f"[red]Slug introuvable : {slug}[/red]")
        console.print("Slugs disponibles :")
        for p in PILLAR_PAGES:
            console.print(f"  [cyan]{p['slug']}[/cyan] (pilier)")
        for a in LONG_TAIL_ARTICLES:
            console.print(f"  [dim]{a['slug']}[/dim] (article)")

    def _build_page(self, page_data: dict, output_dir: Path, is_pillar: bool):
        """Génère et sauvegarde une page."""
        slug = page_data["slug"]
        try:
            if is_pillar:
                html = self.generator.generate_pillar_page(page_data)
                dest = output_dir / f"{slug}.html"
            else:
                html = self.generator.generate_article(page_data)
                dest = output_dir / "blog" / f"{slug}.html"

            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(html, encoding="utf-8")

            size_kb = dest.stat().st_size / 1024
            console.print(f"[green]  ✓ {slug}.html ({size_kb:.0f} Ko)[/green]")

        except Exception as e:
            console.print(f"[red]  ✗ {slug} : {e}[/red]")

    def generate_sitemap(self, output_dir: Path):
        """Génère sitemap.xml avec toutes les URLs SEO."""
        today = datetime.now().strftime("%Y-%m-%d")

        urls = []
        # Page d'accueil
        urls.append(
            f"  <url>\n"
            f"    <loc>{BASE_URL}/</loc>\n"
            f"    <lastmod>{today}</lastmod>\n"
            f"    <priority>1.0</priority>\n"
            f"  </url>"
        )

        # Pages piliers
        for page in PILLAR_PAGES:
            urls.append(
                f"  <url>\n"
                f"    <loc>{BASE_URL}/{page['slug']}</loc>\n"
                f"    <lastmod>{today}</lastmod>\n"
                f"    <priority>0.9</priority>\n"
                f"  </url>"
            )

        # Articles
        for article in LONG_TAIL_ARTICLES:
            urls.append(
                f"  <url>\n"
                f"    <loc>{BASE_URL}/blog/{article['slug']}</loc>\n"
                f"    <lastmod>{today}</lastmod>\n"
                f"    <priority>0.7</priority>\n"
                f"  </url>"
            )

        sitemap = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(urls)
            + "\n</urlset>\n"
        )

        dest = output_dir / "sitemap.xml"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(sitemap, encoding="utf-8")
        console.print(f"[green]  ✓ sitemap.xml ({len(PILLAR_PAGES) + len(LONG_TAIL_ARTICLES) + 1} URLs)[/green]")

    def generate_robots(self, output_dir: Path):
        """Génère robots.txt."""
        robots = (
            "User-agent: *\n"
            "Allow: /\n"
            "\n"
            f"Sitemap: {BASE_URL}/sitemap.xml\n"
        )

        dest = output_dir / "robots.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(robots, encoding="utf-8")
        console.print("[green]  ✓ robots.txt[/green]")
