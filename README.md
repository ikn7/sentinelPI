# SentinelPi

**Station de veille multi-sources autonome pour Raspberry Pi**

SentinelPi collecte, filtre, score et vous alerte automatiquement sur les contenus les plus pertinents provenant de multiples sources (RSS, sites web, Reddit, Mastodon, YouTube).

## Fonctionnalités

- **Agrégation multi-sources** : RSS, sites web, Reddit, Mastodon, YouTube, APIs custom
- **Filtrage intelligent** : mots-clés, expressions régulières, règles composées
- **Scoring de pertinence** : score 0-100 pour prioriser les contenus
- **Apprentissage automatique** : le système apprend de vos actions
- **Alertes temps réel** : Telegram, email, webhooks
- **Dashboard web** : interface Streamlit moderne
- **Déploiement simple** : paquet Debian + service systemd

## Installation rapide

### Via le paquet Debian (recommandé)

```bash
# Télécharger le paquet
wget https://github.com/sentinelpi/sentinelpi/releases/latest/download/sentinelpi.deb

# Installer
sudo dpkg -i sentinelpi.deb

# Configurer
sudo nano /etc/sentinelpi/.env

# Démarrer
sudo systemctl enable --now sentinelpi
sudo systemctl enable --now sentinelpi-dashboard
```

### Depuis les sources

```bash
git clone https://github.com/sentinelpi/sentinelpi.git
cd sentinelpi
python3 -m venv venv
source venv/bin/activate
pip install -e .
cp .env.example .env
sentinelpi
```

## Configuration

### Sources (`config/sources.yaml`)

```yaml
sources:
  - name: "Le Monde - Tech"
    type: rss
    url: "https://www.lemonde.fr/tech/rss_full.xml"
    category: "presse"
    interval_minutes: 30
```

### Filtres (`config/filters.yaml`)

```yaml
filters:
  - name: "Alertes IA"
    action: alert
    action_params:
      severity: notice
    score_modifier: 50
    conditions:
      type: keywords
      field: all
      value: ["intelligence artificielle", "ChatGPT", "LLM"]
```

### Alertes Telegram (`.env`)

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHI...
TELEGRAM_CHAT_ID=123456789
```

## Utilisation

### Ligne de commande

```bash
# Lancer la collecte
sentinelpi

# Lancer le dashboard
sentinelpi-dashboard
```

### Service systemd

```bash
# Démarrer
sudo systemctl start sentinelpi

# Statut
sudo systemctl status sentinelpi

# Logs
journalctl -u sentinelpi -f
```

### Dashboard web

Accédez à **http://localhost:8501** pour :
- Consulter et filtrer le flux d'actualités
- Gérer les sources et les filtres
- Voir les alertes et statistiques
- Configurer le système

## Documentation complète

| Guide | Description |
|-------|-------------|
| [Installation](docs/INSTALLATION.md) | Installation détaillée |
| [Démarrage rapide](docs/QUICKSTART.md) | Premiers pas en 5 minutes |
| [Sources](docs/SOURCES.md) | Configuration des sources |
| [Filtres](docs/FILTERS.md) | Création de règles de filtrage |
| [Alertes](docs/ALERTS.md) | Configuration des notifications |
| [Scoring](docs/SCORING.md) | Comprendre les scores |
| [Apprentissage](docs/LEARNING.md) | Système d'apprentissage IA |
| [Dépannage](docs/TROUBLESHOOTING.md) | Problèmes courants |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Collecteurs    →    Processeurs    →    Stockage    →    UI   │
│  (RSS, Web...)       (Dedup, Score)      (SQLite)       (Web)  │
│                                                                 │
│  Scheduler (APScheduler)    ←→    Alerting (Telegram, Email)   │
└─────────────────────────────────────────────────────────────────┘
```

## Structure du projet

```
sentinelpi/
├── config/          # Fichiers de configuration YAML
├── src/             # Code source
│   ├── collectors/  # Collecteurs par type de source
│   ├── processors/  # Traitement (dédup, filtrage, scoring)
│   ├── storage/     # Base de données SQLite
│   ├── alerting/    # Notifications
│   ├── dashboard/   # Interface Streamlit
│   └── scheduler/   # Planificateur de tâches
├── data/            # Données (DB, cache)
├── logs/            # Fichiers de log
├── docs/            # Documentation
└── debian/          # Fichiers de packaging Debian
```

## Développement

```bash
pip install -e ".[dev]"
pytest
ruff check src/
mypy src/
```

## Licence

MIT

---

**Besoin d'aide ?** Consultez la [documentation](docs/README.md) ou ouvrez une [issue](https://github.com/sentinelpi/sentinelpi/issues).
