"""Rendu des carrousels en images PNG via HTML + Playwright."""
import asyncio
from pathlib import Path
from typing import Optional

from rich.console import Console
from src.models import Carousel, CarouselFormat, CarouselSlide, Platform

console = Console()

PLATFORM_SIZES = {
    Platform.INSTAGRAM: (1080, 1350),
    Platform.TIKTOK: (1080, 1920),
    Platform.X: (1600, 900),
}

COLORS = {
    "bg": "#0D0D0D",
    "text_white": "#FFFFFF",
    "text_body": "#999999",
    "text_muted": "rgba(255,255,255,0.2)",
    "accent": "#f77f00",
    "red": "#EF4444",
    "green": "#10B981",
    "gradient": "linear-gradient(135deg, #f77f00, #e63946)",
}


def _sizes(w: int, h: int) -> dict:
    landscape = w > h
    tall = h > 1500
    pt = "22%" if landscape else ("32%" if tall else "30%")
    return {
        "hook": 90 if landscape else (160 if tall else 140),
        "title": 80 if landscape else (110 if tall else 100),
        "verdict": 96 if landscape else (128 if tall else 112),
        "body": 44 if landscape else (54 if tall else 50),
        "logo": 16 if landscape else (20 if tall else 18),
        "pad": f"{pt} 44px 40px 44px",
    }


def _base_css(w: int, h: int) -> str:
    s = _sizes(w, h)
    return f"""
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500;700&display=swap');
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{
  width:{w}px;height:{h}px;
  font-family:'DM Sans',sans-serif;
  overflow:hidden;position:relative;
  background:{COLORS['bg']};
  color:{COLORS['text_white']};
}}
.logo{{
  position:absolute;top:32px;left:36px;
  font-size:{s['logo']}px;font-weight:800;
  color:rgba(247,127,0,0.7);letter-spacing:3px;z-index:10;
  font-family:'Syne',sans-serif;
}}
.snum{{
  position:absolute;top:32px;right:36px;
  font-size:12px;font-weight:600;color:{COLORS['text_muted']};z-index:10;
}}
.dots{{
  position:absolute;bottom:30px;left:36px;
  display:flex;gap:6px;z-index:10;
}}
.dot{{width:6px;height:6px;border-radius:50%;background:rgba(255,255,255,0.1);}}
.dot.a{{background:{COLORS['accent']};}}
.wrap{{position:relative;z-index:1;}}
"""


def _els(num: int, total: int) -> str:
    dots = "".join(
        f'<div class="dot{" a" if i == num - 1 else ""}"></div>'
        for i in range(total)
    )
    return f"""
<div class="logo">NR | NORADAR</div>
<div class="snum">{num}/{total}</div>
<div class="dots">{dots}</div>
"""


def _slide_hook(slide: CarouselSlide, num: int, total: int, w: int, h: int) -> str:
    s = _sizes(w, h)
    title_text = slide.title or ""
    hook_size = s['hook']
    if len(title_text) > 25:
        hook_size = int(hook_size * 0.75)
    if len(title_text) > 40:
        hook_size = int(hook_size * 0.60)
    css = _base_css(w, h)
    els = _els(num, total)
    bg_word = slide.title.split()[0].upper() if slide.title else "AMENDE"
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{css}
body{{display:flex;flex-direction:column;justify-content:flex-end;padding:{s['pad']};}}
.bg-word{{
  position:absolute;top:0;left:-10px;right:0;
  font-family:'Syne',sans-serif;font-size:{s['hook'] + 60}px;font-weight:800;
  color:rgba(247,127,0,0.06);line-height:1;pointer-events:none;
  white-space:nowrap;overflow:hidden;
}}
.accent-line{{width:40px;height:4px;background:{COLORS['accent']};border-radius:2px;margin-bottom:16px;}}
.htitle{{
  font-family:'Syne',sans-serif;font-size:{hook_size}px;font-weight:800;
  line-height:1.05;color:{COLORS['text_white']};letter-spacing:-1px;max-width:90%;
}}
.swipe{{
  position:absolute;top:32px;right:36px;
  font-size:11px;font-weight:800;color:{COLORS['accent']};letter-spacing:2px;z-index:10;
}}
</style></head><body>
<div class="bg-word">{bg_word}</div>
{els}
<div class="swipe">SWIPE →</div>
<div class="wrap">
  <div class="accent-line"></div>
  <div class="htitle">{slide.title}</div>
</div>
</body></html>"""


def _slide_mythe(slide: CarouselSlide, num: int, total: int, w: int, h: int) -> str:
    s = _sizes(w, h)
    css = _base_css(w, h)
    els = _els(num, total)
    is_true = slide.label_color == "green"
    vc = COLORS['green'] if is_true else COLORS['red']
    label = slide.label or ("VRAI" if is_true else "FAUX")
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{css}
body{{display:flex;flex-direction:column;justify-content:center;padding:{s['pad']};padding-left:52px;}}
.stripe{{position:absolute;left:0;top:0;bottom:0;width:6px;background:{vc};z-index:50;}}
.verdict{{
  font-family:'Syne',sans-serif;font-size:{s['verdict']}px;font-weight:800;
  color:{vc};letter-spacing:4px;margin-bottom:16px;line-height:1;
}}
.ctitle{{
  font-size:{s['title']}px;font-weight:700;line-height:1.1;
  color:{COLORS['text_white']};margin-bottom:18px;max-width:90%;
  font-family:'Syne',sans-serif;
}}
.btext{{
  font-size:{s['body']}px;font-weight:400;line-height:1.55;
  color:{COLORS['text_body']};max-width:88%;
}}
</style></head><body>
<div class="stripe"></div>
{els}
<div class="wrap">
  <div class="verdict">{label}</div>
  <div class="ctitle">{slide.title}</div>
  <div class="btext">{slide.body}</div>
</div>
</body></html>"""


def _slide_checklist(slide: CarouselSlide, num: int, total: int, w: int, h: int) -> str:
    s = _sizes(w, h)
    css = _base_css(w, h)
    els = _els(num, total)
    step = num - 1
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{css}
body{{display:flex;flex-direction:column;justify-content:center;padding:{s['pad']};}}
.ghost{{
  position:absolute;top:60px;right:-20px;
  font-family:'Syne',sans-serif;font-size:220px;font-weight:800;
  color:rgba(247,127,0,0.04);line-height:1;pointer-events:none;
}}
.row{{display:flex;align-items:flex-start;gap:18px;margin-bottom:18px;}}
.chk{{
  width:34px;height:34px;flex-shrink:0;margin-top:4px;
  border:2.5px solid {COLORS['accent']};border-radius:8px;
}}
.ctitle{{
  font-family:'Syne',sans-serif;font-size:{s['title']}px;font-weight:800;
  color:{COLORS['text_white']};line-height:1.15;
}}
.btext{{
  font-size:{s['body']}px;font-weight:400;line-height:1.55;
  color:{COLORS['text_body']};padding-left:52px;max-width:88%;
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


def _slide_chiffre(slide: CarouselSlide, num: int, total: int, w: int, h: int) -> str:
    font_import = "@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800;900&family=DM+Sans:wght@400;500;700&display=swap');"
    pad_v = int(h * 0.062)
    pad_h = int(w * 0.085)
    pad_b = int(h * 0.12)
    nr_sz = int(w * 0.022)
    dot_sz = int(w * 0.015)
    dot_gap = int(w * 0.012)
    block_r = int(w * 0.046)
    block_pv = int(h * 0.062)
    block_ph = int(w * 0.069)
    block_mb = int(h * 0.043)
    ctx_sz = int(w * 0.035)
    big_sz = int(w * 0.146)
    unit_sz = int(w * 0.035)
    label_sz = int(w * 0.046)
    is_green = slide.label_color == "green"
    block_bg = "rgba(16,185,129,0.06)" if is_green else "rgba(247,127,0,0.06)"
    block_border = "rgba(16,185,129,0.12)" if is_green else "rgba(247,127,0,0.12)"
    ctx_color = "rgba(16,185,129,0.6)" if is_green else "rgba(247,127,0,0.6)"
    big_color = "#10B981" if is_green else ""
    big_style = f"color:{big_color};" if is_green else "background:linear-gradient(135deg,#f77f00,#ff4d4d);-webkit-background-clip:text;-webkit-text-fill-color:transparent;"
    dots_html = "".join([
        f'<div style="width:{dot_sz}px;height:{dot_sz}px;border-radius:50%;background:{"#f77f00" if i+1==num else "rgba(255,255,255,0.1)"};"></div>'
        for i in range(total)
    ])
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{font_import}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{width:{w}px;height:{h}px;background:#0D0D0D;font-family:'DM Sans',sans-serif;display:flex;flex-direction:column;justify-content:center;padding:{pad_v}px {pad_h}px {pad_b}px;position:relative;}}
</style></head><body>
<div style="position:absolute;top:{int(h*0.04)}px;left:{pad_h}px;font-size:{nr_sz}px;font-weight:800;letter-spacing:3px;color:rgba(247,127,0,0.5);font-family:'Syne',sans-serif;">NR | NORADAR</div>
<div style="position:absolute;top:{int(h*0.04)}px;right:{pad_h}px;font-size:{nr_sz}px;color:rgba(255,255,255,0.12);">{num}/{total}</div>
<div style="background:{block_bg};border:1px solid {block_border};border-radius:{block_r}px;padding:{block_pv}px {block_ph}px;margin-bottom:{block_mb}px;display:flex;flex-direction:column;align-items:center;text-align:center;">
  <div style="font-size:{ctx_sz}px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:{ctx_color};margin-bottom:{int(h*0.03)}px;">{slide.label or ""}</div>
  <div style="font-family:'Syne',sans-serif;font-size:{big_sz}px;font-weight:900;line-height:1;{big_style}">{slide.title}</div>
  <div style="font-size:{unit_sz}px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:rgba(255,255,255,0.25);margin-top:{int(h*0.012)}px;">{slide.label_text if hasattr(slide, 'label_text') else ""}</div>
</div>
<div style="font-size:{label_sz}px;color:#777;line-height:1.55;padding-left:{int(w*0.046)}px;border-left:2px solid rgba(247,127,0,0.3);">{slide.body}</div>
<div style="position:absolute;bottom:{int(h*0.04)}px;left:{pad_h}px;display:flex;gap:{dot_gap}px;">{dots_html}</div>
</body></html>"""


def _slide_avant_apres(slide: CarouselSlide, num: int, total: int, w: int, h: int) -> str:
    font_import = "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@700;800;900&family=DM+Sans:wght@400;500;700&display=swap');"
    pad_v = int(h * 0.054)
    pad_h = int(w * 0.062)
    pad_b = int(h * 0.12)
    gap = int(h * 0.025)
    nr_sz = int(w * 0.022)
    dot_sz = int(w * 0.015)
    dot_gap = int(w * 0.012)
    card_r = int(w * 0.038)
    card_pv = int(h * 0.054)
    card_ph = int(w * 0.062)
    phase_sz = int(w * 0.034)
    amount_sz = int(w * 0.108)
    sub_sz = int(w * 0.042)
    vs_sz = int(w * 0.035)
    if num == 1:
        title_text = slide.title or "Tu as payé trop vite."
        hook_size = int(w * 0.1) if len(title_text) < 25 else int(w * 0.082)
        dots_html = "".join([
            f'<div style="width:{dot_sz}px;height:{dot_sz}px;border-radius:50%;background:{"#f77f00" if i+1==num else "rgba(255,255,255,0.1)"};"></div>'
            for i in range(total)
        ])
        return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{font_import}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{width:{w}px;height:{h}px;background:#0B0B0B;font-family:'DM Sans',sans-serif;display:flex;flex-direction:column;justify-content:space-between;padding:{int(h*0.07)}px {int(w*0.08)}px;position:relative;overflow:hidden;}}
</style></head><body>
<div style="font-family:'Inter',sans-serif;font-size:{int(w*0.075)}px;font-weight:900;color:#F77F00;letter-spacing:-0.5px;">Flashé par un radar ?</div>
<div>
  <div style="font-family:'Inter',sans-serif;font-size:{hook_size}px;font-weight:900;line-height:1.05;color:#FFFFFF;letter-spacing:-1px;margin-bottom:{int(h*0.03)}px;">{title_text}</div>
  <div style="display:flex;flex-direction:column;gap:{int(h*0.025)}px;">
    <div style="display:flex;align-items:baseline;gap:{int(w*0.04)}px;">
      <div style="font-size:{phase_sz}px;font-weight:800;letter-spacing:3px;color:rgba(247,127,0,0.9);min-width:{int(w*0.35)}px;">SANS NORADAR</div>
      <div style="font-family:'Inter',sans-serif;font-size:{int(w*0.16)}px;font-weight:900;color:#F77F00;line-height:1;">-135€</div>
    </div>
    <div style="width:100%;height:1px;background:rgba(255,255,255,0.1);"></div>
    <div style="display:flex;align-items:baseline;gap:{int(w*0.04)}px;">
      <div style="font-size:{phase_sz}px;font-weight:800;letter-spacing:3px;color:rgba(16,185,129,0.8);min-width:{int(w*0.35)}px;">AVEC NORADAR</div>
      <div style="font-family:'Inter',sans-serif;font-size:{int(w*0.16)}px;font-weight:900;color:#10B981;line-height:1;">-34€</div>
    </div>
  </div>
</div>
<div style="display:flex;gap:{dot_gap}px;">{dots_html}</div>
</body></html>"""

    parts = (slide.body or "").split("|||")
    before_amount = parts[0] if len(parts) > 0 else "?"
    before_sub = parts[1] if len(parts) > 1 else ""
    after_amount = parts[2] if len(parts) > 2 else "–"
    after_sub = parts[3] if len(parts) > 3 else ""
    dots_html = "".join([
        f'<div style="width:{dot_sz}px;height:{dot_sz}px;border-radius:50%;background:{"#f77f00" if i+1==num else "rgba(255,255,255,0.1)"};"></div>'
        for i in range(total)
    ])
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{font_import}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{width:{w}px;height:{h}px;background:#0D0D0D;font-family:'DM Sans',sans-serif;display:flex;flex-direction:column;padding:{pad_v}px {pad_h}px {pad_b}px;gap:{gap}px;position:relative;overflow:hidden;}}
</style></head><body>
<div style="position:absolute;top:{int(h*0.04)}px;left:{pad_h}px;font-size:{nr_sz}px;font-weight:800;letter-spacing:3px;color:rgba(247,127,0,0.5);font-family:'Syne',sans-serif;">NR | NORADAR</div>
<div style="position:absolute;top:{int(h*0.04)}px;right:{pad_h}px;font-size:{nr_sz}px;color:rgba(255,255,255,0.12);">{num}/{total}</div>
<div style="flex:1;background:rgba(247,127,0,0.07);border:1px solid rgba(247,127,0,0.15);border-radius:{card_r}px;padding:{card_pv}px {card_ph}px;display:flex;flex-direction:column;justify-content:center;margin-top:{int(h*0.08)}px;">
  <div style="font-size:{phase_sz}px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:rgba(247,127,0,0.9);margin-bottom:{int(h*0.015)}px;">SANS NORADAR</div>
  <div style="font-family:'Inter',sans-serif;font-size:{amount_sz}px;font-weight:900;line-height:1;color:#f77f00;margin-bottom:{int(h*0.01)}px;">{before_amount}</div>
  <div style="font-size:{sub_sz}px;color:rgba(255,255,255,0.85);line-height:1.4;">{before_sub}</div>
</div>
<div style="display:flex;align-items:center;gap:{int(w*0.03)}px;flex-shrink:0;">
  <div style="flex:1;height:1px;background:rgba(247,127,0,0.15);"></div>
  <div style="font-family:'Syne',sans-serif;font-size:{vs_sz}px;font-weight:900;color:rgba(247,127,0,0.6);letter-spacing:2px;">VS</div>
  <div style="flex:1;height:1px;background:rgba(247,127,0,0.15);"></div>
</div>
<div style="flex:1;background:rgba(16,185,129,0.12);border:1px solid rgba(16,185,129,0.35);border-radius:{card_r}px;padding:{card_pv}px {card_ph}px;display:flex;flex-direction:column;justify-content:center;">
  <div style="font-size:{phase_sz}px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:rgba(16,185,129,0.8);margin-bottom:{int(h*0.015)}px;">AVEC NORADAR</div>
  <div style="font-family:'Inter',sans-serif;font-size:{amount_sz}px;font-weight:900;line-height:1;color:#10B981;margin-bottom:{int(h*0.01)}px;">{after_amount}</div>
  <div style="font-size:{sub_sz}px;color:rgba(255,255,255,0.85);line-height:1.4;">{after_sub}</div>
</div>
<div style="position:absolute;bottom:{int(h*0.04)}px;left:{pad_h}px;display:flex;gap:{dot_gap}px;">{dots_html}</div>
</body></html>"""


def _slide_process(slide: CarouselSlide, num: int, total: int, w: int, h: int) -> str:
    s = _sizes(w, h)
    css = _base_css(w, h)
    els = _els(num, total)
    step_label = slide.label or f"ÉTAPE {num - 1}"
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{css}
body{{display:flex;flex-direction:column;justify-content:center;padding:{s['pad']};padding-left:56px;}}
.timeline{{position:absolute;left:40px;top:20%;bottom:20%;width:2px;background:linear-gradient(to bottom,transparent,rgba(247,127,0,0.3),transparent);}}
.tdot{{
  position:absolute;left:33px;top:50%;transform:translateY(-50%);
  width:14px;height:14px;border-radius:50%;background:{COLORS['accent']};
  box-shadow:0 0 12px rgba(247,127,0,0.5);
}}
.badge{{
  display:inline-block;padding:6px 18px;border-radius:30px;
  font-size:11px;font-weight:800;letter-spacing:3px;
  color:#0D0D0D;background:{COLORS['accent']};margin-bottom:18px;
}}
.ctitle{{
  font-family:'Syne',sans-serif;font-size:{s['title']}px;font-weight:800;
  line-height:1.1;color:{COLORS['text_white']};margin-bottom:14px;max-width:88%;
}}
.btext{{
  font-size:{s['body']}px;font-weight:400;line-height:1.55;
  color:{COLORS['text_body']};max-width:85%;
}}
</style></head><body>
<div class="timeline"></div>
<div class="tdot"></div>
{els}
<div class="wrap">
  <div class="badge">{step_label}</div>
  <div class="ctitle">{slide.title}</div>
  <div class="btext">{slide.body}</div>
</div>
</body></html>"""


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
body{{display:flex;flex-direction:column;justify-content:center;padding:{s['pad']};padding-left:52px;}}
.stripe{{position:absolute;left:0;top:0;bottom:0;width:6px;background:{color};z-index:5;}}
.dlabel{{
  font-size:11px;font-weight:800;letter-spacing:4px;
  color:{color};margin-bottom:20px;
}}
.ctitle{{
  font-family:'Syne',sans-serif;font-size:{s['title']}px;font-weight:800;
  line-height:1.1;color:{COLORS['text_white']};margin-bottom:14px;max-width:90%;
}}
.btext{{
  font-size:{s['body']}px;font-weight:400;line-height:1.55;
  color:{COLORS['text_body']};max-width:88%;
}}
</style></head><body>
<div class="stripe"></div>
{els}
<div class="wrap">
  <div class="dlabel">{icon} {label}</div>
  <div class="ctitle">{slide.title}</div>
  <div class="btext">{slide.body}</div>
</div>
</body></html>"""


def _slide_faq(slide: CarouselSlide, num: int, total: int, w: int, h: int) -> str:
    s = _sizes(w, h)
    css = _base_css(w, h)
    els = _els(num, total)
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{css}
body{{display:flex;flex-direction:column;justify-content:center;padding:{s['pad']};}}
.qmark{{
  font-family:'Syne',sans-serif;font-size:64px;font-weight:800;
  color:{COLORS['accent']};line-height:1;margin-bottom:14px;
}}
.ctitle{{
  font-family:'Syne',sans-serif;font-size:{s['title']}px;font-weight:800;
  line-height:1.1;color:{COLORS['text_white']};margin-bottom:18px;max-width:90%;
}}
.answer{{
  font-size:{s['body']}px;font-weight:400;line-height:1.55;
  color:{COLORS['text_body']};max-width:88%;
  border-left:3px solid {COLORS['accent']};padding-left:18px;
}}
</style></head><body>
{els}
<div class="wrap">
  <div class="qmark">?</div>
  <div class="ctitle">{slide.title}</div>
  <div class="answer">{slide.body}</div>
</div>
</body></html>"""


def _slide_story(slide: CarouselSlide, num: int, total: int, w: int, h: int) -> str:
    s = _sizes(w, h)
    css = _base_css(w, h)
    els = _els(num, total)
    pct = int((num / total) * 100)
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{css}
body{{display:flex;flex-direction:column;justify-content:center;padding:{s['pad']};}}
.qm{{
  position:absolute;top:60px;left:30px;font-size:160px;
  color:rgba(247,127,0,0.05);font-family:Georgia,serif;z-index:0;
}}
.ctitle{{
  font-family:'Syne',sans-serif;font-size:{s['title']}px;font-weight:700;
  line-height:1.2;color:{COLORS['text_white']};margin-bottom:14px;max-width:90%;
}}
.abar{{width:40px;height:4px;background:{COLORS['accent']};border-radius:2px;margin-bottom:14px;}}
.btext{{
  font-size:{s['body'] + 1}px;font-weight:400;line-height:1.6;
  color:{COLORS['text_body']};font-style:italic;max-width:85%;
}}
.pbar{{
  position:absolute;bottom:56px;left:36px;right:36px;
  height:3px;background:rgba(255,255,255,0.06);border-radius:2px;z-index:10;
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


def _slide_countdown(slide: CarouselSlide, num: int, total: int, w: int, h: int) -> str:
    is_hook = num == 1
    label = slide.label or ("AMENDE RADAR" if is_hook else f"ERREUR {num - 1}")
    font_import = "@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800;900&family=DM+Sans:wght@400;500;700&family=Inter:wght@700;800;900&display=swap');"
    pad = int(w * 0.08)
    stripe_w = int(w * 0.012)
    title_size = int(w * 0.11) if is_hook else int(w * 0.065)
    body_size = int(w * 0.032)
    badge_size = int(w * 0.026)
    nr_size = int(w * 0.022)
    dot_size = int(w * 0.013)
    dot_gap = int(w * 0.012)
    dots_html = "".join([
        f'<div style="width:{dot_size}px;height:{dot_size}px;border-radius:50%;background:{"#f77f00" if i+1==num else "rgba(255,255,255,0.12)"};"></div>'
        for i in range(total)
    ])
    badge_html = f'<div style="display:inline-block;padding:3px 12px;border-radius:4px;font-size:{int(w*0.042)}px;font-weight:800;letter-spacing:3px;color:#f77f00;border:1px solid rgba(247,127,0,0.4);background:rgba(247,127,0,0.1);margin-bottom:{int(h*0.025)}px;">{label}</div>' if label else ""
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{font_import}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{
  width:{w}px;height:{h}px;background:#0D0D0D;
  font-family:'DM Sans',sans-serif;
  display:flex;flex-direction:column;justify-content:center;
  padding:{int(h*0.04)}px {pad}px {pad}px {int(w*0.08)}px;
  position:relative;overflow:hidden;
}}
</style></head><body>
<div style="position:absolute;left:0;top:0;bottom:0;width:{int(w*0.04)}px;background:#f77f00;"></div>
<div style="position:absolute;top:{int(h*0.03)}px;left:{pad}px;font-size:{nr_size}px;font-weight:800;letter-spacing:3px;color:rgba(247,127,0,0.5);font-family:'Syne',sans-serif;">{f"NR | NORADAR"}</div>
<div style="position:absolute;top:{int(h*0.03)}px;right:{pad}px;font-size:{nr_size}px;color:rgba(255,255,255,0.12);">{num}/{total}</div>
<div style="position:absolute;bottom:{int(h*0.03)}px;left:{pad}px;display:flex;gap:{dot_gap}px;">{dots_html}</div>
<div>
  {badge_html}
  <div style="font-family:'Inter',sans-serif;font-size:{title_size}px;font-weight:900;line-height:1.1;color:#fff;margin-bottom:{int(h*0.025)}px;letter-spacing:-0.3px;">{slide.title}</div>
  <div style="font-size:{int(w*0.052)}px;color:rgba(247,127,0,0.9);line-height:1.45;font-weight:600;font-family:'DM Sans',sans-serif;">{slide.body}</div>
</div>
</body></html>"""


def _slide_telegram(slide: CarouselSlide, num: int, total: int, w: int, h: int) -> str:
    is_result = slide.label_color == "green"
    is_processing = slide.label_color == "orange"
    is_first = num == 1
    header_status = "🟢 en ligne" if (is_first or is_result) else "⚡ analyse en cours..."
    font_import = "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');"
    # Couleurs thème clair Telegram
    BG = "#DAE6F0"          # fond bleu clair Telegram
    HEADER_BG = "#527DA3"   # header bleu Telegram
    BOT_BG = "#FFFFFF"      # bulle bot blanche
    USER_BG = "#EFFDDE"     # bulle user vert clair
    BOT_TEXT = "#000000"
    USER_TEXT = "#000000"
    TIME_COLOR = "#A0AEB8"
    INPUT_BG = "#FFFFFF"
    # Tailles
    avatar  = int(w * 0.11)
    hpad_v  = int(h * 0.032)
    hpad_h  = int(w * 0.052)
    hgap    = int(w * 0.035)
    name_sz = int(w * 0.042)
    st_sz   = int(w * 0.034)
    bpad_v  = int(h * 0.03)
    bpad_h  = int(w * 0.04)
    bgap    = int(h * 0.02)
    msg_pv  = int(h * 0.022)
    msg_ph  = int(w * 0.042)
    msg_r   = int(w * 0.032)
    msg_sz  = int(w * 0.038)
    time_sz = int(w * 0.028)
    dot_sz  = int(w * 0.013)
    dot_gap = int(w * 0.011)
    shadow  = "0 1px 2px rgba(0,0,0,0.15)"
    dots_html = "".join([
        f'<div style="width:{dot_sz}px;height:{dot_sz}px;border-radius:50%;background:{"#f77f00" if i+1==num else "rgba(255,255,255,0.4)"};flex-shrink:0;"></div>'
        for i in range(total)
    ])
    def bot_bubble(text):
        return f'<div style="background:{BOT_BG};color:{BOT_TEXT};align-self:flex-start;border-radius:{msg_r}px;border-top-left-radius:{int(w*0.008)}px;padding:{msg_pv}px {msg_ph}px;font-size:{msg_sz}px;line-height:1.5;max-width:85%;box-shadow:{shadow};">{text}</div>'
    def user_bubble(text):
        return f'<div style="background:{USER_BG};color:{USER_TEXT};align-self:flex-end;border-radius:{msg_r}px;border-top-right-radius:{int(w*0.008)}px;padding:{msg_pv}px {msg_ph}px;font-size:{msg_sz}px;line-height:1.5;max-width:85%;box-shadow:{shadow};">{text}</div>'
    def time_div(t, align="left"):
        return f'<div style="font-size:{time_sz}px;color:{TIME_COLOR};text-align:{align};margin-top:{int(h*0.004)}px;">{t}</div>'
    def btn(text, color="#4CAF7C"):
        return f'<div style="background:{color};color:#fff;font-size:{int(w*0.036)}px;font-weight:700;padding:{int(h*0.018)}px {msg_ph}px;border-radius:{int(w*0.02)}px;text-align:center;align-self:stretch;margin-top:{int(h*0.008)}px;">{text}</div>'
    if is_first:
        body_html = user_bubble(slide.title) + time_div("12:39", "right") + bot_bubble("🚗 Amende radar ?<br>Envoyez-moi une <b>photo de votre PV</b>, je m'occupe de tout.") + time_div("12:40") + user_bubble("📸 [Photo du PV]") + time_div("12:41", "right")
    elif is_result:
        amount = slide.title
        detail = slide.body
        body_html = f'<div style="background:#EFFDDE;border-radius:{msg_r}px;border-top-left-radius:{int(w*0.008)}px;padding:{msg_pv}px {msg_ph}px;align-self:flex-start;max-width:90%;box-shadow:{shadow};"><div style="font-size:{int(w*0.034)}px;color:#2d7a4f;font-weight:700;margin-bottom:{int(h*0.01)}px;">✅ Amende annulée</div><div style="font-size:{int(w*0.07)}px;font-weight:900;color:#1a8a4a;line-height:1.1;">{amount}</div><div style="font-size:{int(w*0.034)}px;color:#555;margin-top:{int(h*0.01)}px;">{detail}</div></div>' + time_div("J+14")
    else:
        body_html = bot_bubble("✅ <b>Dossier éligible</b><br><br>Votre amende peut être contestée.<br><br>🛡️ <b>Garantie :</b> Points sauvés ou remboursé<br><br>💳 <b>34€ tout compris</b>") + time_div("12:23") + user_bubble("C'est vraiment automatique ?") + time_div("12:24", "right") + bot_bubble("Oui. On s'occupe de tout. ✅") + time_div("12:24") + btn("💳 Payer 34€ →")
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{font_import}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{width:{w}px;height:{h}px;font-family:'Inter',sans-serif;background:{BG};display:flex;flex-direction:column;overflow:hidden;}}
</style></head><body>
<div style="background:{HEADER_BG};padding:{hpad_v}px {hpad_h}px;display:flex;align-items:center;gap:{hgap}px;flex-shrink:0;">
  <div style="width:{avatar}px;height:{avatar}px;border-radius:50%;background:linear-gradient(135deg,#f77f00,#e63946);display:flex;align-items:center;justify-content:center;font-size:{int(w*0.038)}px;font-weight:800;color:white;flex-shrink:0;">NR</div>
  <div>
    <div style="font-size:{name_sz}px;font-weight:700;color:#fff;">noradar</div>
    <div style="font-size:{st_sz}px;color:rgba(255,255,255,0.75);">{header_status}</div>
  </div>
</div>
<div style="flex:1;padding:{bpad_v}px {bpad_h}px;display:flex;flex-direction:column;gap:{bgap}px;overflow:hidden;">
  {body_html}
</div>
<div style="background:{HEADER_BG};padding:{int(h*0.022)}px {bpad_h}px;display:flex;align-items:center;gap:{int(w*0.025)}px;flex-shrink:0;position:relative;">
  <div style="flex:1;background:{INPUT_BG};border-radius:{int(w*0.05)}px;padding:{int(h*0.014)}px {int(w*0.04)}px;font-size:{int(w*0.034)}px;color:{TIME_COLOR};">Message</div>
  <div style="display:flex;gap:{dot_gap}px;margin-left:{int(w*0.02)}px;">{dots_html}</div>
</div>
</body></html>"""


def _slide_cta(slide: CarouselSlide, num: int, total: int, w: int, h: int) -> str:
    s = _sizes(w, h)
    css = _base_css(w, h)
    dots = "".join(
        f'<div class="dot{" a" if i == num - 1 else ""}"></div>'
        for i in range(total)
    )
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@700;800;900&display=swap');
{css}
body{{
  background:{COLORS['gradient']};
  display:flex;flex-direction:column;justify-content:center;align-items:center;
  padding:{s['pad']};text-align:center;
}}
.logo{{color:rgba(255,255,255,0.6);}}
.snum{{color:rgba(255,255,255,0.3);}}
.dots .dot{{background:rgba(255,255,255,0.2);}}
.dots .dot.a{{background:white;}}
.ctatitle{{
  font-family:'Inter',sans-serif;font-size:{s['title'] + 6}px;font-weight:900;
  line-height:1.05;color:white;margin-bottom:14px;max-width:85%;
}}
.ctasub{{
  font-family:'DM Sans',sans-serif;font-size:{s['body']}px;color:rgba(255,255,255,0.85);margin-bottom:18px;line-height:1.45;
}}
.ctabtn{{
  background:white;color:{COLORS['accent']};
  font-size:22px;font-weight:800;
  padding:16px 48px;border-radius:12px;letter-spacing:1px;margin-bottom:12px;
}}
.micro{{font-size:13px;color:rgba(255,255,255,0.5);margin-top:12px;}}
</style></head><body>
<div class="snum">{num}/{total}</div>
<div class="dots">{dots}</div>
<div class="wrap" style="display:flex;flex-direction:column;align-items:center;">
  <div class="ctatitle">{slide.title}</div>
  <div class="ctasub">{slide.body}</div>
  <div style="font-family:'Inter',sans-serif;font-size:{int(w*0.055)}px;font-weight:900;color:#FFFFFF;background:rgba(0,0,0,0.3);border:2px solid rgba(255,255,255,0.6);border-radius:{int(w*0.02)}px;padding:{int(h*0.018)}px {int(w*0.06)}px;display:inline-block;letter-spacing:1px;">noradar.app</div>
  <div style="font-size:{int(w*0.032)}px;color:rgba(255,255,255,0.7);margin-top:{int(h*0.02)}px;">lien en bio · 34€ · remboursé si ça rate</div>
</div>
</body></html>"""


_CONTENT_TEMPLATES = {
    CarouselFormat.MYTHE_VS_FAIT: _slide_mythe,
    CarouselFormat.CHECKLIST: _slide_checklist,
    CarouselFormat.CHIFFRE_CHOC: _slide_chiffre,
    CarouselFormat.AVANT_APRES: _slide_avant_apres,
    CarouselFormat.PROCESS: _slide_process,
    CarouselFormat.DO_DONT: _slide_do_dont,
    CarouselFormat.FAQ: _slide_faq,
    CarouselFormat.STORY_CAS: _slide_story,
    CarouselFormat.COUNTDOWN: _slide_countdown,
    CarouselFormat.SCREENSHOT_TELEGRAM: _slide_telegram,
}


def _render_slide_html(
    slide: CarouselSlide,
    num: int,
    total: int,
    fmt: CarouselFormat,
    w: int,
    h: int,
) -> str:
    if num == 1 and fmt not in (CarouselFormat.COUNTDOWN, CarouselFormat.SCREENSHOT_TELEGRAM, CarouselFormat.AVANT_APRES):
        return _slide_hook(slide, num, total, w, h)
    if num == total:
        return _slide_cta(slide, num, total, w, h)
    template_fn = _CONTENT_TEMPLATES.get(fmt, _slide_mythe)
    return template_fn(slide, num, total, w, h)


async def _render_slides(
    carousel: Carousel,
    output_dir: Path,
    platform: Platform,
) -> list[Path]:
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
            tmp = plat_dir / f"_temp_{i}.html"
            tmp.write_text(html, encoding="utf-8")
            await page.goto(f"file://{tmp.absolute()}")
            await page.wait_for_timeout(800)
            png_path = plat_dir / f"slide_{i}.png"
            await page.screenshot(path=str(png_path))
            paths.append(png_path)
            tmp.unlink(missing_ok=True)
            console.print(f"  [green]✓[/green] {platform.value} slide {i}/{len(carousel.slides)}")

        await browser.close()

    return paths


def render_carousel(
    carousel: Carousel,
    output_dir: Path,
    platforms: Optional[list[Platform]] = None,
) -> dict[str, list[Path]]:
    if platforms is None:
        platforms = list(Platform)

    result = {}
    for platform in platforms:
        w, h = PLATFORM_SIZES[platform]
        console.print(f"  Rendu {platform.value} ({w}x{h})...")
        paths = asyncio.run(_render_slides(carousel, output_dir, platform))
        result[platform.value] = paths

    return result
