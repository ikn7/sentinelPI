# Système d'alertes

Configuration des notifications et canaux d'alerte.

## Canaux disponibles

| Canal | Description | Configuration requise |
|-------|-------------|----------------------|
| Telegram | Messages instantanés | Bot token + Chat ID |
| Email | Notifications email | Serveur SMTP |
| Webhook | Appels HTTP | URL endpoint |
| Desktop | Notifications système | Environnement graphique |

## Configuration générale

Fichier : `config/alerts.yaml`

```yaml
alerting:
  enabled: true

  # Anti-spam
  aggregation:
    enabled: true
    window_minutes: 15
    max_alerts_per_window: 10
    send_summary: true

  # Heures silencieuses
  quiet_hours:
    enabled: false
    start: "22:00"
    end: "07:00"
    bypass_for_critical: true

  channels:
    # Configuration des canaux...
```

---

## Telegram

### Créer un bot

1. Ouvrez Telegram, cherchez **@BotFather**
2. Envoyez `/newbot`
3. Choisissez un nom et username
4. Copiez le **token** fourni

### Obtenir le Chat ID

1. Démarrez une conversation avec votre bot
2. Envoyez un message
3. Visitez : `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Trouvez `"chat":{"id":123456789}`

### Configuration

```yaml
telegram:
  enabled: true
  bot_token: "${TELEGRAM_BOT_TOKEN}"
  chat_id: "${TELEGRAM_CHAT_ID}"
  min_severity: notice
  disable_web_preview: false
  silent: false
  format: |
    🔔 *{severity_emoji} {severity}*

    📰 *{title}*

    📌 Source: {source_name}
    🕐 {published_at}

    {summary}

    🔗 [Lire l'article]({url})
```

**Variables disponibles dans le template :**
- `{severity}`, `{severity_emoji}`
- `{title}`, `{summary}`, `{url}`
- `{source_name}`, `{category}`
- `{published_at}`, `{keywords}`

---

## Email

### Configuration SMTP

```yaml
email:
  enabled: true
  smtp_host: "smtp.gmail.com"
  smtp_port: 587
  use_tls: true
  username: "${EMAIL_USER}"
  password: "${EMAIL_PASSWORD}"
  from_address: "sentinelpi@example.com"
  from_name: "SentinelPi"
  to_addresses:
    - "analyst@example.com"
    - "team@example.com"
  min_severity: warning
  subject_template: "[SentinelPi] {severity_emoji} {title}"
  include_full_content: true
```

### Gmail avec mot de passe d'application

1. Activez la validation en 2 étapes sur votre compte Google
2. Allez dans **Sécurité** > **Mots de passe des applications**
3. Créez un mot de passe pour "Mail"
4. Utilisez ce mot de passe dans `EMAIL_PASSWORD`

---

## Webhook

Pour intégrer avec Slack, Discord, ou systèmes personnalisés.

```yaml
webhook:
  enabled: true
  url: "${WEBHOOK_URL}"
  method: POST
  headers:
    Content-Type: "application/json"
    Authorization: "Bearer ${WEBHOOK_TOKEN}"
  min_severity: notice
  timeout: 30
  max_retries: 3
```

### Exemple Slack

```yaml
webhook:
  enabled: true
  url: "https://hooks.slack.com/services/T00/B00/XXX"
  method: POST
  headers:
    Content-Type: "application/json"
```

Le payload JSON envoyé contient :
```json
{
  "alert_id": "uuid",
  "severity": "notice",
  "title": "Titre de l'article",
  "summary": "Résumé...",
  "url": "https://...",
  "source_name": "Le Monde",
  "published_at": "2024-01-15T10:30:00Z"
}
```

---

## Règles de routage

Personnalisez les canaux par catégorie ou tags.

```yaml
rules:
  # Alertes presse importantes -> Telegram + Email
  - category: "presse"
    min_severity: warning
    channels: [telegram, email]

  # Alertes concurrents -> Telegram uniquement
  - category: "concurrents"
    min_severity: info
    channels: [telegram]

  # Tags urgents -> Tous les canaux
  - tags: ["critique", "urgent"]
    min_severity: info
    channels: [telegram, email, webhook]

  # Tech -> Seulement Telegram
  - category: "tech"
    min_severity: notice
    channels: [telegram]
```

---

## Niveaux de sévérité

| Niveau | Emoji | Quand l'utiliser |
|--------|-------|------------------|
| `info` | ℹ️ | Information générale, FYI |
| `notice` | 📢 | À noter, intéressant |
| `warning` | ⚠️ | Requiert attention |
| `critical` | 🚨 | Action immédiate requise |

---

## Agrégation anti-spam

Évite le flood de notifications.

```yaml
aggregation:
  enabled: true
  window_minutes: 15           # Fenêtre de temps
  max_alerts_per_window: 10    # Seuil avant agrégation
  send_summary: true           # Envoyer un résumé
```

**Comportement :**
1. Les 10 premières alertes en 15 min sont envoyées normalement
2. Au-delà, les alertes sont agrégées
3. Un résumé est envoyé à la fin de la fenêtre

---

## Heures silencieuses

Désactive les notifications la nuit.

```yaml
quiet_hours:
  enabled: true
  start: "22:00"
  end: "07:00"
  bypass_for_critical: true    # Critical passe toujours
```

---

## Tester les alertes

### Via le Dashboard

1. Allez dans **Alertes**
2. Déroulez **Envoyer une notification de test**
3. Choisissez le canal et la sévérité
4. Cliquez **Envoyer**

### Via la ligne de commande

```bash
sentinelpi test-alert --channel telegram --severity notice --message "Test"
```

---

Voir aussi : [Filtres](FILTERS.md) | [Configuration](SETTINGS.md)
