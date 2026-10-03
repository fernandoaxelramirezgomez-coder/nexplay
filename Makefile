.DEFAULT_GOAL := help
SHELL := /bin/bash

# Python con el que se crea .venv (make setup PYTHON=python3.14 para elegir otro).
PYTHON   ?= python3
VENV     := .venv
PY       := $(CURDIR)/$(VENV)/bin/python
BACKEND  := backend
FRONTEND := frontend
# Puerto de make api (el frontend en desarrollo espera la API en el 8000).
PUERTO   ?= 8000
# Carpeta para make notebooks; vacía, cada corrida usa una temporal nueva.
EJECUCION ?=

DB               := $(BACKEND)/datos/nexplay.db
DB_ENTRENAMIENTO := $(BACKEND)/datos/entrenamiento/nexplay_data-v1.db
MODELO           := $(BACKEND)/modelo/nexplay.pkl

.PHONY: help setup data train api web test notebooks doc \
        _venv _datos _modelo _frontend

## help: lista los objetivos disponibles
help:
	@echo "NexPlay: objetivos disponibles (en orden, la primera vez: setup, data, train)"
	@echo ""
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/^## //' | awk '{ i = index($$0, ": "); printf "  make %-10s %s\n", substr($$0, 1, i - 1), substr($$0, i + 2) }'
	@echo ""

# --- Instalación ------------------------------------------------------------

## setup: crea .venv con lo de la API y el modelo, e instala el frontend con npm ci
setup:
	@$(PYTHON) -c 'import sys; sys.exit(sys.version_info < (3, 12))' 2>/dev/null || { \
		echo "Hace falta Python 3.12 o más nuevo y '$(PYTHON)' no lo es (o no existe)."; \
		echo "Indica otro, por ejemplo: make setup PYTHON=python3.14"; exit 1; }
	@command -v npm >/dev/null || { echo "Hace falta Node.js con npm (^22.22.3 o ^24.15.0) para el frontend."; exit 1; }
	@test -x "$(PY)" || $(PYTHON) -m venv $(VENV)
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -r $(BACKEND)/requirements.txt -r $(BACKEND)/requirements-modelo.txt
	cd $(FRONTEND) && npm ci
	@echo "Listo. Siguiente paso: make data"

# --- Datos y modelo -----------------------------------------------------------

## data: baja data-v3 (catálogo) y data-v1 (entrenamiento) a backend/datos/, verificando su sha256
data: _venv
	cd $(BACKEND) && $(PY) despliegue/preparar_entorno.py --solo-datos

## train: entrena el modelo con data-v1 y compara las 123 bandas contra la referencia
train: _datos
	cd $(BACKEND) && $(PY) modelado/entrenar_modelo.py $$($(PY) -c 'from despliegue import preparar_entorno as p; print(f"--db {p.ENTRENAMIENTO_DB_PATH.relative_to(p.RAIZ)} --tag-datos {p.ENTRENAMIENTO_REF} --sha256-asset {p.ENTRENAMIENTO_SHA256}")')
	cd $(BACKEND) && $(PY) modelado/verificar_bandas.py

# --- Desarrollo ---------------------------------------------------------------

## api: levanta la API en http://localhost:8000 (contrato en /docs), recarga al guardar
api: _modelo
	@$(PY) -c 'import socket, sys; sys.exit(socket.socket().connect_ex(("127.0.0.1", $(PUERTO))) == 0)' || { \
		echo "El puerto $(PUERTO) ya está en uso (¿otra API corriendo?). Apágala o usa otro: make api PUERTO=8001"; exit 1; }
	cd $(BACKEND) && $(PY) -m uvicorn api.main:app --reload --port $(PUERTO)

## web: levanta el frontend en http://localhost:4200 (necesita la API corriendo)
web: _frontend
	cd $(FRONTEND) && npx ng serve

# --- Calidad ------------------------------------------------------------------

## test: verificadores del backend (bandas, Nia, factores, preparar_entorno) y pruebas del frontend
test: _modelo _frontend
	cd $(BACKEND) && $(PY) modelado/verificar_bandas.py
	cd $(BACKEND) && $(PY) calidad/verificar_nia.py
	cd $(BACKEND) && $(PY) calidad/verificar_factores.py
	cd $(BACKEND) && $(PY) calidad/verificar_niveles.py
	cd $(BACKEND) && $(PY) calidad/verificar_preparar_entorno.py
	cd $(FRONTEND) && npx ng test --watch=false

## notebooks: ejecuta 00, 01 y 02 en una carpeta temporal y compara con las salidas guardadas, sin tocarlas
notebooks: _venv
	@$(PY) -c 'import torch' 2>/dev/null || $(PY) -m pip install -q torch --index-url https://download.pytorch.org/whl/cpu
	$(PY) -m pip install -q -r $(BACKEND)/requirements-notebooks.txt -r $(BACKEND)/requirements-dev.txt
	cd $(BACKEND) && $(PY) calidad/correr_notebooks.py $(if $(EJECUCION),--carpeta "$(abspath $(EJECUCION))")

# --- Documento ----------------------------------------------------------------

## doc: genera figuras y cifras, compila el documento en LaTeX y deja entregables/documento-entregafinal.pdf
doc: _venv
	@command -v latexmk >/dev/null || { \
		echo "Falta LaTeX. En Ubuntu: sudo apt install latexmk texlive-luatex texlive-latex-extra texlive-lang-spanish texlive-bibtex-extra biber texlive-pictures fonts-inter"; exit 1; }
	$(PY) -m pip install -q -r documento/requirements-documento.txt
	$(PY) documento/generar_figuras.py
	$(PY) documento/verificar_cifras.py
	cd documento && latexmk
	cp documento/build/main.pdf entregables/documento-entregafinal.pdf
	@echo "Listo: entregables/documento-entregafinal.pdf"

# --- Comprobaciones previas (no se listan en help) ----------------------------

_venv:
	@test -x "$(PY)" || { echo "Falta el entorno .venv. Corre primero: make setup"; exit 1; }

_datos: _venv
	@test -f "$(DB)" -a -f "$(DB_ENTRENAMIENTO)" || { \
		echo "Faltan las bases en $(BACKEND)/datos/ (nexplay.db y entrenamiento/nexplay_data-v1.db)."; \
		echo "Corre primero: make data"; exit 1; }

_modelo: _datos
	@test -f "$(MODELO)" || { echo "Falta el modelo $(MODELO). Corre primero: make train"; exit 1; }

_frontend:
	@test -d "$(FRONTEND)/node_modules" || { echo "Faltan las dependencias del frontend. Corre primero: make setup"; exit 1; }
