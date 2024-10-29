FROM python:3.10-slim

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Définition du répertoire de travail
WORKDIR /chatbot

# Copie des fichiers de requirements et installation des dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Création du répertoire models
RUN mkdir -p app/models && chmod 777 app/models

# Copie de l'application complète
COPY app/ app/

# Commande de démarrage
CMD ["python", "-u", "app/app.py"]