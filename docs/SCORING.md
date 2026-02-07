# Système de scoring

Le score de pertinence (0-100) aide à prioriser les articles les plus importants.

## Échelle de pertinence

| Score | Niveau | Couleur | Signification |
|-------|--------|---------|---------------|
| 85-100 | Critique | 🔴 | Très pertinent - À lire en priorité |
| 70-84 | Important | 🟠 | Pertinent - Mérite attention |
| 50-69 | Intéressant | 🟢 | Correspond à vos critères |
| 30-49 | Normal | 🔵 | Contenu standard |
| 0-29 | Faible | ⚪ | Peu pertinent - Bruit potentiel |

## Composantes du score

Le score est calculé à partir de plusieurs facteurs :

### 1. Score de base (50 points)

Tout article commence avec un score de base de **50 points**.

### 2. Fraîcheur (0-20 points)

Articles récents = bonus plus élevé.

| Âge | Bonus |
|-----|-------|
| < 6 heures | +18-20 |
| < 24 heures | +12-18 |
| < 48 heures | +6-12 |
| < 7 jours | +0-6 |
| > 7 jours | +0 |

### 3. Priorité source (4-15 points)

Selon la priorité de la source.

| Priorité | Bonus |
|----------|-------|
| Haute (1) | +15 |
| Normale (2) | +10 |
| Basse (3) | +4 |

### 4. Qualité du contenu (0-15 points)

| Critère | Bonus |
|---------|-------|
| Contenu long (>500 mots) | +5 |
| Image présente | +3 |
| Auteur identifié | +2 |
| Résumé disponible | +3 |
| Mots-clés extraits | +2 |

### 5. Filtres (-100 à +100 points)

Chaque filtre peut modifier le score via `score_modifier`.

```yaml
filters:
  - name: "Alerte IA"
    action: alert
    score_modifier: 50    # +50 points si match
```

### 6. Préférences apprises (-25 à +25 points)

Le système d'apprentissage ajuste le score selon vos actions.

| Action | Signal | Effet sur articles similaires |
|--------|--------|------------------------------|
| ⭐ Star | +1.0 | Boost significatif |
| 📁 Archive | +0.5 | Boost modéré |
| ✅ Lire | +0.3 | Léger boost |
| 🗑️ Supprimer | -0.8 | Pénalité significative |
| Ignorer | -0.2 | Légère pénalité |

## Calcul final

```
Score = Base(50)
      + Fraîcheur(0-20)
      + PrioritéSource(4-15)
      + QualitéContenu(0-15)
      + Filtres(-100 à +100)
      + Préférences(-25 à +25)
```

**Bornes :** Le score final est contraint entre 0 et 100.

## Optimiser les scores

### 1. Configurez les priorités sources

```yaml
sources:
  - name: "Source critique"
    priority: 1              # +15 points
  - name: "Source secondaire"
    priority: 3              # +4 points
```

### 2. Créez des filtres avec score_modifier

```yaml
filters:
  - name: "Sujets prioritaires"
    action: highlight
    score_modifier: 40
    conditions:
      type: keywords
      value: ["mots", "importants"]
```

### 3. Interagissez avec les articles

Plus vous interagissez (star, archive, supprimer), plus le système apprend vos préférences.

### 4. Excluez le bruit

```yaml
filters:
  - name: "Exclusion spam"
    action: exclude
    priority: 1
    conditions:
      type: keywords
      value: ["[sponsored]", "[ad]"]
```

## Affichage dans le Dashboard

### Flux principal

Les articles sont triés par score décroissant (par défaut).

### Détails du score

Cliquez sur **ℹ️** à côté d'un article pour voir :
- Score total et niveau
- Contribution de chaque facteur
- Filtres ayant matché

### Statistiques

Dans l'onglet **Stats**, consultez :
- Distribution des scores
- Évolution dans le temps
- Sources les mieux notées

---

Voir aussi : [Filtres](FILTERS.md) | [Apprentissage](LEARNING.md) | [Sources](SOURCES.md)
