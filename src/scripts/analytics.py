"""
Analytics TikTok + rapport Telegram hebdomadaire.

Récupère les stats des vidéos TikTok publiées et envoie un rapport
formaté sur Telegram chaque semaine.

Variables d'environnement requises :
    TIKTOK_ACCESS_TOKEN     — Token TikTok Business API
    TELEGRAM_BOT_TOKEN      — Token du bot Telegram pour les rapports
    ADMIN_TELEGRAM_CHAT_ID  — Chat ID Telegram de l'admin
"""

import os
from datetime import datetime, timedelta

import httpx
from rich.console import Console

console = Console()

TIKTOK_API_BASE = "https://open.tiktokapis.com/v2"


def _env(key: str) -> str:
    val = os.environ.get(key, "")
    if not val:
        raise ValueError(f"{key} non configurée dans .env")
    return val


def fetch_tiktok_videos(days: int = 7, max_count: int = 50, dry_run: bool = False) -> list[dict]:
    """
    Récupère les vidéos TikTok publiées sur les N derniers jours
    via TikTok Content Posting API (list videos).

    Si dry_run=True et que le token est absent, retourne une liste vide
    au lieu de crasher (permet de tester le pipeline sans credentials).
    """
    token = os.environ.get("TIKTOK_ACCESS_TOKEN", "")
    if not token:
        if dry_run:
            console.print("[yellow]TIKTOK_ACCESS_TOKEN non configurée, skip fetch (dry run)[/yellow]")
            return []
        raise ValueError("TIKTOK_ACCESS_TOKEN non configurée dans .env")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    since = datetime.now() - timedelta(days=days)

    resp = httpx.post(
        f"{TIKTOK_API_BASE}/video/list/",
        headers=headers,
        json={"max_count": max_count},
        params={"fields": "id,title,create_time,like_count,comment_count,share_count,view_count"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json().get("data", {})
    videos = data.get("videos", [])

    # Filtrer par date
    result = []
    for v in videos:
        created = datetime.fromtimestamp(v.get("create_time", 0))
        if created >= since:
            result.append({
                "id": v.get("id", ""),
                "title": v.get("title", "")[:50],
                "views": v.get("view_count", 0),
                "likes": v.get("like_count", 0),
                "comments": v.get("comment_count", 0),
                "shares": v.get("share_count", 0),
                "created": created.strftime("%d/%m"),
            })

    return sorted(result, key=lambda x: x["views"], reverse=True)


def build_report(videos: list[dict], days: int = 7) -> str:
    """Construit le message Telegram formaté."""
    if not videos:
        return "📊 *NoRadar Content — Semaine*\n\nAucune vidéo publiée cette semaine."

    total_views = sum(v["views"] for v in videos)
    total_likes = sum(v["likes"] for v in videos)
    total_shares = sum(v["shares"] for v in videos)
    avg_views = total_views // len(videos) if videos else 0

    lines = [
        f"📊 *NoRadar Content — {days} derniers jours*",
        f"📹 {len(videos)} vidéos publiées\n",
        "🏆 *Top 5 vidéos :*",
    ]

    for i, v in enumerate(videos[:5], 1):
        lines.append(f"{i}. _{v['title']}_")
        lines.append(f"   👁 {v['views']:,} | ❤️ {v['likes']:,} | ↗️ {v['shares']:,}")

    lines.append(f"\n📈 *Totaux semaine :*")
    lines.append(f"  👁 Vues : {total_views:,}")
    lines.append(f"  ❤️ Likes : {total_likes:,}")
    lines.append(f"  ↗️ Partages : {total_shares:,}")
    lines.append(f"  📊 Moyenne/vidéo : {avg_views:,} vues")

    # Worst performer
    if len(videos) > 1:
        worst = videos[-1]
        lines.append(f"\n⚠️ *Moins performante :* _{worst['title']}_ ({worst['views']:,} vues)")

    return "\n".join(lines)


def send_telegram_report(message: str) -> None:
    """Envoie le rapport via Telegram Bot API."""
    token = _env("TELEGRAM_BOT_TOKEN")
    chat_id = _env("ADMIN_TELEGRAM_CHAT_ID")

    resp = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
        },
        timeout=15,
    )
    resp.raise_for_status()
    console.print("[green]✓ Rapport envoyé sur Telegram[/green]")


def run_weekly_report(days: int = 7) -> str:
    """Pipeline complet : fetch TikTok → build rapport → envoi Telegram."""
    console.print(f"[blue]Récupération des stats TikTok ({days} jours)...[/blue]")
    videos = fetch_tiktok_videos(days=days)
    console.print(f"[green]✓ {len(videos)} vidéos récupérées[/green]")

    report = build_report(videos, days=days)
    console.print(f"\n{report}\n")

    send_telegram_report(report)
    return report
