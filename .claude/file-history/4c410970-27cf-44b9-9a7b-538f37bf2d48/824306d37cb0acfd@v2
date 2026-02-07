# Système de filtrage

Les filtres permettent de trier, marquer et alerter automatiquement sur les contenus collectés.

## Concept

Chaque article collecté passe par tous les filtres actifs. Un filtre peut :
- **Inclure/Exclure** des articles
- **Mettre en avant** (highlight) des articles importants
- **Ajouter des tags** automatiquement
- **Déclencher des alertes** via Telegram, email, etc.
- **Modifier le score** de pertinence

## Actions disponibles

| Action | Description | Effet sur le flux |
|--------|-------------|-------------------|
| `include` | Inclure si match | Conserve l'article |
| `exclude` | Exclure si match | Supprime l'article |
| `highlight` | Mettre en avant | Badge visuel + boost score |
| `tag` | Ajouter un tag | Tag automatique |
| `alert` | Déclencher alerte | Notification envoyée |

## Structure d'un filtre

```yaml
- name: "Nom du filtre"            # Requis - Identifiant unique
  description: "Description"        # Optionnel - Aide contextuelle
  action: alert                     # Requis - Action à effectuer
  action_params:                    # Optionnel - Paramètres de l'action
    severity: notice
  score_modifier: 30                # Optionnel - Modification du score (-100 à +100)
  priority: 10                      # Optionnel - Ordre d'exécution (1 = premier)
  enabled: true                     # Optionnel - Activer/désactiver
  conditions:                       # Requis - Conditions de déclenchement
    type: keywords
    field: all
    value: ["mot1", "mot2"]
```

---

## Types de conditions

### Keywords (mots-clés)

Recherche de mots ou expressions dans le texte.

```yaml
conditions:
  type: keywords
  field: all                    # Champ ciblé
  operator: contains            # Type de recherche
  case_sensitive: false         # Sensibilité à la casse
  value:
    - "intelligence artificielle"
    - "machine learning"
    - "GPT"
```

**Champs disponibles :**
| Champ | Description |
|-------|-------------|
| `all` | Tous les champs texte (défaut) |
| `title` | Titre uniquement |
| `content` | Contenu/résumé uniquement |
| `author` | Auteur uniquement |

**Opérateurs :**
| Opérateur | Description |
|-----------|-------------|
| `contains` | Contient le mot (défaut) |
| `starts_with` | Commence par |
| `ends_with` | Finit par |
| `equals` | Égalité exacte |

### Regex (expressions régulières)

Pour des patterns complexes.

```yaml
conditions:
  type: regex
  field: title
  operator: matches
  value: "(?i)(première|first|nouveau|new)\\s+(mondial|world|record)"
```

**Exemples de regex utiles :**

| Pattern | Description |
|---------|-------------|
| `(?i)mot` | Insensible à la casse |
| `\b\d+\s*M€\b` | Montants en millions d'euros |
| `^\\[.*\\]` | Commence par un tag [TAG] |
| `CVE-\d{4}-\d+` | Références CVE |

### Compound (conditions composées)

Combine plusieurs conditions avec AND ou OR.

```yaml
conditions:
  type: compound
  logic: and                    # and ou or
  conditions:
    - type: keywords
      field: title
      value: ["IA", "AI", "intelligence artificielle"]
    - type: keywords
      field: all
      value: ["France", "Paris", "français"]
```

**Logique :**
- `and` : Toutes les conditions doivent être vraies
- `or` : Au moins une condition doit être vraie

**Exemple complexe (nested) :**
```yaml
conditions:
  type: compound
  logic: and
  conditions:
    # Doit contenir des mots-clés IA
    - type: keywords
      field: all
      value: ["IA", "AI", "machine learning"]
    # ET soit France soit Europe
    - type: compound
      logic: or
      conditions:
        - type: keywords
          field: all
          value: ["France", "français"]
        - type: keywords
          field: all
          value: ["Europe", "européen", "UE"]
```

---

## Exemples par cas d'usage

### Alertes critiques

```yaml
- name: "Alertes critiques"
  description: "Événements nécessitant une attention immédiate"
  action: alert
  action_params:
    severity: critical
  score_modifier: 100
  priority: 1
  conditions:
    type: keywords
    field: all
    value:
      - "faillite"
      - "liquidation"
      - "data breach"
      - "fuite de données"
      - "cyberattaque"
      - "ransomware"
```

### Veille concurrentielle

```yaml
- name: "Mentions concurrents"
  description: "Détection des mentions de nos concurrents"
  action: alert
  action_params:
    severity: notice
  score_modifier: 30
  conditions:
    type: keywords
    field: all
    case_sensitive: false
    value:
      - "Concurrent A"
      - "Concurrent B"
      - "@concurrent_a"
```

### Tagging automatique

```yaml
- name: "Tag réglementation"
  description: "Identifier les contenus réglementaires"
  action: tag
  action_params:
    tag: "réglementation"
  conditions:
    type: keywords
    field: all
    value:
      - "RGPD"
      - "GDPR"
      - "CNIL"
      - "directive européenne"
      - "AI Act"
```

### Exclusion de bruit

```yaml
- name: "Exclusion publicités"
  description: "Filtrer le contenu sponsorisé"
  action: exclude
  priority: 1          # S'exécute en premier
  conditions:
    type: compound
    logic: or
    conditions:
      - type: keywords
        field: title
        value:
          - "[sponsored]"
          - "[ad]"
          - "[pub]"
      - type: regex
        field: title
        operator: matches
        value: "^\\s*\\[?(Sponsored|Pub|Ad)\\]?"
```

### Détection de montants financiers

```yaml
- name: "Montants significatifs"
  action: highlight
  score_modifier: 20
  conditions:
    type: regex
    field: all
    operator: matches
    value: "\\b\\d+(?:[,.]\\d+)?\\s*(?:millions?|milliards?|M€|M\\$|B€|B\\$)\\b"
```

### Combinaison thématique + géographique

```yaml
- name: "IA en France"
  description: "Articles sur l'IA mentionnant la France"
  action: highlight
  score_modifier: 40
  conditions:
    type: compound
    logic: and
    conditions:
      - type: keywords
        field: all
        value: ["intelligence artificielle", "IA", "AI", "machine learning", "deep learning"]
      - type: keywords
        field: all
        value: ["France", "français", "french", "Paris", "Hexagone"]
```

---

## Niveaux de sévérité (pour action: alert)

| Niveau | Emoji | Description | Usage |
|--------|-------|-------------|-------|
| `info` | ℹ️ | Information | Suivi général |
| `notice` | 📢 | À noter | Éléments intéressants |
| `warning` | ⚠️ | Attention | Requiert attention |
| `critical` | 🚨 | Critique | Action immédiate requise |

---

## Score Modifier

Le `score_modifier` ajuste le score de pertinence des articles matchés :

| Valeur | Effet |
|--------|-------|
| +100 | Article critique - top du flux |
| +50 | Très important |
| +30 | Important |
| +10 | Légèrement plus pertinent |
| 0 | Pas de modification |
| -10 | Légèrement moins pertinent |
| -50 | Peu intéressant |
| -100 | À ignorer |

---

## Priorité d'exécution

Les filtres sont exécutés par ordre de priorité (1 = premier) :

1. **Priorité 1** : Exclusions (pour ne pas traiter le bruit)
2. **Priorité 5-10** : Alertes critiques
3. **Priorité 20-50** : Highlighting et tags
4. **Priorité 100** : Filtres de faible importance

```yaml
- name: "Exclusion spam"
  priority: 1              # S'exécute en premier
  action: exclude
  # ...

- name: "Alerte importante"
  priority: 5              # S'exécute ensuite
  action: alert
  # ...
```

---

## Bonnes pratiques

### 1. Commencez simple

```yaml
# Bien - Simple et efficace
- name: "Alerte IA"
  action: alert
  conditions:
    type: keywords
    field: all
    value: ["ChatGPT", "GPT-4", "Claude"]
```

### 2. Utilisez des descriptions

```yaml
- name: "CVE critiques"
  description: "Vulnérabilités de sécurité à traiter en priorité"
  # Aide à comprendre l'intention du filtre
```

### 3. Testez vos regex

```bash
# Tester une regex en Python
python3 -c "import re; print(re.search(r'votre_regex', 'texte test'))"
```

### 4. Évitez les faux positifs

```yaml
# Problématique - "IA" peut matcher "IATA", "LIABILITIES"...
conditions:
  type: keywords
  value: ["IA"]

# Mieux - Mots complets
conditions:
  type: regex
  value: "\\bIA\\b"
```

### 5. Organisez par catégorie

Dans `config/filters.yaml`, groupez vos filtres :
- Alertes critiques (priorité 1-10)
- Veille concurrentielle (priorité 10-20)
- Tags automatiques (priorité 50)
- Exclusions (priorité 1)

---

Voir aussi : [Alertes](ALERTS.md) | [Scoring](SCORING.md) | [Sources](SOURCES.md)
