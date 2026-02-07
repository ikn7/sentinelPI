# Documentation SentinelPi

**SentinelPi** est une station de veille multi-sources autonome conçue pour le Raspberry Pi. Elle permet de collecter, filtrer, scorer et alerter automatiquement sur des contenus provenant de multiples sources (RSS, sites web, réseaux sociaux).

## Table des matières

### Guides de démarrage
- [Installation](INSTALLATION.md) - Guide d'installation complet
- [Configuration rapide](QUICKSTART.md) - Premiers pas en 5 minutes
- [Utilisation du Dashboard](DASHBOARD.md) - Guide de l'interface web

### Configuration détaillée
- [Sources](SOURCES.md) - Configuration des sources de données
- [Filtres](FILTERS.md) - Système de filtrage et règles
- [Alertes](ALERTS.md) - Notifications et canaux d'alerte
- [Paramètres généraux](SETTINGS.md) - Configuration complète

### Fonctionnalités avancées
- [Système de scoring](SCORING.md) - Comprendre les scores de pertinence
- [Apprentissage des préférences](LEARNING.md) - IA d'apprentissage automatique
- [Rapports](REPORTS.md) - Génération de rapports périodiques
- [API programmatique](API.md) - Utilisation en tant que bibliothèque

### Maintenance
- [Dépannage](TROUBLESHOOTING.md) - Problèmes courants et solutions
- [Sauvegarde et restauration](BACKUP.md) - Gestion des données
- [Mise à jour](UPDATE.md) - Procédures de mise à jour

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         SentinelPi                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │ Collecteurs │───▶│ Processeurs │───▶│ Stockage (SQLite)   │ │
│  │  - RSS      │    │  - Dedup    │    │  - Items            │ │
│  │  - Web      │    │  - Filtrage │    │  - Sources          │ │
│  │  - Reddit   │    │  - Scoring  │    │  - Alertes          │ │
│  │  - Mastodon │    │  - Enrichir │    │  - Préférences      │ │
│  │  - YouTube  │    │  - Apprendre│    └─────────────────────┘ │
│  │  - Custom   │    └─────────────┘              │             │
│  └─────────────┘                                 ▼             │
│                                        ┌─────────────────────┐ │
│  ┌─────────────┐    ┌─────────────┐    │ Dashboard Streamlit │ │
│  │  Scheduler  │───▶│  Alerting   │    │  - Flux             │ │
│  │  (APSched)  │    │  - Telegram │    │  - Sources          │ │
│  │             │    │  - Email    │    │  - Filtres          │ │
│  │             │    │  - Webhook  │    │  - Statistiques     │ │
│  └─────────────┘    │  - Desktop  │    │  - Configuration    │ │
│                     └─────────────┘    └─────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Flux de données

1. **Collecte** : Les collecteurs récupèrent les données des sources configurées
2. **Déduplication** : Élimination des doublons par hash de contenu et GUID
3. **Filtrage** : Application des règles de filtrage (inclusion, exclusion, tags, alertes)
4. **Scoring** : Calcul du score de pertinence (0-100)
5. **Enrichissement** : Extraction de mots-clés, analyse de sentiment, résumé
6. **Stockage** : Persistance en base SQLite
7. **Apprentissage** : Mise à jour des préférences basées sur les actions utilisateur
8. **Alerting** : Envoi des notifications pour les items correspondant aux règles d'alerte

## Liens utiles

- **Repository** : https://github.com/sentinelpi/sentinelpi
- **Issues** : https://github.com/sentinelpi/sentinelpi/issues
- **Licence** : MIT
