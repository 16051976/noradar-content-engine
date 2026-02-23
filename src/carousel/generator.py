"""
Générateur de carrousels avec Google Gemini API.
Produit le contenu (slides) pour chaque format de carrousel noradar.
"""

import json
import random
from typing import Optional

import anthropic
from rich.console import Console

from src.config import settings
from src.models import Carousel, CarouselFormat, CarouselSlide

console = Console()


# ══════════════════════════════════════════════════════
# SYSTEM PROMPT (contexte noradar pour les carrousels)
# ══════════════════════════════════════════════════════

CAROUSEL_SYSTEM_PROMPT = """Tu es un expert en copywriting viral pour les réseaux sociaux français.
Tu crées des CARROUSELS (slides swipables) sur le thème des amendes routières pour noradar.

CONTEXTE NORADAR :
- IA juridique de contestation d'amendes, conçue par des avocats spécialisés
- Prix : 34€ (ce prix bas est possible parce que tout est automatisé)
- Garantie : 100% remboursé si la contestation échoue
- Process : envoie la photo de ton PV sur Telegram, l'IA fait le reste en 60 secondes
- Gimmick signature : "Conçu par des avocats. Exécuté par une IA."

═══════════════════════════════════════════════════════════════
TYPES D'AMENDES COUVERTES (radars automatiques uniquement) :
═══════════════════════════════════════════════════════════════
Excès de vitesse (radar fixe, mobile, tronçon)
Feu rouge grillé
Ceinture non attachée
Téléphone au volant
Franchissement de ligne continue

═══════════════════════════════════════════════════════════════
RÈGLES ABSOLUES — NE JAMAIS MENTIONNER :
═══════════════════════════════════════════════════════════════
- La méthode juridique utilisée (aucun article de loi, pas de L.121-3)
- Comment fonctionne la contestation techniquement
- Les motifs de contestation (vice de procédure, anomalie, etc.)
- Toute information qui permettrait de contester sans noradar
- Les mots "équipe", "manuel", "on s'occupe", "nous analysons"
- La conclusion doit TOUJOURS être POSITIVE

═══════════════════════════════════════════════════════════════
RÈGLES DE SLIDES :
═══════════════════════════════════════════════════════════════
- 8 slides par carrousel
- Slide 1 = HOOK : UNIQUEMENT un titre percutant de 6-10 mots (majuscule uniquement en début de phrase). PAS de body text (body vide ""). Le titre DOIT contenir un CHIFFRE ou un RÉSULTAT concret. PAS de titre générique.
- Slides 2-7 = CONTENU : title = 5-8 mots (majuscule uniquement en début de phrase). body = MAX 15 MOTS (pas plus !). Court et percutant.
- Slide 8 = CTA : title = question directe (majuscule uniquement en début de phrase). body = "Lien en bio → noradar.app | 34€, remboursé si ça rate"
- TUTOIEMENT : "tu" / "ton", jamais "vous"
- EMOJIS : un emoji pertinent par slide (champ "icon")

EXEMPLES DE BONS HOOKS (slide 1 — title uniquement, body VIDE) :
❌ "Vrai ou Faux ?" (trop vague, pas de chiffre)
❌ "Teste tes connaissances" (ennuyeux)
❌ "Les mythes sur les amendes" (descriptif, pas accrocheur)
✅ "87% des conducteurs se trompent là-dessus"
✅ "Ces 5 erreurs te coûtent tes points"
✅ "135€ d'amende ? Attends 2 minutes."
✅ "Tu paies des amendes pour rien."
✅ "J'ai économisé 375€ en 60 secondes"

EXEMPLES DE BON BODY TEXT (slides 2-7 — MAX 15 MOTS) :
❌ "Détrompe-toi ! noradar te permet de contester pour 34€, et on te rembourse si ça ne marche pas." (28 mots = TROP LONG)
✅ "34€ avec noradar. Remboursé si ça rate." (7 mots = PARFAIT)
❌ "C'est exact ! Agis vite après avoir reçu ta contravention pour maximiser tes chances de succès." (15 mots = LIMITE)
✅ "Agis vite. Chaque jour compte." (5 mots = PARFAIT)

═══════════════════════════════════════════════════════════════
FORMAT DE SORTIE (JSON strict) :
═══════════════════════════════════════════════════════════════
{
    "slides": [
        {
            "icon": "emoji",
            "title": "Titre de la slide",
            "body": "Texte explicatif court",
            "label": "LABEL OPTIONNEL (ex: VRAI, FAUX, ÉTAPE 1)",
            "label_color": "green ou red (optionnel)"
        }
    ]
}

IMPORTANT :
- La PREMIÈRE slide est le HOOK (titre CHIFFRÉ, majuscule uniquement en début de phrase, body VIDE "")
- La DERNIÈRE slide est le CTA (incitation + "noradar.app")
- Chaque slide intermédiaire = UNE idée, body MAX 15 MOTS
- TOTAL : 8 slides exactement
- Le JSON doit être valide et parsable
"""


# ══════════════════════════════════════════════════════
# PROMPTS PAR FORMAT DE CARROUSEL
# ══════════════════════════════════════════════════════

CAROUSEL_FORMAT_PROMPTS = {
    CarouselFormat.MYTHE_VS_FAIT: """FORMAT : MYTHE VS FAIT
Objectif : Casser des idées reçues sur les amendes / contestation.

STRUCTURE (8 slides) :
- Slide 1 (HOOK) : Hook CHIFFRÉ sans body (body vide ""). Exemples :
  "87% des conducteurs croient ça à tort"
  "Ces 5 mythes te coûtent des points"
  "Tu crois connaître tes droits ? Vérifie."
- Slides 2-7 (CONTENU) : Chaque slide = une affirmation courante
  → title = l'affirmation (ex: "Contester, ça sert à rien")
  → body = la vérité courte
  → label = "FAUX" ou "VRAI" selon le cas
  → label_color = "red" si FAUX, "green" si VRAI
  → icon = emoji pertinent
- Slide 8 (CTA) : Incitation à tester noradar

EXEMPLES D'AFFIRMATIONS :
- "Contester une amende, c'est réservé aux riches" → FAUX
- "Tu as 45 jours pour contester" → VRAI
- "Si tu contestes, tu risques de payer plus" → FAUX
- "Une IA peut générer ta contestation" → VRAI
- "Faut un avocat pour contester" → FAUX""",

    CarouselFormat.CHECKLIST: """FORMAT : CHECKLIST
Objectif : Donner une liste d'actions concrètes à suivre.

STRUCTURE (6-7 slides) :
- Slide 1 (HOOK) : Titre de la checklist + sous-titre (ex: "Reçu une amende ? Voici quoi faire")
- Slides 2-6 (CONTENU) : Chaque slide = un item de checklist
  → title = l'action à faire (impératif, ex: "Ne paie pas tout de suite")
  → body = explication courte de pourquoi
  → icon = emoji pertinent
- Dernière slide (CTA) : Synthèse + "noradar.app"

EXEMPLES DE CHECKLISTS :
- "5 réflexes quand tu reçois une amende"
- "Checklist avant de payer ton PV"
- "Les 5 erreurs à ne pas faire avec ton amende"
- "Amende radar : la marche à suivre"

TON : Utile, pratique, comme un ami qui te guide.""",

    CarouselFormat.CHIFFRE_CHOC: """FORMAT : CHIFFRE CHOC
Objectif : Impressionner avec des statistiques / chiffres marquants.

STRUCTURE (6 slides) :
- Slide 1 (HOOK) : "Les chiffres que personne ne te montre" ou similaire
- Slides 2-5 (CONTENU) : Chaque slide = un chiffre clé
  → title = le chiffre en GROS (ex: "2 milliards €", "60 sec", "34€")
  → body = contexte / explication du chiffre
  → icon = emoji pertinent
- Slide 6 (CTA) : "Et toi ?" + incitation à agir

CHIFFRES UTILISABLES :
- 34€ : coût noradar
- 60 secondes : temps de génération
- 100% : remboursé si échec
- Montants d'amendes : 90€, 135€, 375€
- Points : 1 à 6 points par infraction

RÈGLE ABSOLUE : tous les chiffres doivent concerner DIRECTEMENT NoRadar ou les amendes radar.
Chiffres autorisés uniquement : 135€ (amende), 34€ (prix NoRadar), 3 points (retrait moyen), 60s (délai contestation), 90% (taux succès), 4 conducteurs sur 5 (ne contestent pas).
INTERDIT : inventer des montants, parler d'assurance, de coûts indirects.

TON : Impact, surprise. Chaque chiffre doit faire réagir.""",

    CarouselFormat.AVANT_APRES: """FORMAT : SANS / AVEC NORADAR

Tu dois générer UNIQUEMENT un titre accrocheur pour ce carousel (champ "title" du carousel).
Exemples OBLIGATOIRES à imiter — max 6 mots, brutal, chiffre dedans :
"135€. Ou 34€. Choisis."
"Ton PV radar coûte 4x trop cher."
"J'ai contesté. J'ai gagné. 34€."
"Payer 135€ ou pas. C'est ton choix."
Le titre DOIT être court, direct, choquant. PAS de phrase longue. PAS de "Voici", "Découvre", "Je vais te montrer".

Génère UN objet JSON avec UNIQUEMENT ces champs :
{
  "title": "...",
  "slides": []
}

Ne génère PAS de slides. Juste le title.""",

    CarouselFormat.PROCESS: """FORMAT : PROCESS / ÉTAPES
Objectif : Expliquer le parcours noradar étape par étape.

STRUCTURE (6 slides) :
- Slide 1 (HOOK) : "Comment contester en 60 secondes" ou similaire
- Slides 2-5 (ÉTAPES) : Chaque slide = une étape
  → label = "ÉTAPE 1", "ÉTAPE 2", etc.
  → title = l'action (ex: "Prends ton PV en photo")
  → body = détail court
  → icon = emoji pertinent
- Slide 6 (CTA) : "C'est tout." + noradar.app

ÉTAPES NORADAR :
1. Tu reçois ton amende
2. Tu prends ton PV en photo
3. Tu l'envoies sur Telegram à noradar
4. L'IA génère ta contestation en 60 secondes
5. Tu reçois ton dossier prêt à envoyer

TON : Simple, rassurant. Montrer que c'est ultra facile.""",

    CarouselFormat.DO_DONT: """FORMAT : DO / DON'T
Objectif : Montrer les bonnes et mauvaises pratiques.

STRUCTURE (7 slides) :
- Slide 1 (HOOK) : "Amende radar : les DO et les DON'T" ou similaire
- Slides 2-4 (DON'T) : Ce qu'il ne faut PAS faire
  → label = "NE FAIS PAS", label_color = "red"
  → title = la mauvaise pratique
  → body = pourquoi c'est une erreur
  → icon = emoji d'avertissement
- Slides 5-6 (DO) : Ce qu'il FAUT faire
  → label = "FAIS", label_color = "green"
  → title = la bonne pratique
  → body = pourquoi c'est malin
  → icon = emoji positif
- Slide 7 (CTA) : "Le bon réflexe" + noradar.app

EXEMPLES :
- DON'T : Payer dans la panique → DO : Prendre le temps de vérifier
- DON'T : Ignorer le délai de 45 jours → DO : Agir vite avec noradar
- DON'T : Chercher un avocat cher → DO : Utiliser l'IA à 34€""",

    CarouselFormat.FAQ: """FORMAT : FAQ
Objectif : Répondre aux questions les plus fréquentes.

STRUCTURE (6-7 slides) :
- Slide 1 (HOOK) : "Tout ce que tu veux savoir sur la contestation d'amendes"
- Slides 2-6 (QUESTIONS) : Chaque slide = une question + réponse
  → title = la question (ex: "C'est légal ?")
  → body = la réponse courte et rassurante
  → icon = emoji pertinent
- Dernière slide (CTA) : "Encore des questions ?" + noradar.app

QUESTIONS FRÉQUENTES :
- "C'est vraiment légal ?" → Oui, c'est un droit
- "Ça marche pour toutes les amendes ?" → Amendes radar automatiques
- "Et si ça marche pas ?" → 100% remboursé
- "C'est compliqué ?" → Photo du PV sur Telegram, 60 secondes
- "Combien ça coûte ?" → 34€, tout compris
- "C'est fiable ?" → Conçu par des avocats spécialisés

TON : Rassurant, transparent. Lever tous les doutes.""",

    CarouselFormat.STORY_CAS: """FORMAT : STORY / CAS RÉEL
Objectif : Raconter une histoire de contestation (anonymisée) en plusieurs slides.

STRUCTURE (6-7 slides) :
- Slide 1 (HOOK) : Accroche narrative (ex: "Il allait payer 135€. Puis il a découvert ça.")
- Slides 2-3 (CONTEXTE) : Le problème
  → title = ce qui s'est passé
  → body = détails narratifs
  → icon = emoji
- Slides 4-5 (SOLUTION) : La découverte de noradar et l'action
  → title = le tournant
  → body = ce qu'il a fait
  → icon = emoji
- Slide 6 (RÉSULTAT) : Le dénouement positif
  → title = "Résultat ?"
  → body = amende annulée, points gardés
  → icon = emoji victoire
- Slide 7 (CTA) : "Et toi ?" + noradar.app

SCÉNARIOS :
- Excès de vitesse sur autoroute, frustration, découverte, victoire
- Feu rouge grillé de nuit, amende injuste, contestation, annulation
- Téléphone au volant, jeune conducteur, risque permis, noradar sauve la mise

TON : Narratif, suspense progressif. Le lecteur s'identifie.""",

    CarouselFormat.COUNTDOWN: """FORMAT : COUNTDOWN / TOP N
Objectif : Lister N erreurs ou faits choc qui créent de l'urgence.

STRUCTURE (7 slides) :
- Slide 1 (HOOK) : Titre accrocheur + body vide ""
  Ex: "5 erreurs qui te font payer pour rien"
  Ex: "Les 4 réflexes que 9 conducteurs sur 10 n'ont pas"
  → icon = "🔥" ou "⚠️"
- Slides 2-6 (CONTENU) : Chaque slide = une erreur numérotée
  → title = l'erreur concrète (ex: "Payer sans réfléchir")
  → body = la conséquence exacte en € ou en points (MAX 12 MOTS)
  → label = "ERREUR 1", "ERREUR 2", etc.
  → label_color = "red"
  → icon = emoji pertinent
- Slide 7 (CTA) : "Tu viens de faire une de ces erreurs ?"

TON : Provocateur, comme un ami qui te secoue.""",

    CarouselFormat.SCREENSHOT_TELEGRAM: """Tu génères exactement 4 slides pour un carousel NoRadar format "Screenshot Telegram".

RÈGLE ABSOLUE : exactement 4 slides, pas une de plus.
RÈGLE label_color : slide 1 = null, slide 2 = 'orange', slide 3 = 'green', slide 4 = null. Ces valeurs sont OBLIGATOIRES et ne peuvent pas être modifiées.

Slide 1 - label_color: null
  title: message émotionnel et court de l'user, style texto stressé, avec emoji (ex: "J'ai reçu un PV de 135€ ce matin... j'ai vraiment pas les moyens 😓 C'est contestable ?", "Encore un radar ! 135€ + 3 points, à ce rythme je perds mon permis 😤", "J'ai 45 jours pour contester mais je sais pas du tout comment faire...")
  body: réponse immédiate du bot (ex: "🚗 Amende radar ? Envoyez-moi une photo de votre PV, je m'occupe de tout.")

Slide 2 - label_color: "orange"
  title: (vide ou ignoré)
  body: (vide ou ignoré) — la slide affiche toujours le message "Dossier éligible / Garantie / 34€ / bouton Payer"

Slide 3 - label_color: "green"
  title: description du résultat (ex: "Résultat : amende annulée")
  body: détails (ex: "135€ récupérés · Points intacts · 0€ supplémentaire")

Slide 4 - CTA (générée automatiquement par le renderer)
  title: accroche (ex: "Même amende ? Fais pareil.")
  body: sous-titre (ex: "34€ · Remboursé si ça rate · Lien en bio → noradar.app")

Génère des variations réalistes selon le type d'infraction : excès vitesse, feu rouge, téléphone, stationnement, ceinture.
Formate la réponse en JSON avec une liste "slides" de 4 éléments.
""",
}


# ══════════════════════════════════════════════════════
# VARIATIONS PAR FORMAT (anti-doublon)
# ══════════════════════════════════════════════════════

CAROUSEL_ANGLE_VARIATIONS = {
    CarouselFormat.MYTHE_VS_FAIT: [
        "Angle : mythes sur le délai de contestation",
        "Angle : mythes sur le coût de la contestation",
        "Angle : mythes sur les radars automatiques",
        "Angle : mythes sur les points de permis",
        "Angle : mythes sur les droits du conducteur",
    ],
    CarouselFormat.CHECKLIST: [
        "Angle : checklist à la réception de l'amende",
        "Angle : checklist avant de payer",
        "Angle : checklist erreurs à éviter",
        "Angle : checklist pour jeune conducteur flashé",
        "Angle : checklist si tu cumules les amendes",
    ],
    CarouselFormat.CHIFFRE_CHOC: [
        "Angle : chiffres sur le business des amendes en France",
        "Angle : chiffres sur le coût pour les conducteurs",
        "Angle : chiffres sur la simplicité de noradar",
        "Angle : chiffres sur les points perdus chaque année",
        "Angle : chiffres comparatifs amende vs contestation",
    ],
    CarouselFormat.AVANT_APRES: [
        "Angle : avant/après émotionnel (stress vs sérénité)",
        "Angle : avant/après financier (payer vs économiser)",
        "Angle : avant/après temps (semaines vs 60 secondes)",
        "Angle : avant/après pour un jeune conducteur",
        "Angle : avant/après pour un conducteur récidiviste",
    ],
    CarouselFormat.PROCESS: [
        "Angle : process ultra simple en 4 étapes",
        "Angle : process comparé à la méthode classique",
        "Angle : process du point de vue du conducteur pressé",
        "Angle : process en insistant sur la rapidité",
        "Angle : process rassurant pour un novice",
    ],
    CarouselFormat.DO_DONT: [
        "Angle : erreurs classiques à la réception d'un PV",
        "Angle : do/don't pour garder ses points",
        "Angle : do/don't pour économiser de l'argent",
        "Angle : do/don't du conducteur malin",
        "Angle : do/don't en cas de première amende",
    ],
    CarouselFormat.FAQ: [
        "Angle : questions d'un sceptique",
        "Angle : questions pratiques (prix, délai, process)",
        "Angle : questions sur la légalité et la fiabilité",
        "Angle : questions d'un jeune conducteur",
        "Angle : questions les plus posées en commentaires",
    ],
    CarouselFormat.STORY_CAS: [
        "Cas : excès de vitesse autoroute, conducteur régulier",
        "Cas : feu rouge grillé de nuit, premier PV",
        "Cas : téléphone au volant, jeune conducteur permis probatoire",
        "Cas : flashé à 3 km/h au-dessus, sentiment d'injustice",
        "Cas : ceinture non attachée sur un parking",
        "Cas : conducteur qui cumule les amendes et découvre noradar",
    ],
    CarouselFormat.COUNTDOWN: [
        "Angle : erreurs à la réception d'une amende",
        "Angle : erreurs qui font perdre des points inutilement",
        "Angle : erreurs financières face à une amende",
        "Angle : réflexes que les bons conducteurs ont",
        "Angle : top 5 des erreurs du conducteur lambda",
    ],
    CarouselFormat.SCREENSHOT_TELEGRAM: [
        "Angle : excès de vitesse radar (ex: 135€, perte de points)",
        "Angle : feu rouge grillé (ex: 135€ forfaitaire)",
        "Angle : téléphone au volant (ex: 135€ + 3 points)",
        "Angle : stop non respecté (ex: 135€ + 4 points)",
        "Angle : vitesse en agglomération (ex: 68€, perte de point)",
    ],
}


# ══════════════════════════════════════════════════════
# POOL AVANT/APRÈS (données hardcodées)
# ══════════════════════════════════════════════════════

AVANT_APRES_TITLES = [
    "Tu as payé trop vite.",
    "135€ partis. Sans réfléchir.",
    "Pourquoi tu as payé ?",
    "Tu pouvais au moins tenter.",
    "Réflexe : 135€. Décision : 34€.",
]

AVANT_APRES_POOL = [
    ("-135€", "payé direct", "-34€", "au moins tenté"),
    ("-3 points", "acceptés trop vite", "0 point", "contestation possible"),
    ("payer direct", "réflexe automatique", "contester", "réflexe malin"),
    ("135€ débités", "aucune tentative", "34€ investis", "tenté au moins"),
    ("tout le monde paie", "sans réfléchir", "certains contestent", "et gagnent"),
]

CHIFFRE_CHOC_HOOKS = [
    "Flashé par un radar ? Ces chiffres te concernent.",
    "Avant de payer ton amende radar. Lis ça.",
    "Ce que ton amende radar te coûte vraiment.",
    "Tu as reçu un PV radar ? Ces chiffres vont te choquer.",
    "Amende radar : les chiffres que tu dois connaître.",
]

CHIFFRE_CHOC_POOL = [
    ("135€", "Tu as payé sans essayer.", "Automatiquement."),
    ("34€", "C'est tout ce que ça coûtait", "d'essayer."),
    ("3 points", "Perdus.", "Sans même contester."),
    ("4 sur 5", "Paient.", "Sans réfléchir."),
    ("60 secondes", "C'est le temps", "qu'il fallait."),
    ("0€", "Si ça rate.", "Tu récupères tout."),
]


# ══════════════════════════════════════════════════════
# CLASSE PRINCIPALE
# ══════════════════════════════════════════════════════

class CarouselGenerator:
    """Génère le contenu des carrousels via Gemini API."""

    def __init__(self):
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY non configurée dans .env")
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._generated_hooks: list[str] = []

    def _call_claude_api(self, system: str, user: str) -> str:
        message = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            temperature=1.0,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return message.content[0].text

    def generate(
        self,
        format: CarouselFormat,
        theme: Optional[str] = None,
    ) -> Carousel:
        """
        Génère un carrousel pour le format spécifié.

        Args:
            format: Le format de carrousel souhaité.
            theme: Thème optionnel pour orienter le contenu.

        Returns:
            Un objet Carousel avec toutes les slides.
        """
        # CHIFFRE_CHOC : pool hardcodé, pas d'appel API
        if format == CarouselFormat.CHIFFRE_CHOC:
            hook = random.choice(CHIFFRE_CHOC_HOOKS)
            pairs = random.sample(CHIFFRE_CHOC_POOL, 4)
            slides = [
                CarouselSlide(icon="", title=hook, body="", label=""),
                *[CarouselSlide(icon="", title=p[0], label=p[1], body=p[2]) for p in pairs],
                CarouselSlide(icon="", title="Et toi ?", body="Lien en bio → noradar.app | 34€, remboursé si ça rate"),
            ]
            carousel = Carousel(format=format, title=hook, slides=slides)
            self._generated_hooks.append(hook)
            console.print(
                f"[green]Carrousel CHIFFRE_CHOC généré : {hook} "
                f"({len(slides)} slides)[/green]"
            )
            return carousel

        max_attempts = 3

        for attempt in range(max_attempts):
            # Construction du prompt
            format_prompt = CAROUSEL_FORMAT_PROMPTS[format]
            user_prompt = f"{format_prompt}\n\n"

            # Angle aléatoire anti-doublon
            angles = CAROUSEL_ANGLE_VARIATIONS.get(format, [])
            chosen_angle = "default"
            if angles:
                chosen_angle = random.choice(angles)
                user_prompt += f"DIRECTION CRÉATIVE : {chosen_angle}\n\n"

            # Nonce anti-cache
            nonce = random.randint(10000, 99999)
            user_prompt += f"[Variation #{nonce}] "

            if theme:
                user_prompt += f"THÈME SPÉCIFIQUE : {theme}\n\n"

            # Anti-doublon hooks
            if self._generated_hooks:
                hooks_list = " | ".join(self._generated_hooks[-10:])
                user_prompt += (
                    f"\nATTENTION — Ces titres de HOOK ont DÉJÀ été utilisés, "
                    f"crée un titre COMPLÈTEMENT DIFFÉRENT : [{hooks_list}]\n\n"
                )

            user_prompt += (
                "Génère UN carrousel au format JSON demandé. "
                "Rappel : ne JAMAIS mentionner la méthode juridique. "
                "8 slides exactement (hook + 6 contenu + CTA). "
                "Slide 1 = hook CHIFFRÉ, body VIDE. Body slides 2-7 = MAX 15 MOTS. "
                "JSON valide uniquement."
            )

            console.print(
                f"[blue]Génération carrousel {format.value} "
                f"(angle: {chosen_angle})...[/blue]"
            )

            try:
                response_text = self._call_claude_api(CAROUSEL_SYSTEM_PROMPT, user_prompt).strip()
                if response_text.startswith("```"):
                    response_text = response_text.split("```")[1]
                    if response_text.startswith("json"):
                        response_text = response_text[4:]
                response_text = response_text.strip()

                data = json.loads(response_text)

                # Correction body AVANT_APRES si nécessaire
                raw_slides = data["slides"]
                if format == CarouselFormat.AVANT_APRES:
                    pool_filtered = [p for p in AVANT_APRES_POOL if p[0] != "-135€"]
                    pairs = random.sample(pool_filtered, 3)
                    carousel_title = random.choice(AVANT_APRES_TITLES)
                    raw_slides = [
                        {"icon": "", "title": carousel_title, "body": ""},
                        *[{"icon": "", "title": "", "body": f"{p[0]}|||{p[1]}|||{p[2]}|||{p[3]}"} for p in pairs],
                        {"icon": "", "title": "Prêt à garder tes points ?", "body": ""},
                    ]

                # Construction des slides
                slides = []
                for s in raw_slides:
                    slide = CarouselSlide(
                        icon=s.get("icon") or "",
                        title=s["title"],
                        body=s.get("body") or "",
                        label=s.get("label"),
                        label_color=s.get("label_color"),
                    )
                    slides.append(slide)

                # Validation : au moins 5 slides
                if len(slides) < 5:
                    console.print(
                        f"[yellow]Seulement {len(slides)} slides, "
                        f"tentative {attempt + 2}/{max_attempts}...[/yellow]"
                    )
                    if attempt < max_attempts - 1:
                        continue

                carousel = Carousel(format=format, title=slides[0].title if slides else format.value, slides=slides)

                # Anti-doublon : vérifier le hook
                hook_title = slides[0].title.strip().lower() if slides else ""
                if hook_title in [h.strip().lower() for h in self._generated_hooks]:
                    if attempt < max_attempts - 1:
                        console.print(
                            f"[yellow]Hook doublon, "
                            f"tentative {attempt + 2}/{max_attempts}...[/yellow]"
                        )
                        continue

                self._generated_hooks.append(slides[0].title if slides else "")
                console.print(
                    f"[green]Carrousel généré : {slides[0].title} "
                    f"({len(slides)} slides)[/green]"
                )
                return carousel

            except json.JSONDecodeError as e:
                console.print(f"[red]Erreur parsing JSON : {e}[/red]")
                console.print(f"[dim]Réponse brute : {response_text[:500]}...[/dim]")
                if attempt < max_attempts - 1:
                    console.print(
                        f"[yellow]Nouvelle tentative "
                        f"({attempt + 2}/{max_attempts})...[/yellow]"
                    )
                    continue
                raise
            except Exception as e:
                console.print(f"[red]Erreur génération : {e}[/red]")
                raise

        raise RuntimeError(
            f"Échec de génération carrousel après {max_attempts} tentatives"
        )

    def generate_batch(
        self,
        formats: dict[CarouselFormat, int],
        theme: Optional[str] = None,
    ) -> list[Carousel]:
        """
        Génère un batch de carrousels selon la distribution demandée.

        Args:
            formats: Dict {format: nombre} ex: {MYTHE_VS_FAIT: 2, FAQ: 1}
            theme: Thème optionnel pour tous les carrousels.

        Returns:
            Liste de carrousels générés.
        """
        carousels = []

        for fmt, count in formats.items():
            console.print(f"\n[bold]Génération {count}x {fmt.value}[/bold]")
            for i in range(count):
                try:
                    carousel = self.generate(fmt, theme)
                    carousels.append(carousel)
                    hook = carousel.slides[0].title if carousel.slides else "?"
                    console.print(f"  [{i + 1}/{count}] {hook}")
                except Exception as e:
                    console.print(f"  [red][{i + 1}/{count}] Échec : {e}[/red]")

        console.print(f"\n[green]Total : {len(carousels)} carrousels générés[/green]")
        return carousels

    def save_carousel(self, carousel: Carousel) -> str:
        """Sauvegarde un carrousel en JSON."""
        settings.ensure_directories()
        output_dir = settings.output_dir / "carousels"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{carousel.format.value}_{carousel.id}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(carousel.model_dump_json(indent=2))

        console.print(f"[dim]Sauvegardé : {output_path}[/dim]")
        return str(output_path)

    @staticmethod
    def load_carousel(path: str) -> Carousel:
        """Charge un carrousel depuis un fichier JSON."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Carousel(**data)
