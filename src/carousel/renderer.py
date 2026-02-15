"""Rendu des carrousels en images PNG via HTML + Playwright."""
import asyncio
from pathlib import Path
from typing import Optional

from rich.console import Console
from src.models import Carousel, CarouselFormat, CarouselSlide, Platform

console = Console()

# ══════════════════════════════════════════════════════
# PLATEFORMES
# ══════════════════════════════════════════════════════

PLATFORM_SIZES = {
    Platform.INSTAGRAM: (1080, 1350),
    Platform.TIKTOK: (1080, 1920),
    Platform.X: (1600, 900),
}

# ══════════════════════════════════════════════════════
# COULEURS
# ══════════════════════════════════════════════════════

COLORS = {
    "bg": "#F5F0EB",
    "text_dark": "#1A1A2E",
    "text_body": "#4A4A5A",
    "text_muted": "#BBBBBB",
    "accent": "#f77f00",
    "red": "#DC2626",
    "green": "#059669",
    "gradient": "linear-gradient(135deg, #f77f00, #e63946)",
}


# ══════════════════════════════════════════════════════
# TAILLES ADAPTATIVES
# ══════════════════════════════════════════════════════

def _sizes(w: int, h: int) -> dict:
    landscape = w > h
    tall = h > 1500
    # padding-top en % pour centrer le contenu au tiers supérieur
    pt = "22%" if landscape else ("32%" if tall else "30%")
    return {
        "hook": 90 if landscape else (160 if tall else 140),
        "title": 90 if landscape else (120 if tall else 108),
        "verdict": 96 if landscape else (128 if tall else 112),
        "body": 48 if landscape else (58 if tall else 54),
        "logo": 16 if landscape else (20 if tall else 18),
        "pad": f"{pt} 44px 40px 44px" if landscape else (f"{pt} 44px 40px 44px" if tall else f"{pt} 40px 40px 40px"),
    }


# ══════════════════════════════════════════════════════
# CSS DE BASE
# ══════════════════════════════════════════════════════

def _base_css(w: int, h: int) -> str:
    s = _sizes(w, h)
    return f"""
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800;900&display=swap');
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{
  width:{w}px;height:{h}px;
  font-family:'Outfit',sans-serif;
  overflow:hidden;position:relative;
  background:{COLORS['bg']};
  color:{COLORS['text_dark']};
}}
.logo{{
  position:absolute;top:32px;left:36px;
  font-size:{s['logo']}px;font-weight:900;
  color:{COLORS['accent']};letter-spacing:2px;z-index:10;
}}
.snum{{
  position:absolute;top:32px;right:36px;
  font-size:12px;font-weight:600;color:{COLORS['text_muted']};z-index:10;
}}
.dots{{
  position:absolute;bottom:30px;left:36px;
  display:flex;gap:6px;z-index:10;
}}
.dot{{width:7px;height:7px;border-radius:50%;background:rgba(0,0,0,0.1);}}
.dot.a{{background:{COLORS['accent']};}}
.blob{{
  position:absolute;border-radius:50%;pointer-events:none;z-index:0;
}}
.b1{{
  width:360px;height:360px;top:-100px;right:-100px;
  background:radial-gradient(circle,rgba(247,127,0,0.06) 0%,transparent 70%);
}}
.b2{{
  width:260px;height:260px;bottom:-80px;left:-80px;
  background:radial-gradient(circle,rgba(230,57,70,0.03) 0%,transparent 70%);
}}
.wrap{{position:relative;z-index:1;}}
"""


# ══════════════════════════════════════════════════════
# ÉLÉMENTS COMMUNS
# ══════════════════════════════════════════════════════

def _els(num: int, total: int) -> str:
    dots = "".join(
        f'<div class="dot{" a" if i == num - 1 else ""}"></div>'
        for i in range(total)
    )
    return f"""
<div class="logo">NR | NORADAR</div>
<div class="snum">{num}/{total}</div>
<div class="blob b1"></div>
<div class="blob b2"></div>
<div class="dots">{dots}</div>
"""


# ══════════════════════════════════════════════════════
# TEMPLATE : HOOK (slide 1)
# ══════════════════════════════════════════════════════

def _slide_hook(slide: CarouselSlide, num: int, total: int, w: int, h: int) -> str:
    s = _sizes(w, h)
    css = _base_css(w, h)
    els = _els(num, total)
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{css}
body{{display:flex;flex-direction:column;padding:{s['pad']};}}
.htitle{{
  font-size:{s['hook']}px;font-weight:900;line-height:1.0;
  color:{COLORS['text_dark']};letter-spacing:-1.5px;max-width:90%;
}}
.abar{{width:48px;height:4px;background:{COLORS['accent']};border-radius:2px;margin-top:20px;}}
.swipe{{
  position:absolute;bottom:30px;right:36px;
  font-size:13px;font-weight:700;color:{COLORS['accent']};letter-spacing:1px;z-index:10;
}}
</style></head><body>
{els}
<div class="wrap">
  <div class="htitle">{slide.title}</div>
  <div class="abar"></div>
</div>
<div class="swipe">SWIPE →</div>
</body></html>"""


# ══════════════════════════════════════════════════════
# TEMPLATE : MYTHE VS FAIT
# ══════════════════════════════════════════════════════

def _slide_mythe(slide: CarouselSlide, num: int, total: int, w: int, h: int) -> str:
    s = _sizes(w, h)
    css = _base_css(w, h)
    els = _els(num, total)
    is_true = slide.label_color == "green"
    vc = COLORS['green'] if is_true else COLORS['red']
    label = slide.label or ("VRAI" if is_true else "FAUX")
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{css}
body{{display:flex;flex-direction:column;padding:{s['pad']};}}
.stripe{{position:absolute;left:0;top:0;bottom:0;width:8px;background:{vc};z-index:50;}}
.ctitle{{
  font-size:{s['title']}px;font-weight:800;line-height:1.1;
  color:{COLORS['text_dark']};margin-bottom:20px;max-width:90%;
}}
.verdict{{
  display:inline-block;font-size:{s['verdict']}px;font-weight:900;
  color:{vc};letter-spacing:6px;margin-bottom:24px;
  position:relative;padding-bottom:6px;
}}
.verdict::after{{
  content:'';position:absolute;bottom:0;left:0;right:0;
  height:3px;background:{vc};border-radius:2px;
}}
.btext{{
  font-size:{s['body']}px;font-weight:400;line-height:1.5;
  color:{COLORS['text_body']};max-width:88%;
}}
</style></head><body>
<div class="stripe"></div>
{els}
<div class="wrap">
  <div class="ctitle">{slide.title}</div>
  <div class="verdict">{label}</div>
  <div class="btext">{slide.body}</div>
</div>
</body></html>"""


# ══════════════════════════════════════════════════════
# TEMPLATE : CHECKLIST
# ══════════════════════════════════════════════════════

def _slide_checklist(slide: CarouselSlide, num: int, total: int, w: int, h: int) -> str:
    s = _sizes(w, h)
    css = _base_css(w, h)
    els = _els(num, total)
    step = num - 1
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{css}
body{{display:flex;flex-direction:column;padding:{s['pad']};}}
.ghost{{
  position:absolute;top:80px;right:50px;
  font-size:180px;font-weight:900;color:rgba(247,127,0,0.04);z-index:0;
}}
.row{{display:flex;align-items:flex-start;gap:20px;margin-bottom:20px;}}
.chk{{
  width:36px;height:36px;border:3px solid {COLORS['accent']};
  border-radius:8px;flex-shrink:0;margin-top:4px;
}}
.ctitle{{
  font-size:{s['title']}px;font-weight:800;line-height:1.15;
  color:{COLORS['text_dark']};
}}
.btext{{
  font-size:{s['body']}px;font-weight:400;line-height:1.5;
  color:{COLORS['text_body']};padding-left:56px;max-width:88%;
}}
</style></head><body>
{els}
<div class="ghost">{step}</div>
<div class="wrap">
  <div class="row">
    <div class="chk"></div>
    <div class="ctitle">{slide.title}</div>
  </div>
  <div class="btext">{slide.body}</div>
</div>
</body></html>"""


# ══════════════════════════════════════════════════════
# TEMPLATE : CHIFFRE CHOC
# ══════════════════════════════════════════════════════

def _slide_chiffre(slide: CarouselSlide, num: int, total: int, w: int, h: int) -> str:
    s = _sizes(w, h)
    css = _base_css(w, h)
    els = _els(num, total)
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{css}
body{{display:flex;flex-direction:column;align-items:center;padding:{s["pad"]};text-align:center;}}
.bignum{{
  font-size:{s['hook'] + 20}px;font-weight:900;
  color:{COLORS['accent']};letter-spacing:-2px;margin-bottom:12px;
}}
.abar{{width:48px;height:4px;background:{COLORS['accent']};border-radius:2px;margin:12px auto;}}
.btext{{
  font-size:{s['body']}px;font-weight:400;line-height:1.5;
  color:{COLORS['text_body']};max-width:80%;
}}
</style></head><body>
{els}
<div class="wrap" style="display:flex;flex-direction:column;align-items:center;">
  <div class="bignum">{slide.title}</div>
  <div class="abar"></div>
  <div class="btext">{slide.body}</div>
</div>
</body></html>"""


# ══════════════════════════════════════════════════════
# TEMPLATE : AVANT / APRÈS
# ══════════════════════════════════════════════════════

def _slide_avant_apres(slide: CarouselSlide, num: int, total: int, w: int, h: int) -> str:
    s = _sizes(w, h)
    css = _base_css(w, h)
    els = _els(num, total)
    is_after = slide.label_color == "green" if slide.label_color else num > total // 2
    color = COLORS['green'] if is_after else COLORS['red']
    label = slide.label or ("APRES" if is_after else "AVANT")
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{css}
body{{display:flex;flex-direction:column;padding:{s['pad']};}}
.topbar{{position:absolute;top:0;left:0;right:0;height:5px;background:{color};z-index:5;}}
.phase{{
  display:inline-block;font-size:14px;font-weight:800;letter-spacing:4px;
  color:{color};margin-bottom:28px;
}}
.ctitle{{
  font-size:{s['title']}px;font-weight:800;line-height:1.15;
  color:{COLORS['text_dark']};margin-bottom:16px;max-width:90%;
}}
.btext{{
  font-size:{s['body']}px;font-weight:400;line-height:1.5;
  color:{COLORS['text_body']};max-width:88%;
}}
</style></head><body>
<div class="topbar"></div>
{els}
<div class="wrap">
  <div class="phase">{label}</div>
  <div class="ctitle">{slide.title}</div>
  <div class="btext">{slide.body}</div>
</div>
</body></html>"""


# ══════════════════════════════════════════════════════
# TEMPLATE : PROCESS (ÉTAPES)
# ══════════════════════════════════════════════════════

def _slide_process(slide: CarouselSlide, num: int, total: int, w: int, h: int) -> str:
    s = _sizes(w, h)
    css = _base_css(w, h)
    els = _els(num, total)
    step_label = slide.label or f"ETAPE {num - 1}"
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{css}
body{{display:flex;flex-direction:column;padding:{s['pad']};}}
.timeline{{position:absolute;left:50px;top:25%;bottom:25%;width:3px;background:rgba(247,127,0,0.1);}}
.tdot{{position:absolute;left:43px;top:48%;width:17px;height:17px;border-radius:50%;background:{COLORS['accent']};}}
.badge{{
  display:inline-block;padding:8px 24px;border-radius:30px;
  font-size:13px;font-weight:800;letter-spacing:3px;
  color:white;background:{COLORS['accent']};margin-bottom:24px;
}}
.ctitle{{
  font-size:{s['title']}px;font-weight:800;line-height:1.15;
  color:{COLORS['text_dark']};margin-bottom:16px;max-width:88%;
}}
.btext{{
  font-size:{s['body']}px;font-weight:400;line-height:1.5;
  color:{COLORS['text_body']};max-width:85%;
}}
</style></head><body>
<div class="timeline"></div>
<div class="tdot"></div>
{els}
<div class="wrap" style="padding-left:40px;">
  <div class="badge">{step_label}</div>
  <div class="ctitle">{slide.title}</div>
  <div class="btext">{slide.body}</div>
</div>
</body></html>"""


# ══════════════════════════════════════════════════════
# TEMPLATE : DO / DON'T
# ══════════════════════════════════════════════════════

def _slide_do_dont(slide: CarouselSlide, num: int, total: int, w: int, h: int) -> str:
    s = _sizes(w, h)
    css = _base_css(w, h)
    els = _els(num, total)
    is_do = slide.label_color == "green" if slide.label_color else num % 2 == 0
    color = COLORS['green'] if is_do else COLORS['red']
    icon = "✅" if is_do else "❌"
    label = slide.label or ("FAIS" if is_do else "NE FAIS PAS")
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{css}
body{{display:flex;flex-direction:column;padding:{s['pad']};}}
.stripe{{position:absolute;left:0;top:0;bottom:0;width:5px;background:{color};z-index:5;}}
.dlabel{{
  font-size:16px;font-weight:800;letter-spacing:3px;
  color:{color};margin-bottom:24px;
}}
.ctitle{{
  font-size:{s['title']}px;font-weight:800;line-height:1.15;
  color:{COLORS['text_dark']};margin-bottom:16px;max-width:90%;
}}
.abar{{width:48px;height:4px;background:{COLORS['accent']};border-radius:2px;margin-bottom:16px;}}
.btext{{
  font-size:{s['body']}px;font-weight:400;line-height:1.5;
  color:{COLORS['text_body']};max-width:88%;
}}
</style></head><body>
<div class="stripe"></div>
{els}
<div class="wrap">
  <div class="dlabel">{icon} {label}</div>
  <div class="ctitle">{slide.title}</div>
  <div class="abar"></div>
  <div class="btext">{slide.body}</div>
</div>
</body></html>"""


# ══════════════════════════════════════════════════════
# TEMPLATE : FAQ
# ══════════════════════════════════════════════════════

def _slide_faq(slide: CarouselSlide, num: int, total: int, w: int, h: int) -> str:
    s = _sizes(w, h)
    css = _base_css(w, h)
    els = _els(num, total)
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{css}
body{{display:flex;flex-direction:column;padding:{s['pad']};}}
.qmark{{font-size:64px;font-weight:900;color:{COLORS['accent']};margin-bottom:16px;}}
.ctitle{{
  font-size:{s['title']}px;font-weight:800;line-height:1.15;
  color:{COLORS['text_dark']};margin-bottom:24px;max-width:90%;
}}
.answer{{
  font-size:{s['body']}px;font-weight:400;line-height:1.5;
  color:{COLORS['text_body']};max-width:88%;
  border-left:3px solid {COLORS['accent']};padding-left:20px;
}}
</style></head><body>
{els}
<div class="wrap">
  <div class="qmark">?</div>
  <div class="ctitle">{slide.title}</div>
  <div class="answer">{slide.body}</div>
</div>
</body></html>"""


# ══════════════════════════════════════════════════════
# TEMPLATE : STORY / CAS RÉEL
# ══════════════════════════════════════════════════════

def _slide_story(slide: CarouselSlide, num: int, total: int, w: int, h: int) -> str:
    s = _sizes(w, h)
    css = _base_css(w, h)
    els = _els(num, total)
    pct = int((num / total) * 100)
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{css}
body{{display:flex;flex-direction:column;padding:{s['pad']};}}
.qm{{
  position:absolute;top:80px;left:40px;font-size:140px;
  color:rgba(247,127,0,0.05);font-family:Georgia,serif;z-index:0;
}}
.ctitle{{
  font-size:{s['title']}px;font-weight:700;line-height:1.2;
  color:{COLORS['text_dark']};margin-bottom:16px;max-width:90%;
}}
.abar{{width:48px;height:4px;background:{COLORS['accent']};border-radius:2px;margin-bottom:16px;}}
.btext{{
  font-size:{s['body'] + 1}px;font-weight:400;line-height:1.6;
  color:{COLORS['text_body']};font-style:italic;max-width:85%;
}}
.pbar{{
  position:absolute;bottom:56px;left:40px;right:40px;
  height:3px;background:rgba(0,0,0,0.06);border-radius:2px;z-index:10;
}}
.pfill{{height:100%;width:{pct}%;background:{COLORS['accent']};border-radius:2px;}}
</style></head><body>
<div class="qm">"</div>
{els}
<div class="wrap">
  <div class="ctitle">{slide.title}</div>
  <div class="abar"></div>
  <div class="btext">{slide.body}</div>
</div>
<div class="pbar"><div class="pfill"></div></div>
</body></html>"""


# ══════════════════════════════════════════════════════
# TEMPLATE : CTA (dernière slide)
# ══════════════════════════════════════════════════════

def _slide_cta(slide: CarouselSlide, num: int, total: int, w: int, h: int) -> str:
    s = _sizes(w, h)
    css = _base_css(w, h)
    dots = "".join(
        f'<div class="dot{" a" if i == num - 1 else ""}"></div>'
        for i in range(total)
    )
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{css}
body{{
  background:{COLORS['gradient']};
  display:flex;flex-direction:column;justify-content:center;align-items:center;
  padding:{s['pad']};text-align:center;
}}
.logo{{color:rgba(255,255,255,0.7);}}
.snum{{color:rgba(255,255,255,0.4);}}
.dots .dot{{background:rgba(255,255,255,0.25);}}
.dots .dot.a{{background:white;}}
.ctatitle{{
  font-size:{s['title'] + 4}px;font-weight:900;line-height:1.05;
  color:white;margin-bottom:16px;max-width:85%;
}}
.ctasub{{
  font-size:{s['body']}px;font-weight:400;
  color:rgba(255,255,255,0.85);margin-bottom:32px;line-height:1.4;max-width:80%;
}}
.ctabtn{{
  background:white;color:{COLORS['accent']};
  font-size:24px;font-weight:800;
  padding:18px 52px;border-radius:12px;letter-spacing:1px;
}}
.micro{{font-size:14px;color:rgba(255,255,255,0.55);margin-top:20px;}}
</style></head><body>
<div class="logo">NR | NORADAR</div>
<div class="snum">{num}/{total}</div>
<div class="dots">{dots}</div>
<div class="wrap" style="display:flex;flex-direction:column;align-items:center;">
  <div class="ctatitle">{slide.title}</div>
  <div class="ctasub">{slide.body}</div>
  <div class="ctabtn">noradar.app</div>
  <div class="micro">📸 Photo du PV → Telegram → 60 sec</div>
</div>
</body></html>"""


# ══════════════════════════════════════════════════════
# DISPATCH : slide → template
# ══════════════════════════════════════════════════════

# Map format → template pour les slides de contenu (2 à N-1)
_CONTENT_TEMPLATES = {
    CarouselFormat.MYTHE_VS_FAIT: _slide_mythe,
    CarouselFormat.CHECKLIST: _slide_checklist,
    CarouselFormat.CHIFFRE_CHOC: _slide_chiffre,
    CarouselFormat.AVANT_APRES: _slide_avant_apres,
    CarouselFormat.PROCESS: _slide_process,
    CarouselFormat.DO_DONT: _slide_do_dont,
    CarouselFormat.FAQ: _slide_faq,
    CarouselFormat.STORY_CAS: _slide_story,
}


def _render_slide_html(
    slide: CarouselSlide,
    num: int,
    total: int,
    fmt: CarouselFormat,
    w: int,
    h: int,
) -> str:
    """Genere le HTML d'une slide."""
    # Slide 1 = hook
    if num == 1:
        return _slide_hook(slide, num, total, w, h)
    # Derniere slide = CTA
    if num == total:
        return _slide_cta(slide, num, total, w, h)
    # Slides de contenu
    template_fn = _CONTENT_TEMPLATES.get(fmt, _slide_mythe)
    return template_fn(slide, num, total, w, h)


# ══════════════════════════════════════════════════════
# RENDU PLAYWRIGHT
# ══════════════════════════════════════════════════════

async def _render_slides(
    carousel: Carousel,
    output_dir: Path,
    platform: Platform,
) -> list[Path]:
    """Rend toutes les slides en PNG pour une plateforme."""
    from playwright.async_api import async_playwright

    w, h = PLATFORM_SIZES[platform]
    plat_dir = output_dir / platform.value
    plat_dir.mkdir(parents=True, exist_ok=True)

    paths = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": w, "height": h})

        for i, slide in enumerate(carousel.slides, 1):
            html = _render_slide_html(slide, i, len(carousel.slides), carousel.format, w, h)

            # Ecrire HTML temp
            tmp = plat_dir / f"_temp_{i}.html"
            tmp.write_text(html, encoding="utf-8")

            await page.goto(f"file://{tmp.absolute()}")
            await page.wait_for_timeout(800)  # attendre le chargement des fonts

            png_path = plat_dir / f"slide_{i}.png"
            await page.screenshot(path=str(png_path))
            paths.append(png_path)

            # Nettoyage
            tmp.unlink(missing_ok=True)

            console.print(f"  [green]✓[/green] {platform.value} slide {i}/{len(carousel.slides)}")

        await browser.close()

    return paths


def render_carousel(
    carousel: Carousel,
    output_dir: Path,
    platforms: Optional[list[Platform]] = None,
) -> dict[str, list[Path]]:
    """
    Rend un carrousel pour toutes les plateformes demandees.

    Args:
        carousel: Le carrousel a rendre.
        output_dir: Dossier de sortie.
        platforms: Liste de plateformes. Par defaut : toutes.

    Returns:
        Dict {platform_value: [paths PNG]}.
    """
    if platforms is None:
        platforms = list(Platform)

    result = {}
    for platform in platforms:
        w, h = PLATFORM_SIZES[platform]
        console.print(f"  Rendu {platform.value} ({w}x{h})...")
        paths = asyncio.run(_render_slides(carousel, output_dir, platform))
        result[platform.value] = paths

    return result
