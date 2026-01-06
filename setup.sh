#!/bin/bash
# ============================================
# NoRadar Content Engine - Setup Script
# ============================================

set -e

echo "🎬 NoRadar Content Engine - Installation"
echo "=========================================="
echo ""

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 non trouvé. Installez Python 3.11+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}✓ Python $PYTHON_VERSION détecté${NC}"

# Vérifier FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}⚠ FFmpeg non trouvé. Installation...${NC}"
    if command -v apt &> /dev/null; then
        sudo apt update && sudo apt install -y ffmpeg
    elif command -v brew &> /dev/null; then
        brew install ffmpeg
    else
        echo -e "${RED}❌ Impossible d'installer FFmpeg automatiquement.${NC}"
        echo "Installez-le manuellement : https://ffmpeg.org/download.html"
        exit 1
    fi
fi
echo -e "${GREEN}✓ FFmpeg installé${NC}"

# Créer l'environnement virtuel (optionnel)
if [ ! -d "venv" ]; then
    echo ""
    echo "Création de l'environnement virtuel..."
    python3 -m venv venv
    echo -e "${GREEN}✓ Environnement virtuel créé${NC}"
fi

# Activer l'environnement virtuel
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null || true

# Installer les dépendances
echo ""
echo "Installation des dépendances..."
pip install --upgrade pip
pip install -e .
echo -e "${GREEN}✓ Dépendances installées${NC}"

# Créer les dossiers
echo ""
echo "Création des dossiers..."
mkdir -p credentials
mkdir -p outputs/{scripts,audio,videos,ready,uploaded}
mkdir -p assets/{backgrounds,fonts,music}
mkdir -p temp
echo -e "${GREEN}✓ Dossiers créés${NC}"

# Copier .env.example si .env n'existe pas
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ Fichier .env créé${NC}"
else
    echo -e "${YELLOW}⚠ Fichier .env existant conservé${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✓ Installation terminée !${NC}"
echo ""
echo "Prochaines étapes :"
echo "  1. Éditez .env avec vos clés API :"
echo "     - GEMINI_API_KEY (https://aistudio.google.com)"
echo "     - GOOGLE_CLOUD_PROJECT"
echo "     - Placez service-account.json dans credentials/"
echo ""
echo "  2. Testez l'installation :"
echo "     content-engine init"
echo ""
echo "  3. Générez votre première vidéo :"
echo "     content-engine produce --format scandale --script-only"
echo ""
