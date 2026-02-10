"""
Base de données de mots-clés SEO pour NoRadar.

3 couches :
- PILLAR_PAGES : pages piliers (haut volume, forte concurrence)
- LONG_TAIL_ARTICLES : articles longue traîne (questions spécifiques)
- INTERNAL_LINKS : maillage interne entre pages
"""

PILLAR_PAGES = [
    {
        "slug": "contester-amende-radar",
        "title": "Contester une amende radar : guide complet 2026",
        "keyword": "contester amende radar",
        "meta": "Comment contester une amende radar ? Procédure, délais, documents. Contestez en 60 secondes avec NoRadar pour 34\u202f\u20ac.",
    },
    {
        "slug": "contester-amende-stationnement",
        "title": "Contester une amende de stationnement",
        "keyword": "contester amende stationnement",
        "meta": "Comment contester une amende de stationnement ? D\u00e9marches, mod\u00e8le de lettre et recours possibles. NoRadar vous accompagne.",
    },
    {
        "slug": "contester-amende-feu-rouge",
        "title": "Contester une amende feu rouge",
        "keyword": "contester amende feu rouge",
        "meta": "Amende pour feu rouge grill\u00e9 : peut-on contester ? Proc\u00e9dure, d\u00e9lais et chances de succ\u00e8s. Contestez avec NoRadar en 60 secondes.",
    },
    {
        "slug": "delai-contestation-amende",
        "title": "D\u00e9lai pour contester une amende : tout savoir",
        "keyword": "d\u00e9lai contestation amende",
        "meta": "Quel est le d\u00e9lai pour contester une amende ? 45 jours, amende major\u00e9e, exceptions. Tout ce qu\u2019il faut savoir avant qu\u2019il soit trop tard.",
    },
    {
        "slug": "modele-lettre-contestation-amende",
        "title": "Mod\u00e8le de lettre de contestation d\u2019amende",
        "keyword": "lettre contestation amende mod\u00e8le",
        "meta": "Mod\u00e8le gratuit de lettre pour contester une amende radar. T\u00e9l\u00e9chargez ou g\u00e9n\u00e9rez votre contestation en 60 secondes avec NoRadar.",
    },
    {
        "slug": "comment-contester-pv",
        "title": "Comment contester un PV ? Guide \u00e9tape par \u00e9tape",
        "keyword": "contester un PV",
        "meta": "Comment contester un PV ? Guide complet : d\u00e9lais, proc\u00e9dure ANTAI, documents. Ou contestez automatiquement avec NoRadar pour 34\u202f\u20ac.",
    },
]

LONG_TAIL_ARTICLES = [
    {
        "slug": "contester-amende-pas-conducteur",
        "title": "Contester une amende si on n\u2019\u00e9tait pas le conducteur",
        "keyword": "amende pas conducteur",
    },
    {
        "slug": "contester-amende-radar-mal-flashe",
        "title": "Contester une amende radar mal flash\u00e9",
        "keyword": "radar mal flash\u00e9 contestation",
    },
    {
        "slug": "documents-contestation-amende",
        "title": "Quels documents joindre \u00e0 une contestation d\u2019amende ?",
        "keyword": "documents contestation amende",
    },
    {
        "slug": "erreurs-contestation-amende",
        "title": "5 erreurs qui rendent une contestation invalide",
        "keyword": "erreurs contestation amende",
    },
    {
        "slug": "amende-recue-apres-1-an",
        "title": "Amende re\u00e7ue apr\u00e8s 1 an : est-elle valable ?",
        "keyword": "amende re\u00e7ue apr\u00e8s 1 an",
    },
    {
        "slug": "contester-amende-sans-avocat",
        "title": "Contester une amende sans avocat : c\u2019est possible",
        "keyword": "contester amende sans avocat",
    },
    {
        "slug": "amende-sans-photo-radar",
        "title": "Amende sans photo radar : peut-on contester ?",
        "keyword": "amende sans photo radar",
    },
    {
        "slug": "erreur-plaque-immatriculation-amende",
        "title": "Erreur de plaque sur une amende : comment prouver ?",
        "keyword": "erreur plaque amende",
    },
    {
        "slug": "radar-mobile-contestation",
        "title": "Radar mobile : comment contester ?",
        "keyword": "radar mobile contestation",
    },
    {
        "slug": "amende-voiture-pretee",
        "title": "Amende sur voiture pr\u00eat\u00e9e : qui paie ?",
        "keyword": "amende voiture pr\u00eat\u00e9e",
    },
    {
        "slug": "contester-amende-peage",
        "title": "Contester une amende de p\u00e9age",
        "keyword": "contester amende p\u00e9age",
    },
    {
        "slug": "amende-majoree-contestation",
        "title": "Amende major\u00e9e : peut-on encore contester ?",
        "keyword": "amende major\u00e9e contestation",
    },
    {
        "slug": "contester-pv-stationnement-horodateur",
        "title": "Contester un PV de stationnement horodateur",
        "keyword": "contester PV horodateur",
    },
    {
        "slug": "exces-vitesse-marge-erreur",
        "title": "Exc\u00e8s de vitesse et marge d\u2019erreur : ce qu\u2019il faut savoir",
        "keyword": "marge erreur radar exc\u00e8s vitesse",
    },
    {
        "slug": "amende-zone-30",
        "title": "Amende en zone 30 : les recours possibles",
        "keyword": "amende zone 30 contestation",
    },
    {
        "slug": "retrait-points-permis-contestation",
        "title": "Retrait de points : comment les r\u00e9cup\u00e9rer par contestation",
        "keyword": "retrait points permis contestation",
    },
    {
        "slug": "pv-electronique-contestation",
        "title": "PV \u00e9lectronique : comment le contester",
        "keyword": "PV \u00e9lectronique contestation",
    },
    {
        "slug": "amende-entreprise-non-designation",
        "title": "Amende entreprise : non-d\u00e9signation du conducteur",
        "keyword": "amende entreprise non d\u00e9signation conducteur",
    },
    {
        "slug": "contester-amende-ceinture-securite",
        "title": "Contester une amende pour non-port de ceinture",
        "keyword": "contester amende ceinture s\u00e9curit\u00e9",
    },
    {
        "slug": "flash-radar-nuit-contestation",
        "title": "Flash\u00e9 par un radar de nuit : vos recours",
        "keyword": "flash radar nuit contestation",
    },
]

# Maillage interne : chaque article lie vers ces pages piliers
INTERNAL_LINKS = {
    "contester-amende-radar": "Contester une amende radar",
    "comment-contester-pv": "Comment contester un PV",
    "delai-contestation-amende": "D\u00e9lais de contestation",
    "modele-lettre-contestation-amende": "Mod\u00e8le de lettre de contestation",
}
