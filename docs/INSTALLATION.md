# Installation

Guide d'installation complet de SentinelPi.

## Prérequis

### Matériel
- Raspberry Pi 4 ou 5 (recommandé)
- 2 Go de RAM minimum (4 Go recommandé)
- Carte SD 16 Go minimum (32 Go recommandé)
- Connexion réseau (Ethernet ou WiFi)

### Logiciel
- Raspberry Pi OS (Debian 11/12) ou autre distribution Linux
- Python 3.11 ou supérieur
- pip (gestionnaire de paquets Python)
- git

## Installation rapide

```bash
# 1. Cloner le repository
git clone https://github.com/sentinelpi/sentinelpi.git
cd sentinelpi

# 2. Créer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate

# 3. Installer les dépendances
pip install -e .

# 4. Copier la configuration exemple
cp .env.example .env

# 5. Lancer SentinelPi
sentinelpi
```

## Installation détaillée

### Étape 1 : Préparation du système

```bash
# Mettre à jour le système
sudo apt update && sudo apt upgrade -y

# Installer les dépendances système
sudo apt install -y python3 python3-pip python3-venv git

# Vérifier la version de Python (doit être >= 3.11)
python3 --version
```

### Étape 2 : Cloner le projet

```bash
# Cloner dans le répertoire utilisateur
cd ~
git clone https://github.com/sentinelpi/sentinelpi.git
cd sentinelpi
```

### Étape 3 : Environnement virtuel

```bash
# Créer l'environnement virtuel
python3 -m venv venv

# Activer l'environnement
source venv/bin/activate

# Vérifier que pip est à jour
pip install --upgrade pip
```

### Étape 4 : Installation des dépendances

```bash
# Installation standard
pip install -e .

# Installation avec dépendances de développement
pip install -e ".[dev]"
```

### Étape 5 : Configuration initiale

```bash
# Copier le fichier d'environnement
cp .env.example .env

# Éditer le fichier .env
nano .env
```

**Contenu minimal de `.env` :**
```bash
# Telegram (optionnel)
TELEGRAM_BOT_TOKEN=votre_token_bot
TELEGRAM_CHAT_ID=votre_chat_id

# Email (optionnel)
EMAIL_USER=votre@email.com
EMAIL_PASSWORD=mot_de_passe_application
```

### Étape 6 : Vérification

```bash
# Vérifier l'installation
sentinelpi --help

# Lancer le dashboard (dans un autre terminal)
sentinelpi-dashboard
```

## Installation en tant que service

Pour que SentinelPi démarre automatiquement au boot :

### Créer le fichier service

```bash
sudo nano /etc/systemd/system/sentinelpi.service
```

```ini
[Unit]
Description=SentinelPi Monitoring Station
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/sentinelpi
Environment="PATH=/home/pi/sentinelpi/venv/bin"
ExecStart=/home/pi/sentinelpi/venv/bin/sentinelpi
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Créer le service dashboard

```bash
sudo nano /etc/systemd/system/sentinelpi-dashboard.service
```

```ini
[Unit]
Description=SentinelPi Dashboard
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/sentinelpi
Environment="PATH=/home/pi/sentinelpi/venv/bin"
ExecStart=/home/pi/sentinelpi/venv/bin/streamlit run src/dashboard/app.py --server.port 8501 --server.address 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Activer les services

```bash
# Recharger systemd
sudo systemctl daemon-reload

# Activer au démarrage
sudo systemctl enable sentinelpi
sudo systemctl enable sentinelpi-dashboard

# Démarrer les services
sudo systemctl start sentinelpi
sudo systemctl start sentinelpi-dashboard

# Vérifier le statut
sudo systemctl status sentinelpi
sudo systemctl status sentinelpi-dashboard
```

## Configuration du pare-feu (optionnel)

Si vous souhaitez accéder au dashboard depuis d'autres machines :

```bash
# Autoriser le port 8501 (dashboard)
sudo ufw allow 8501/tcp

# Vérifier les règles
sudo ufw status
```

## Mise à jour

```bash
cd ~/sentinelpi

# Mettre à jour le code
git pull origin main

# Mettre à jour les dépendances
source venv/bin/activate
pip install -e .

# Redémarrer les services
sudo systemctl restart sentinelpi
sudo systemctl restart sentinelpi-dashboard
```

## Désinstallation

```bash
# Arrêter et désactiver les services
sudo systemctl stop sentinelpi sentinelpi-dashboard
sudo systemctl disable sentinelpi sentinelpi-dashboard

# Supprimer les fichiers service
sudo rm /etc/systemd/system/sentinelpi.service
sudo rm /etc/systemd/system/sentinelpi-dashboard.service
sudo systemctl daemon-reload

# Supprimer le projet
rm -rf ~/sentinelpi
```

## Dépannage de l'installation

### Erreur "python3-venv not found"

```bash
sudo apt install python3-venv
```

### Erreur de version Python

Si Python 3.11+ n'est pas disponible :

```bash
# Installer pyenv pour gérer les versions Python
curl https://pyenv.run | bash

# Ajouter à .bashrc
echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc

# Installer Python 3.11
pyenv install 3.11.0
pyenv global 3.11.0
```

### Erreur de mémoire lors de pip install

Sur les Raspberry Pi avec peu de RAM :

```bash
# Ajouter du swap temporairement
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Installer avec moins de parallélisme
pip install -e . --no-cache-dir
```

### Le dashboard ne s'affiche pas

```bash
# Vérifier que le port n'est pas utilisé
sudo netstat -tlnp | grep 8501

# Vérifier les logs
journalctl -u sentinelpi-dashboard -f
```

---

Voir aussi : [Configuration rapide](QUICKSTART.md) | [Dépannage](TROUBLESHOOTING.md)
