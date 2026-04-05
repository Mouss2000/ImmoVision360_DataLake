# Phase 2 - Script 04 : EXTRACTION

## Objectif

**Extraire et filtrer les données brutes** pour créer un dataset concentré sur le quartier Élysée, en sélectionnant les colonnes stratégiques alignées avec les hypothèses de recherche.

---

## Données d'Entrée

| Élément | Description |
|--------|-------------|
| **Source** | `data/raw/tabular/listings.csv` |
| **Provenance** | Inside Airbnb - Paris |
| **Format** | CSV (UTF-8) |
| **Taille** | ~90,000 annonces × ~100+ colonnes |
| **Champs clés** | `id`, `name`, `neighbourhood_cleansed`, `price`, `room_type`, `host_id`, etc. |

---

## Stratégie de Filtrage

### 1. Filtrage Géographique

**Quartier cible :** Élysée (8ème arrondissement, Paris)

```python
TARGET_NEIGHBOURHOOD = "Élysée"
NEIGHBOURHOOD_COLUMN = "neighbourhood_cleansed"  # Column used for filtering
```

**Résultat :** 2,625 annonces dans le quartier Élysée (100% des annonces Keep)

### 2. Sélection de Colonnes Stratégiques

Les 20 colonnes sélectionnées sont organisées autour de **3 hypothèses principales** :

#### **Hypothèse A : Détection des Propriétaires Professionnels (Économique)**

Ces features permettent d'identifier les propriétaires opérant comme des entreprises :

| Colonne | Type | Interprétation |
|---------|------|----------------|
| `calculated_host_listings_count` | **Integer** | Nombre d'annonces gérées par ce propriétaire |
| `property_type` | **String** | Type (Apartment, House, etc.) |
| `room_type` | **String** | Entire home vs Shared room |
| `price` | **Float** | Prix nuitée (en €) |
| `minimum_nights` | **Integer** | Durée min. de location (indicateur professionnel) |
| `availability_365` | **Integer** | Jours disponibles/an (haute valeur = professionnel) |

**Logique :** Un propriétaire professionnel a souvent :
- Plusieurs annonces (`calculated_host_listings_count` élevé)
- Prix stable et minimum_nights élevé
- Disponibilité calendaire stratégique

#### **Hypothèse B : Engagement & Réactivité du Propriétaire (Social)**

Ces features mesurent la qualité de service :

| Colonne | Type | Interprétation |
|---------|------|----------------|
| `host_response_time` | **String** | Catégorie (within_an_hour, within_a_day, etc.) |
| `host_response_rate` | **Float** | Taux de réponse (%) – Qualité relationnelle |

**Logique :** Les propriétaires actifs répondent rapidement → différenciation avec location "fantôme"

#### **Hypothèse C : Standardisation Visuelle (Vision – Phase 2)**

Analysées ultérieurement via Gemini Vision API :

| Colonne (générée) | Type | Interprétation |
|------------------|------|----------------|
| `Standardization_Score` | **Integer** | 1 = Catalog style / 0 = Personal décor |

**Logique :** Les propriétés "industrialisées" (style Airbnb standardisé) vs personnelles revèlent des stratégies commerciales différentes.

#### **Autres Colonnes Essentielles**

| Catégorie | Colonnes | Objectif |
|-----------|----------|----------|
| **Identifiants** | `id`, `name`, `host_id`, `host_name` | Traçabilité & jointure with images/texts |
| **Localisation** | `neighbourhood_cleansed`, `latitude`, `longitude` | Analyse géographique |
| **Activité** | `number_of_reviews`, `reviews_per_month`, `last_review` | Indicateurs usage/popularité |
| **Conformité** | `license` | Respect des régulations parisiennes |

---

## Données de Sortie

| Élément | Description |
|--------|-------------|
| **Fichier** | `data/processed/filtered_elysee.csv` |
| **Format** | CSV (UTF-8) |
| **Taille** | 2,625 lignes × 20 colonnes |
| **Espace disque** | ~400 KB |

### Aperçu de la Sortie

```
id         name                              host_id  price  room_type   calculated_host_listings_count
100000001  Charming Studio in Élysée        122456   250.0  Entire      12
100000002  Luxury Suite Champs-Élysées      789012   450.0  Entire      5
...
```

---

## Mappings : Hypothèses → Features

### Tableau Récapitulatif

| Hypothèse | Feature | Type | Source | Utilisation |
|-----------|---------|------|--------|-------------|
| A - Professionnel | `calculated_host_listings_count` | Integer | CSV | Détection multi-propriétés |
| A - Professionnel | `minimum_nights` | Integer | CSV | Indicateur de location longue durée |
| A - Professionnel | `availability_365` | Integer | CSV | Stratégie calendaire |
| A - Professionnel | `price` | Float | CSV | Tarification stratégique |
| A - Professionnel | `property_type`, `room_type` | String | CSV | Segmentation marché |
| B - Social | `host_response_time` | String | CSV | Engagement propriétaire |
| B - Social | `host_response_rate` | Float | CSV | Qualité service |
| C - Visuel | `Standardization_Score` | Integer | Images (.jpg) | Style esthétique (Phase 2) |
| C - Textual | `Neighborhood_Impact` | Integer | Texts (.txt) | Focus marketing quartier (Phase 2) |

---

## Exécution

```bash
cd scripts
python 04_extract.py
```

### Logs Attendus

```
2024-03-15 14:23:45 | INFO     | Validating paths...
2024-03-15 14:23:45 | INFO     | ✓ Input file found: data/raw/tabular/listings.csv
2024-03-15 14:23:45 | INFO     | Loading raw data...
2024-03-15 14:23:46 | INFO     | ✓ Loaded 90,482 listings with 106 columns
2024-03-15 14:23:46 | INFO     | Filtering for neighbourhood: 'Élysée'...
2024-03-15 14:23:46 | INFO     | ✓ Filtered to 2,625 listings in Élysée
2024-03-15 14:23:46 | INFO     | Selecting 20 strategic columns...
2024-03-15 14:23:46 | INFO     | ✓ Saved successfully: data/processed/filtered_elysee.csv
```

---

## Résultats

| Métrique | Valeur |
|----------|--------|
| **Lignes conservées** | 2,625 (100% du quartier) |
| **Colonnes source** | 106 |
| **Colonnes filtrées** | 20 |
| **Réduction colonnes** | 81.1% |
| **Temps d'exécution** | ~10 sec |

---

## Notes & Qualité des Données

1. **Prix (100% NaN)** : La colonne `price` est entièrement manquante dans les données source Inside Airbnb pour ce dataset. Ceci est documenté dans `README_DATAPROFILING.md`.

2. **Géolocalisation** : Toutes les coordonnées (latitude/longitude) sont valides.

3. **Couverture temporelle** : Data updated mars 2024.

4. **Jointures** : L'`id` permet de joindre with:
   - Images : `data/raw/images/<id>.jpg`
   - Textes : `data/raw/texts/<id>.txt`

---

## Prochaine Étape

Le fichier `filtered_elysee.csv` est le point d'entrée pour le **Script 05 (Transform)**, qui appliquera le nettoyage et générera les features IA.

Voir : `README_TRANSFORM.md`
