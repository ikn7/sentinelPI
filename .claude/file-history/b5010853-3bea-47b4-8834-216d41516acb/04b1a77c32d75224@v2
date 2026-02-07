# Apprentissage des préférences

SentinelPi apprend automatiquement vos préférences à partir de vos actions.

## Principe

Le système observe vos interactions avec les articles et ajuste les scores des futurs articles similaires.

```
Action utilisateur → Extraction des caractéristiques → Mise à jour des poids → Influence sur les scores futurs
```

## Signaux d'apprentissage

| Action | Signal | Interprétation |
|--------|--------|----------------|
| ⭐ Star (favori) | +1.0 | "Je veux plus de contenu comme ça" |
| 📁 Archiver | +0.5 | "C'est intéressant, je garde" |
| ✅ Marquer lu | +0.3 | "J'ai lu, ça m'intéresse un peu" |
| 🗑️ Supprimer | -0.8 | "Ce type de contenu ne m'intéresse pas" |
| Ignorer (automatique) | -0.2 | "Pas assez intéressant pour être lu" |

## Caractéristiques extraites

Pour chaque article, le système extrait :

| Type | Description | Exemple |
|------|-------------|---------|
| `keyword` | Mots-clés de l'article | "machine learning", "startup" |
| `source` | Source de l'article | "Le Monde", "TechCrunch" |
| `category` | Catégorie de la source | "tech", "presse" |
| `author` | Auteur de l'article | "John Doe" |

## Seuil d'activation

Le système nécessite **20 actions minimum** avant d'influencer les scores.

**Pourquoi ?**
- Évite les biais de démarrage à froid
- Garantit une base statistique suffisante
- Permet des recommandations fiables

**Progression :**
```
📊 Apprentissage: 13/20 actions  →  En attente
🧠 Apprentissage actif (47 actions)  →  Actif
```

## Algorithme

### Mise à jour des poids (EMA)

```python
nouveau_poids = (1 - taux) * ancien_poids + taux * signal
```

Avec un taux d'apprentissage de 0.1 par défaut.

### Décroissance temporelle

Les préférences anciennes s'estompent progressivement :

```python
poids_actuel = poids * 2^(-jours_écoulés / demi_vie)
```

Avec une demi-vie de 30 jours par défaut.

### Calcul du score de préférence

```python
score_preference = moyenne(poids_correspondants) * max_score
# Range: -25 à +25 points
```

## Configuration

Dans `config/settings.yaml` :

```yaml
learning:
  enabled: true                    # Activer l'apprentissage
  learning_rate: 0.1               # Vitesse d'apprentissage (0.0-1.0)
  decay_half_life_days: 30         # Demi-vie de décroissance
  min_actions_required: 20         # Seuil d'activation
  max_preference_score: 25.0       # Score max de préférence (±)
```

### Paramètres avancés

| Paramètre | Défaut | Description |
|-----------|--------|-------------|
| `learning_rate` | 0.1 | Plus élevé = apprentissage rapide mais volatile |
| `decay_half_life_days` | 30 | Plus élevé = préférences persistantes |
| `min_actions_required` | 20 | Plus élevé = plus fiable mais plus lent |
| `max_preference_score` | 25.0 | Impact maximum sur le score total |

## Dashboard

### Indicateur sidebar

L'indicateur en bas de la sidebar affiche :
- Nombre d'actions enregistrées
- État actif/en attente

### Section Préférences (Paramètres)

Dans **Config** > **Préférences** :

1. **Statistiques**
   - Actions totales
   - Préférences positives/négatives
   - État du système

2. **Top préférences positives**
   - Mots-clés, sources, auteurs favorisés

3. **Top préférences négatives**
   - Éléments défavorisés

4. **Réinitialisation**
   - Bouton pour effacer toutes les préférences

## Bonnes pratiques

### 1. Soyez cohérent

Utilisez les actions de manière cohérente :
- ⭐ Star uniquement pour le contenu vraiment excellent
- 🗑️ Supprimer le contenu clairement non pertinent

### 2. Donnez du contexte au système

Au début, interagissez avec différents types de contenus pour aider le système à comprendre vos préférences.

### 3. Laissez le temps au système

Après 20 actions, attendez quelques collectes pour voir l'effet sur les scores.

### 4. Réinitialisez si nécessaire

Si vos intérêts changent radicalement, utilisez le bouton de réinitialisation.

## Exemple concret

**Situation :** Vous êtes intéressé par l'IA mais pas par les crypto-monnaies.

**Actions :**
1. ⭐ Star 3 articles sur "ChatGPT", "LLM", "machine learning"
2. 🗑️ Supprimer 2 articles sur "Bitcoin", "NFT"

**Résultat après activation :**
- Articles avec mots-clés IA : +10-15 points
- Articles avec mots-clés crypto : -10-15 points

---

Voir aussi : [Scoring](SCORING.md) | [Dashboard](DASHBOARD.md)
