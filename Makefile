.PHONY: install dev test lint format clean help

# Variables
PYTHON := python3
PIP := pip3

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Installe le projet en mode production
	$(PIP) install -e .
	@echo "✓ Installation terminée"
	@echo "Copiez .env.example vers .env et configurez vos clés API"

dev: ## Installe le projet en mode développement
	$(PIP) install -e ".[dev]"
	@echo "✓ Installation dev terminée"

setup: install ## Configure le projet (install + init)
	cp -n .env.example .env || true
	mkdir -p credentials
	content-engine init

test: ## Lance les tests
	pytest tests/ -v

lint: ## Vérifie le code
	ruff check src/
	mypy src/

format: ## Formate le code
	black src/
	ruff check --fix src/

clean: ## Nettoie les fichiers temporaires
	rm -rf __pycache__ .pytest_cache .mypy_cache
	rm -rf outputs/scripts/* outputs/audio/* outputs/videos/* outputs/ready/*
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Nettoyage terminé"

# === Raccourcis de production ===

script: ## Génère un script (usage: make script FORMAT=scandale)
	content-engine produce --format $(FORMAT) --script-only

video: ## Produit une vidéo (usage: make video FORMAT=tuto)
	content-engine produce --format $(FORMAT)

batch: ## Produit un batch (usage: make batch COUNT=10)
	content-engine batch --count $(COUNT)

weekly: ## Produit une semaine complète (30 vidéos)
	content-engine weekly

sync: ## Synchronise vers Google Drive
	content-engine sync

status: ## Affiche le statut de production
	content-engine status

# === Défauts ===
FORMAT ?= scandale
COUNT ?= 10
