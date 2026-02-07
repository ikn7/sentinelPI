# Guide de démarrage rapide

Configurez SentinelPi en 5 minutes !

## 1. Première exécution

Après l'installation, lancez SentinelPi :

```bash
cd ~/sentinelpi
source venv/bin/activate
sentinelpi
```

Le système va :
- Créer la base de données
- Synchroniser les sources depuis `config/sources.yaml`
- Synchroniser les filtres depuis `config/filters.yaml`
- Démarrer la collecte automatique

## 2. Accéder au Dashboard

Dans un autre terminal :

```bash
cd ~/sentinelpi
source venv/bin/activate
sentinelpi-dashboard
```

Ouvrez votre navigateur à l'adresse : **http://localhost:8501**

## 3. Ajouter votre première source

### Via le Dashboard (recommandé)

1. Cliquez sur **Sources** dans le menu
2. Cliquez sur **+ Nouvelle source**
3. Remplissez :
   - **Type** : RSS
   - **Nom** : Mon blog préféré
   - **URL** : https://example.com/feed.xml
   - **Catégorie** : tech
   - **Intervalle** : 60 minutes
4. Cliquez sur **Enregistrer**

### Via le fichier YAML

Éditez `config/sources.yaml` :

```yaml
sources:
  - name: "Mon blog préféré"
    type: rss
    url: "https://example.com/feed.xml"
    category: "tech"
    interval_minutes: 60
    enabled: true
```

Redémarrez SentinelPi pour appliquer les changements.

## 4. Créer votre premier filtre

### Via le Dashboard

1. Cliquez sur **Filtres** dans le menu
2. Cliquez sur **+ Nouveau filtre**
3. Configurez :
   - **Nom** : Alerte IA
   - **Action** : alert
   - **Sévérité** : notice
   - **Type de condition** : keywords
   - **Mots-clés** : intelligence artificielle, machine learning, GPT
4. Cliquez sur **Enregistrer**

### Via le fichier YAML

Éditez `config/filters.yaml` :

```yaml
filters:
  - name: "Alerte IA"
    action: alert
    action_params:
      severity: notice
    score_modifier: 30
    conditions:
      type: keywords
      field: all
      value:
        - "intelligence artificielle"
        - "machine learning"
        - "GPT"
```

## 5. Configurer Telegram (optionnel)

### Créer un bot Telegram

1. Ouvrez Telegram et cherchez **@BotFather**
2. Envoyez `/newbot`
3. Suivez les instructions pour nommer votre bot
4. Copiez le **token** (format: `123456789:ABCdefGHI...`)

### Obtenir votre Chat ID

1. Démarrez une conversation avec votre bot
2. Envoyez un message quelconque
3. Visitez : `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Cherchez `"chat":{"id":123456789}` - c'est votre Chat ID

### Configurer SentinelPi

Éditez `.env` :

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHI...
TELEGRAM_CHAT_ID=123456789
```

Éditez `config/alerts.yaml` :

```yaml
alerting:
  channels:
    telegram:
      enabled: true
      bot_token: "${TELEGRAM_BOT_TOKEN}"
      chat_id: "${TELEGRAM_CHAT_ID}"
      min_severity: notice
```

Redémarrez SentinelPi.

## 6. Tester l'installation

### Forcer une collecte

Dans le dashboard :
1. Allez dans **Sources**
2. Cliquez sur **Tester** à côté d'une source
3. Vérifiez que des items sont collectés

### Tester une alerte

Dans le dashboard :
1. Allez dans **Alertes**
2. Déroulez **Envoyer une notification de test**
3. Sélectionnez Telegram et cliquez **Envoyer**

## 7. Comprendre le score de pertinence

Chaque article reçoit un score de 0 à 100 :

| Score | Niveau | Signification |
|-------|--------|---------------|
| 85-100 | Critique | Très pertinent - À lire en priorité |
| 70-84 | Important | Pertinent - Mérite attention |
| 50-69 | Intéressant | Correspond à vos critères |
| 30-49 | Normal | Contenu standard |
| 0-29 | Faible | Peu pertinent |

**Comment augmenter le score :**
- Créez des filtres avec des mots-clés (+10 à +100 points)
- Mettez vos sources en priorité haute (+15 points)
- Les articles récents ont un bonus fraîcheur (+20 points max)

## 8. L'apprentissage automatique

SentinelPi apprend de vos actions :

| Action | Signal | Effet |
|--------|--------|-------|
| ⭐ Star | +1.0 | Augmente le score des articles similaires |
| 📁 Archiver | +0.5 | Signal positif modéré |
| ✅ Lire | +0.3 | Signal positif léger |
| 🗑️ Supprimer | -0.8 | Diminue le score des articles similaires |
| Ignorer | -0.2 | Signal négatif léger (automatique) |

Après **20 actions**, le système commence à influencer les scores.

## Prochaines étapes

- [Configuration des sources](SOURCES.md) - Types de sources et options
- [Création de filtres avancés](FILTERS.md) - Conditions composées, regex
- [Personnalisation des alertes](ALERTS.md) - Canaux et routage
- [Comprendre le scoring](SCORING.md) - Optimiser la pertinence

---

**Besoin d'aide ?** Consultez le [Guide de dépannage](TROUBLESHOOTING.md)
