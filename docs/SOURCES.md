# Configuration des sources

SentinelPi supporte plusieurs types de sources pour la collecte de données.

## Types de sources disponibles

| Type | Description | Exemple d'utilisation |
|------|-------------|----------------------|
| `rss` | Flux RSS/Atom | Blogs, journaux, podcasts |
| `web` | Scraping de pages web | Sites sans RSS |
| `reddit` | Subreddits Reddit | Communautés techniques |
| `mastodon` | Instances Mastodon | Hashtags, comptes |
| `youtube` | Chaînes YouTube | Vidéos techniques |
| `custom` | API personnalisée | APIs propriétaires |

## Paramètres communs

Tous les types de sources partagent ces paramètres :

```yaml
- name: "Nom affiché"           # Requis - Nom dans le dashboard
  type: rss                      # Requis - Type de collecteur
  url: "https://..."             # Requis - URL de la source
  enabled: true                  # Optionnel - Activer/désactiver (défaut: true)
  category: "presse"             # Optionnel - Catégorie pour le tri
  tags: ["tech", "ia"]           # Optionnel - Tags pour le filtrage
  interval_minutes: 60           # Optionnel - Fréquence de collecte (défaut: 60)
  priority: 2                    # Optionnel - 1=haute, 2=normale, 3=basse
  config: {}                     # Optionnel - Configuration spécifique au type
```

### Priorités

| Valeur | Niveau | Bonus score |
|--------|--------|-------------|
| 1 | Haute | +15 points |
| 2 | Normale | +10 points |
| 3 | Basse | +4 points |

---

## RSS / Atom

Le type le plus courant pour les flux de syndication.

### Configuration de base

```yaml
- name: "Le Monde - Tech"
  type: rss
  url: "https://www.lemonde.fr/tech/rss_full.xml"
  category: "presse"
  interval_minutes: 30
```

### Options avancées

```yaml
- name: "Blog technique"
  type: rss
  url: "https://blog.example.com/feed.xml"
  category: "tech"
  config:
    max_items: 50              # Nombre max d'items par collecte (défaut: 100)
    include_content: true      # Inclure le contenu complet (défaut: true)
    timeout: 30                # Timeout en secondes (défaut: 30)
```

### Trouver des flux RSS

- **Chercher dans le code source** : `Ctrl+U`, chercher "rss" ou "atom"
- **Ajouter `/feed` ou `/rss`** à l'URL du site
- **Extensions navigateur** : RSS Finder, Feedbro
- **Services** : Feedly, Inoreader (pour découvrir)

---

## Web Scraping

Pour les sites web sans flux RSS.

### Configuration de base

```yaml
- name: "Actualités Concurrent"
  type: web
  url: "https://concurrent.fr/actualites"
  category: "concurrents"
  config:
    selector: "article.news-item"      # Requis - Conteneur des articles
    title_selector: "h2"               # Sélecteur du titre
    link_selector: "a"                 # Sélecteur du lien
    content_selector: ".excerpt"       # Sélecteur du résumé
```

### Options complètes

```yaml
- name: "Site complexe"
  type: web
  url: "https://example.com/news"
  config:
    # Sélecteurs CSS (obligatoire: selector)
    selector: "div.article"            # Conteneur de chaque article
    title_selector: "h2.title"         # Titre de l'article
    link_selector: "a.read-more"       # Lien vers l'article complet
    content_selector: ".summary"       # Résumé ou contenu
    date_selector: "span.date"         # Date de publication
    author_selector: ".author-name"    # Auteur
    image_selector: "img.thumbnail"    # Image principale

    # Parsing de date
    date_format: "%d/%m/%Y"            # Format strptime
    date_locale: "fr_FR"               # Locale pour les mois

    # Options avancées
    wait_for_js: false                 # Attendre l'exécution JavaScript
    scroll_to_load: false              # Scroller pour charger plus
    max_pages: 1                       # Nombre de pages à scraper
    next_page_selector: "a.next"       # Sélecteur pagination
```

### Trouver les sélecteurs CSS

1. Ouvrez la page dans le navigateur
2. Clic droit sur un élément > **Inspecter**
3. Identifiez la structure HTML
4. Construisez le sélecteur CSS

**Exemples de sélecteurs :**
- `article` - Tous les éléments `<article>`
- `.news-item` - Éléments avec classe `news-item`
- `div.content h2` - Les `<h2>` dans un `<div class="content">`
- `[data-type="article"]` - Éléments avec attribut `data-type="article"`

---

## Reddit

Collecte les posts d'un subreddit.

### Configuration de base

```yaml
- name: "r/technology"
  type: reddit
  url: "https://www.reddit.com/r/technology"
  category: "social"
  config:
    sort: "hot"        # Mode de tri
    limit: 25          # Nombre de posts
```

### Options de tri

| Valeur | Description |
|--------|-------------|
| `hot` | Populaires actuellement (défaut) |
| `new` | Plus récents |
| `top` | Meilleurs (toutes périodes) |
| `rising` | En progression |

### Options complètes

```yaml
- name: "r/MachineLearning"
  type: reddit
  url: "https://www.reddit.com/r/MachineLearning"
  config:
    sort: "new"
    limit: 50                  # Max: 100
    time_filter: "week"        # Pour "top": hour, day, week, month, year, all
    include_comments: false    # Inclure les commentaires (défaut: false)
```

---

## Mastodon

Collecte depuis une instance Mastodon (ou compatible ActivityPub).

### Suivre un hashtag

```yaml
- name: "Mastodon - #AI"
  type: mastodon
  url: "https://mastodon.social"
  config:
    type: "hashtag"
    hashtag: "artificialintelligence"   # Sans le #
    limit: 20
```

### Suivre un compte

```yaml
- name: "Compte expert IA"
  type: mastodon
  url: "https://mastodon.social"
  config:
    type: "account"
    account_id: "123456789"    # ID numérique du compte
    limit: 20
    include_replies: false     # Inclure les réponses
    include_boosts: true       # Inclure les retoots
```

### Suivre la timeline locale

```yaml
- name: "Instance locale"
  type: mastodon
  url: "https://mon-instance.social"
  config:
    type: "timeline"
    timeline: "local"          # local ou federated
    limit: 50
```

### Trouver l'ID d'un compte

1. Allez sur le profil du compte
2. L'URL sera comme : `https://mastodon.social/@user`
3. Utilisez l'API : `https://mastodon.social/api/v1/accounts/lookup?acct=user`
4. L'ID sera dans la réponse JSON

---

## YouTube

Collecte les vidéos d'une chaîne YouTube via son flux RSS.

### Configuration

```yaml
- name: "Chaîne Tech"
  type: youtube
  url: "https://www.youtube.com/feeds/videos.xml?channel_id=UC_x5XG1OV2P6uZZ5FSM9Ttw"
  category: "video"
  config:
    max_items: 20
```

### Trouver l'ID d'une chaîne

1. Allez sur la chaîne YouTube
2. Clic droit > **Afficher la source**
3. Cherchez `channel_id` ou `channelId`
4. L'ID commence par `UC`

**Format de l'URL RSS :**
```
https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID
```

---

## Custom (API personnalisée)

Pour les APIs REST ou sources non standard.

### Configuration de base

```yaml
- name: "API Interne"
  type: custom
  url: "https://api.internal.com/v1/news"
  config:
    method: "GET"
    headers:
      Authorization: "Bearer ${API_TOKEN}"
      Content-Type: "application/json"
```

### Configuration complète

```yaml
- name: "API avancée"
  type: custom
  url: "https://api.example.com/articles"
  config:
    # Requête HTTP
    method: "GET"                      # GET, POST
    headers:
      Authorization: "Bearer ${TOKEN}"
      Accept: "application/json"
    params:                            # Paramètres URL (?key=value)
      limit: 50
      category: "tech"
    body: null                         # Corps pour POST (JSON string)

    # Mapping des champs JSON
    items_path: "data.articles"        # Chemin vers la liste d'items
    title_path: "headline"             # Chemin vers le titre
    url_path: "link"                   # Chemin vers l'URL
    content_path: "body"               # Chemin vers le contenu
    date_path: "published_at"          # Chemin vers la date
    author_path: "author.name"         # Chemin vers l'auteur

    # Options
    timeout: 60
    max_items: 100
```

---

## Import OPML

Importez vos flux RSS depuis un fichier OPML (export Feedly, Inoreader, etc.).

### Via le Dashboard

1. Allez dans **Sources**
2. Cliquez sur **Importer OPML**
3. Sélectionnez votre fichier `.opml`
4. Validez les sources à importer

### Via la ligne de commande

```bash
sentinelpi import-opml fichier.opml
```

---

## Bonnes pratiques

### Intervalles de collecte

| Type de source | Intervalle recommandé |
|----------------|----------------------|
| Actualités chaudes | 15-30 minutes |
| Blogs, médias | 60 minutes |
| Réseaux sociaux | 30-60 minutes |
| Sites lents | 120-360 minutes |

### Catégorisation

Utilisez des catégories cohérentes pour filtrer efficacement :
- `presse` - Médias traditionnels
- `tech` - Blogs et sites techniques
- `social` - Réseaux sociaux
- `concurrents` - Veille concurrentielle
- `veille` - Intelligence économique

### Tags

Les tags permettent un filtrage transversal :
```yaml
tags: ["ia", "startup", "france"]
```

---

Voir aussi : [Filtres](FILTERS.md) | [Scoring](SCORING.md) | [Dépannage](TROUBLESHOOTING.md)
