"""
Générateur de pages HTML SEO via Google Gemini.
"""

import json
import re
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, DeadlineExceeded
from rich.console import Console

from src.config import settings
from src.utils.retry import with_retry
from src.seo.keywords import PILLAR_PAGES, INTERNAL_LINKS

console = Console()


# ═══════════════════════════════════════════════════════════════
# PROMPTS SEO
# ═══════════════════════════════════════════════════════════════

PILLAR_PROMPT = """Tu es un expert SEO et rédacteur juridique vulgarisateur.
Génère le CONTENU HTML (uniquement le contenu à l'intérieur du <main>, pas le <html>/<head>) pour une page pilier SEO.

SUJET : {title}
MOT-CLÉ PRINCIPAL : {keyword}

RÈGLES DE CONTENU — NE JAMAIS VIOLER :
1. Tu éduques sur le PROBLÈME, tu ne donnes JAMAIS la SOLUTION concrète
2. Tu expliques que contester est un DROIT et que c'est POSSIBLE — mais tu ne dis jamais COMMENT rédiger une contestation
3. INTERDIT de fournir : modèle de lettre, motifs juridiques précis, articles de loi exploitables, stratégie de contestation, exemple de requête en exonération
4. Tu peux mentionner que des motifs existent (vice de forme, erreur de procédure, etc.) SANS les détailler
5. Chaque section doit naturellement pousser le lecteur vers NoRadar comme solution : "C'est possible, mais c'est technique → NoRadar le fait pour toi"
6. Le ton est : expert accessible qui montre qu'il maîtrise le sujet SANS révéler ses secrets
7. Les informations publiques sont OK : délais, montants, marges techniques, droits généraux du conducteur
8. Termine TOUJOURS par un CTA fort vers NoRadar

L'OBJECTIF de chaque page est de convaincre le lecteur que :
- Son amende est probablement contestable
- La procédure est trop complexe pour être faite seul
- NoRadar est la solution la plus simple et la moins chère

RÈGLES :
- 1500-2000 mots
- Structuré avec des <h2> et <h3> (PAS de <h1>, il est déjà dans le template)
- Paragraphes courts (3-4 lignes max)
- Listes à puces quand pertinent
- Ton : professionnel mais accessible, tutoiement
- Juridiquement correct mais vulgarisé (pas de jargon)
- NE PAS inventer de statistiques ou de jurisprudences précises

SECTIONS OBLIGATOIRES (dans cet ordre) :
1. Introduction (2-3 paragraphes, poser le contexte, rassurer)
2. Procédure de contestation (étapes concrètes)
3. Délais à respecter (45 jours, majorée, etc.)
4. Documents nécessaires
5. Erreurs courantes à éviter
6. FAQ (3-5 questions en <h3> avec réponses)
7. Section CTA NoRadar (paragraphe final qui mentionne NoRadar comme solution : 34€, 60 secondes, Telegram, remboursé si échec)

FORMAT DE SORTIE : JSON strict
{{
    "content_html": "<h2>...</h2><p>...</p>...",
    "faq": [
        {{"question": "...", "answer": "..."}},
        {{"question": "...", "answer": "..."}}
    ]
}}

Le content_html doit contenir TOUT le contenu y compris la FAQ (les questions FAQ dans le HTML + séparément dans le champ faq pour le schema JSON-LD).
Utilise des balises HTML sémantiques : <h2>, <h3>, <p>, <ul>, <li>, <strong>, <em>.
PAS de classes CSS, PAS de style inline dans le contenu."""

ARTICLE_PROMPT = """Tu es un expert SEO et rédacteur juridique vulgarisateur.
Génère le CONTENU HTML (uniquement le contenu à l'intérieur du <main>) pour un article SEO longue traîne.

SUJET : {title}
MOT-CLÉ PRINCIPAL : {keyword}

RÈGLES DE CONTENU — NE JAMAIS VIOLER :
1. Tu éduques sur le PROBLÈME, tu ne donnes JAMAIS la SOLUTION concrète
2. Tu expliques que contester est un DROIT et que c'est POSSIBLE — mais tu ne dis jamais COMMENT rédiger une contestation
3. INTERDIT de fournir : modèle de lettre, motifs juridiques précis, articles de loi exploitables, stratégie de contestation, exemple de requête en exonération
4. Tu peux mentionner que des motifs existent (vice de forme, erreur de procédure, etc.) SANS les détailler
5. Chaque section doit naturellement pousser le lecteur vers NoRadar comme solution : "C'est possible, mais c'est technique → NoRadar le fait pour toi"
6. Le ton est : expert accessible qui montre qu'il maîtrise le sujet SANS révéler ses secrets
7. Les informations publiques sont OK : délais, montants, marges techniques, droits généraux du conducteur
8. Termine TOUJOURS par un CTA fort vers NoRadar

L'OBJECTIF de chaque page est de convaincre le lecteur que :
- Son amende est probablement contestable
- La procédure est trop complexe pour être faite seul
- NoRadar est la solution la plus simple et la moins chère

RÈGLES :
- 800-1200 mots
- Structuré avec des <h2> et <h3>
- Répondre DIRECTEMENT à la question dès l'introduction
- Ton : professionnel mais accessible, tutoiement
- Juridiquement correct mais vulgarisé
- NE PAS inventer de statistiques ou de jurisprudences précises

SECTIONS OBLIGATOIRES :
1. Introduction (réponse directe en 2-3 phrases + développement)
2. Détails pratiques (procédure, cas concrets)
3. Ce qu'il faut savoir (pièges, délais, astuces)
4. FAQ (2-3 questions en <h3> avec réponses)
5. Section CTA NoRadar (34€, 60 secondes, Telegram, remboursé si échec)

FORMAT DE SORTIE : JSON strict
{{
    "content_html": "<h2>...</h2><p>...</p>...",
    "faq": [
        {{"question": "...", "answer": "..."}},
        {{"question": "...", "answer": "..."}}
    ]
}}

Utilise des balises HTML sémantiques : <h2>, <h3>, <p>, <ul>, <li>, <strong>, <em>.
PAS de classes CSS, PAS de style inline dans le contenu."""


# ═══════════════════════════════════════════════════════════════
# TEMPLATE HTML
# ═══════════════════════════════════════════════════════════════

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | NoRadar</title>
    <meta name="description" content="{meta_description}">
    <link rel="canonical" href="https://noradar.app/{slug}">

    <!-- OpenGraph -->
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{meta_description}">
    <meta property="og:url" content="https://noradar.app/{slug}">
    <meta property="og:type" content="article">
    <meta property="og:site_name" content="NoRadar">
    <meta property="og:image" content="https://noradar.app/og-image.png">
    <meta property="og:locale" content="fr_FR">

    <!-- Twitter -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{meta_description}">

    <!-- Schema.org FAQ -->
    {schema_faq}

    <style>
        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #1f2937;
            background: #ffffff;
            line-height: 1.7;
            font-size: 17px;
        }}
        a {{ color: #10B981; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}

        /* Header */
        .site-header {{
            background: #111827;
            padding: 16px 0;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        .header-inner {{
            max-width: 960px;
            margin: 0 auto;
            padding: 0 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .logo {{
            font-size: 22px;
            font-weight: 800;
            color: #10B981;
            letter-spacing: -0.5px;
        }}
        .logo span {{ color: #ffffff; }}
        .header-nav a {{
            color: #d1d5db;
            margin-left: 24px;
            font-size: 14px;
            font-weight: 500;
        }}
        .header-nav a:hover {{ color: #10B981; text-decoration: none; }}

        /* Hero */
        .hero {{
            background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
            padding: 60px 20px 48px;
            text-align: center;
        }}
        .hero h1 {{
            color: #ffffff;
            font-size: clamp(26px, 5vw, 38px);
            font-weight: 800;
            max-width: 720px;
            margin: 0 auto 16px;
            line-height: 1.2;
        }}
        .hero .subtitle {{
            color: #9ca3af;
            font-size: 16px;
            max-width: 560px;
            margin: 0 auto;
        }}

        /* Content */
        .content {{
            max-width: 720px;
            margin: 0 auto;
            padding: 48px 20px 80px;
        }}
        .content h2 {{
            font-size: 24px;
            font-weight: 700;
            color: #111827;
            margin: 40px 0 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid #10B981;
        }}
        .content h3 {{
            font-size: 19px;
            font-weight: 600;
            color: #374151;
            margin: 28px 0 12px;
        }}
        .content p {{
            margin-bottom: 16px;
            color: #374151;
        }}
        .content ul, .content ol {{
            margin: 0 0 16px 24px;
            color: #374151;
        }}
        .content li {{
            margin-bottom: 8px;
        }}
        .content strong {{
            color: #111827;
        }}

        /* CTA box */
        .cta-box {{
            background: linear-gradient(135deg, #10B981 0%, #059669 100%);
            border-radius: 12px;
            padding: 32px;
            margin: 48px 0 0;
            text-align: center;
            color: #ffffff;
        }}
        .cta-box h2 {{
            color: #ffffff;
            border: none;
            font-size: 22px;
            margin: 0 0 12px;
            padding: 0;
        }}
        .cta-box p {{
            color: rgba(255,255,255,0.9);
            margin-bottom: 20px;
            font-size: 15px;
        }}
        .cta-button {{
            display: inline-block;
            background: #ffffff;
            color: #059669;
            font-weight: 700;
            font-size: 16px;
            padding: 14px 32px;
            border-radius: 8px;
            text-decoration: none;
            transition: transform 0.15s;
        }}
        .cta-button:hover {{
            transform: translateY(-2px);
            text-decoration: none;
        }}

        /* Internal links */
        .related {{
            margin: 48px 0;
            padding: 24px;
            background: #f9fafb;
            border-radius: 8px;
        }}
        .related h2 {{
            font-size: 18px;
            border: none;
            margin: 0 0 12px;
            padding: 0;
        }}
        .related ul {{ list-style: none; margin: 0; padding: 0; }}
        .related li {{ margin-bottom: 8px; }}
        .related a {{ font-weight: 500; }}

        /* Footer */
        .site-footer {{
            background: #111827;
            color: #9ca3af;
            padding: 40px 20px;
            text-align: center;
            font-size: 14px;
        }}
        .site-footer a {{ color: #10B981; }}
        .footer-links {{ margin-bottom: 16px; }}
        .footer-links a {{ margin: 0 12px; }}

        /* Sticky CTA mobile */
        .sticky-cta {{
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #059669;
            padding: 12px 20px;
            text-align: center;
            z-index: 99;
            box-shadow: 0 -2px 10px rgba(0,0,0,0.15);
        }}
        .sticky-cta a {{
            color: #ffffff;
            font-weight: 700;
            font-size: 15px;
        }}
        .sticky-cta a:hover {{ text-decoration: none; }}

        /* Breadcrumb */
        .breadcrumb {{
            max-width: 720px;
            margin: 0 auto;
            padding: 16px 20px 0;
            font-size: 13px;
            color: #9ca3af;
        }}
        .breadcrumb a {{ color: #6b7280; }}
    </style>
</head>
<body>
    <header class="site-header">
        <div class="header-inner">
            <a href="https://noradar.app" class="logo">No<span>Radar</span></a>
            <nav class="header-nav">
                <a href="https://noradar.app/contester-amende-radar">Guide</a>
                <a href="https://t.me/noradar_bot">Telegram</a>
            </nav>
        </div>
    </header>

    <section class="hero">
        <h1>{title}</h1>
        <p class="subtitle">{meta_description}</p>
    </section>

    <div class="breadcrumb">
        <a href="https://noradar.app">NoRadar</a> &rsaquo; {breadcrumb_label}
    </div>

    <main class="content">
        {content}

        <div class="cta-box">
            <h2>Contestez votre amende en 60 secondes</h2>
            <p>Envoyez la photo de votre PV sur Telegram. L'IA fait le reste. 34&nbsp;&euro; &mdash; rembours&eacute; si &ccedil;a ne marche pas.</p>
            <a href="https://t.me/noradar_bot" class="cta-button">Contester mon amende</a>
        </div>

        <div class="related">
            <h2>Articles connexes</h2>
            <ul>
                {internal_links}
            </ul>
        </div>
    </main>

    <footer class="site-footer">
        <div class="footer-links">
            <a href="https://noradar.app">Accueil</a>
            <a href="https://noradar.app/contester-amende-radar">Guide contestation</a>
            <a href="https://t.me/noradar_bot">Telegram</a>
        </div>
        <p>&copy; 2025 NoRadar &mdash; Con&ccedil;u par des avocats. Ex&eacute;cut&eacute; par une IA.</p>
    </footer>

    <div class="sticky-cta">
        <a href="https://t.me/noradar_bot">Contestez votre amende &mdash; 34&nbsp;&euro; tout compris &rarr;</a>
    </div>
</body>
</html>"""


class SEOPageGenerator:
    """Génère des pages HTML SEO via Gemini."""

    def __init__(self):
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY non configurée dans .env")
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)

    @with_retry(exceptions=(ResourceExhausted, ServiceUnavailable, DeadlineExceeded))
    def _call_gemini(self, prompt: str) -> str:
        response = self.model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=4096,
                temperature=0.4,
            ),
        )
        return response.text.strip()

    def generate_pillar_page(self, page_data: dict) -> str:
        """Génère une page pilier complète."""
        console.print(f"[blue]SEO pilier : {page_data['slug']}...[/blue]")

        prompt = PILLAR_PROMPT.format(
            title=page_data["title"],
            keyword=page_data["keyword"],
        )
        raw = self._call_gemini(prompt)
        data = self._parse_json(raw)

        return self._wrap_html(
            content=data["content_html"],
            faq=data.get("faq", []),
            title=page_data["title"],
            meta=page_data["meta"],
            slug=page_data["slug"],
            is_pillar=True,
        )

    def generate_article(self, article_data: dict) -> str:
        """Génère un article longue traîne."""
        console.print(f"[blue]SEO article : {article_data['slug']}...[/blue]")

        meta = article_data.get(
            "meta",
            f"{article_data['title']}. Guide complet et conseils pratiques. Contestez avec NoRadar pour 34\u202f\u20ac.",
        )

        prompt = ARTICLE_PROMPT.format(
            title=article_data["title"],
            keyword=article_data["keyword"],
        )
        raw = self._call_gemini(prompt)
        data = self._parse_json(raw)

        return self._wrap_html(
            content=data["content_html"],
            faq=data.get("faq", []),
            title=article_data["title"],
            meta=meta,
            slug=f"blog/{article_data['slug']}",
            is_pillar=False,
        )

    def _parse_json(self, raw: str) -> dict:
        """Parse la réponse JSON de Gemini."""
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        return json.loads(text)

    def _wrap_html(
        self,
        content: str,
        faq: list[dict],
        title: str,
        meta: str,
        slug: str,
        is_pillar: bool,
    ) -> str:
        """Enveloppe le contenu dans le template HTML complet."""
        # Schema.org FAQ JSON-LD
        schema_faq = ""
        if faq:
            faq_entities = []
            for item in faq:
                faq_entities.append({
                    "@type": "Question",
                    "name": item["question"],
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": item["answer"],
                    },
                })
            schema = {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": faq_entities,
            }
            schema_faq = (
                '<script type="application/ld+json">'
                + json.dumps(schema, ensure_ascii=False)
                + "</script>"
            )

        # Liens internes (exclure la page courante)
        link_items = []
        bare_slug = slug.replace("blog/", "")
        for link_slug, link_label in INTERNAL_LINKS.items():
            if link_slug != bare_slug:
                link_items.append(
                    f'<li><a href="https://noradar.app/{link_slug}">{link_label}</a></li>'
                )
        internal_links_html = "\n                ".join(link_items)

        breadcrumb_label = "Guide" if is_pillar else "Blog"

        return HTML_TEMPLATE.format(
            title=title,
            meta_description=meta,
            slug=slug,
            schema_faq=schema_faq,
            content=content,
            internal_links=internal_links_html,
            breadcrumb_label=breadcrumb_label,
        )
