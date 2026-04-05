# Phase 2 - Script 05 : TRANSFORMATION

## Objectif

**Nettoyer et enrichir les données** du dataset `filtered_elysee.csv` en :
1. Appliquant des règles de nettoyage (imputation, conversions)
2. Générant des features IA via Google Gemini (Vision + NLP)
3. Produisant un dataset prêt pour le chargement en base de données

---

## Données d'Entrée

| Élément | Description |
|--------|-------------|
| **Fichier CSV** | `data/processed/filtered_elysee.csv` (2,625 lignes × 20 colonnes) |
| **Images** | `data/raw/images/<id>.jpg` (1 image par annonce) |
| **Textes** | `data/raw/texts/<id>.txt` (descriptions consolidées) |

---

## Phase 1 : Nettoyage des Données

### Règles Appliquées par Colonne

#### 1. **host_response_rate** (String % → Float)

| Étape | Description |
|-------|-------------|
| **Problème** | Format String avec `%` (ex: "95%") |
| **Nettoyage** | Supprimer "%", convertir en Float |
| **Imputation** | Valeurs NaN → médiane (100%) |
| **Résultat** | Float [0.0, 100.0] |

```python
# Avant
host_response_rate: ["95%", "100%", NaN, "85%"]
# Après
host_response_rate: [95.0, 100.0, 100.0, 85.0]  # médiane = 100
```

#### 2. **host_response_time** (Catégorique NaN)

| Étape | Description |
|-------|-------------|
| **Problème** | 11.4% de valeurs manquantes |
| **Imputation** | Remplir avec 'unknown' |
| **Résultat** | String (catégories valides) |

```python
# Avant
host_response_time: ["within_an_hour", NaN, "within_a_day"]
# Après
host_response_time: ["within_an_hour", "unknown", "within_a_day"]
```

#### 3. **calculated_host_listings_count** (Numeric NaN)

| Étape | Description |
|-------|-------------|
| **Problème** | 8.2% de valeurs manquantes |
| **Imputation** | Médiane = 2 |
| **Résultat** | Integer |

#### 4. **reviews_per_month** (Numeric NaN)

| Étape | Description |
|-------|-------------|
| **Problème** | 2.9% manquant, interprétation logique |
| **Imputation** | → 0 (nouvelle annonce = 0 reviews/mois) |
| **Résultat** | Float ≥ 0 |

#### 5. **number_of_reviews** (Numeric NaN)

| Étape | Description |
|-------|-------------|
| **Problème** | Manquant = pas d'avis |
| **Imputation** | → 0 |
| **Résultat** | Integer ≥ 0 |

#### 6. **minimum_nights** (Numeric with outliers)

| Étape | Description |
|-------|-------------|
| **Problème** | 0.3% NaN, certaines valeurs > 365 |
| **Imputation** | NaN → 1 (défaut minimum) |
| **Capping** | max(minimum_nights) = 365 jours |
| **Résultat** | Integer [1, 365] |

#### 7. **availability_365** (Numeric NaN)

| Étape | Description |
|-------|-------------|
| **Problème** | Interprétation : 0 = entièrement réservé |
| **Imputation** | NaN → 0 |
| **Résultat** | Integer [0, 365] |

#### 8. **license** (Catégorique NaN)

| Étape | Description |
|-------|-------------|
| **Problème** | 54.3% manquant (non déclarence) |
| **Imputation** | → 'Not provided' |
| **Résultat** | String |

```python
# Avant
license: ["LICENSE-2024-001", NaN, NaN, "LICENSE-2024-002"]
# Après
license: ["LICENSE-2024-001", "Not provided", "Not provided", "LICENSE-2024-002"]
```

#### 9. **last_review** (Date avec NaN significatif)

| Étape | Description |
|-------|-------------|
| **Problème** | 29.5% NaN → sens logique (jamais examiné) |
| **Traitement** | CONSERVER NULL (ne pas imputer) |
| **Résultat** | String (DATE) ou NULL |

#### 10. **price** (100% NaN)

| Étape | Description |
|-------|-------------|
| **Problème** | 100% manquant dans la source |
| **Traitement** | CONSERVER vide (documenté dans README_DATAPROFILING) |
| **Résultat** | Float (NULL) |

---

## Phase 2 : Ingénierie de Features par IA

### Feature 1 : Standardization_Score (Vision API)

**Objectif :** Classifier chaque annonce comme "professionnelle" (standardisée) ou "personnelle".

#### Logique

L'API Gemini Vision analyse les **images des propriétés** et les classe :

| Classe | Score | Interprétation |
|--------|-------|----------------|
| **Apartment Industrialisé** | 1 | Décor minimaliste, style catalogue, esthétique froide, standardisée → Propriétaire professionnel |
| **Apartment Personnel** | 0 | Mobilier hétéroclite, objets personnels, chaleureux → Owner-occupied ou petit propriétaire |
| **Autre / Erreur** | -1 | Image non pertinente, erreur API |

#### Processus

```
Pour chaque listing_id:
  1. Charger image: data/raw/images/{id}.jpg
  2. Envoyer à Gemini Vision API avec prompt
  3. Analyser réponse
  4. Stocker: Standardization_Score ∈ {-1, 0, 1}
```

#### Prompt Utilisé

```
Analyse cette image et classifie-la strictement dans l'une de ces catégories :
- 'Appartement industrialisé' (Déco minimaliste, style catalogue, standardisé, froid)
- 'Appartement personnel' (Objets de vie, livres, décoration hétéroclite, chaleureux)
- 'Autre' (Si l'image ne montre pas l'intérieur d'un logement)

Réponds uniquement par le nom de la catégorie.
```

#### Handling d'Erreurs & Rate Limiting

| Situation | Traitement |
|-----------|-----------|
| Image introuvable | Score = -1 |
| Gemini timeout/error | Retry (max 3 tentatives) |
| Rate limit API | Délai 5 sec + backoff exponentiel |
| Checkpoint perdu | Reprendre depuis checkpoint.csv |

#### Résultat Exemple

```
id          | Standardization_Score | Interprétation
------------|----------------------|--------------------------------
100000001   | 1                    | Standardisé (professionnel)
100000002   | 0                    | Personnel (petit proprio)
100000003   | 1                    | Standardisé
100000004   | -1                   | Erreur / image invalide
...
```

---

### Feature 2 : Neighborhood_Impact (NLP API)

**Objectif :** Mesurer à quel point le quartier est mis en avant dans la description textuelle.

#### Logique

L'API Gemini NLP analyse les **descriptions textes** pour évaluer le poids du quartier dans la stratégie marketing :

- **Score Élevé** : "Located in prestigious Élysée district near Champs-Élysées..." (quartier = argument clé)
- **Score Bas** : Quartier à peine mentionné (focus sur commodités intérieures)

#### Processus

```
Pour chaque listing_id:
  1. Charger description texte: data/raw/texts/{id}.txt
  2. Envoyer à Gemini NLP API
  3. Analyzer l'importance du quartier (0-10 scale)
  4. Stocker: Neighborhood_Impact ∈ [0, 10]
```

#### Prompt Utilisé

```
Analyse ce texte de description Airbnb et évalue l'importance 
du quartier dans la stratégie marketing (0-10).
0 = Quartier non mentionné
10 = Quartier est l'argument central

Réponds par un nombre seul.
```

#### Résultat Exemple

```
id          | Neighborhood_Impact | Description Marketing
------------|----------------------|----------------------------------
100000001   | 8                   | Forte valorisation du quartier
100000002   | 3                   | Quartier secondaire
100000003   | 9                   | Quartier = argument principal
...
```

---

## Phase 3 : Génération de Valeurs Aléatoires (Fallback)

**IMPORTANT POUR LA REMISE :** Conformément aux consignes, si l'intégration Gemini API n'est pas complète, les features IA sont **remplies avec des valeurs aléatoires cohérentes** :

```python
# Standardization_Score: Random {1, 0, -1}
Standardization_Score = random.choice([1, 0, 1])  # Weighted: favoriser non-error

# Neighborhood_Impact: Random Integer [0, 10]
Neighborhood_Impact = random.randint(0, 10)
```

**Raison :** Démontrer que le pipeline End-to-End fonctionne et est chargeable en base de données.

---

## Données de Sortie

| Élément | Description |
|--------|-------------|
| **Fichier CSV** | `data/processed/transformed_elysee.csv` |
| **Format** | CSV (UTF-8), Index=No |
| **Taille** | 2,625 lignes × 22 colonnes |
| **Checkpoint** | `data/processed/transform_checkpoint.csv` (sauvegarde tous les 25 lignes) |

### Colonnes de Sortie

```
Original 20 + 2 Nouvelles:

1. id
2. name
3. host_id
4. host_name
5. calculated_host_listings_count
6. host_response_time
7. host_response_rate
8. neighbourhood_cleansed
9. latitude
10. longitude
11. property_type
12. room_type
13. price
14. minimum_nights
15. availability_365
16. number_of_reviews
17. reviews_per_month
18. last_review
19. license
20. Standardization_Score        ← NEW (Vision AI)
21. Neighborhood_Impact          ← NEW (NLP AI)
```

---

## Exécution

```bash
cd scripts
python 05_transform.py
```

### Configuration

| Paramètre | Valeur | Description |
|-----------|--------|-------------|
| **GEMINI_MODEL** | gemini-2.5-flash | Modèle principal (fallback: 2.0 Flash Lite) |
| **CHECKPOINT_INTERVAL** | 25 | Sauvegarder tous les 25 listings (reprise) |
| **MAX_RETRIES** | 3 | Nb tentatives max avant -1 (error) |
| **RATE_LIMIT_DELAY** | 5 sec | Délai entre requêtes API |

### Logs Attendus

```
2024-03-15 15:45:00 | INFO     | ============================================================
2024-03-15 15:45:00 | INFO     | PHASE 1: DATA CLEANING
2024-03-15 15:45:00 | INFO     | ============================================================
2024-03-15 15:45:00 | INFO     | 
2024-03-15 15:45:00 | INFO     |   Initial dataset: 2625 rows × 20 columns
2024-03-15 15:45:01 | INFO     |   price: 2625/2625 NaN (100.0%)
2024-03-15 15:45:01 | INFO     |     → Column is 100% empty (source data issue)
2024-03-15 15:45:01 | INFO     |     → Decision: Keep column, document in README_DATAPROFILING.md
2024-03-15 15:45:01 | INFO     |   host_response_rate: 675 NaN → imputed with median (100.0)
...
2024-03-15 15:45:05 | INFO     |   ✓ Cleaning Summary: 2625 → 2625 rows (0 removed)
2024-03-15 15:45:05 | INFO     | 
2024-03-15 15:45:05 | INFO     | ============================================================
2024-03-15 15:45:05 | INFO     | PHASE 2: AI FEATURE ENGINEERING
2024-03-15 15:45:05 | INFO     | ============================================================
2024-03-15 15:45:05 | INFO     | 
2024-03-15 15:45:05 | INFO     | Initializing Gemini model...
2024-03-15 15:45:06 | INFO     | ✓ Gemini model initialized: gemini-2.5-flash
2024-03-15 15:45:06 | INFO     | 
2024-03-15 15:45:06 | INFO     | Processing listings (Standardization_Score from images)...
2024-03-15 15:45:20 | INFO     | ✓ Listing 1/2625: ID=100000001, Score=1 (Standardized)
2024-03-15 15:45:35 | INFO     | ✓ Listing 2/2625: ID=100000002, Score=0 (Personal)
...
[Processing continues with checkpoints...]
2024-03-15 17:30:00 | INFO     | 
2024-03-15 17:30:00 | INFO     | ============================================================
2024-03-15 17:30:00 | INFO     | TRANSFORMATION COMPLETE
2024-03-15 17:30:00 | INFO     | ============================================================
2024-03-15 17:30:00 | INFO     | ✓ Transformed data saved: data/processed/transformed_elysee.csv
2024-03-15 17:30:00 | INFO     | File size: 512 KB
2024-03-15 17:30:00 | INFO     | Rows: 2,625 | Columns: 22
```

---

## Impact des Transformations

| Métrique | Avant | Après | Changement |
|----------|-------|-------|-----------|
| **Lignes** | 2,625 | 2,625 | 0 (aucune suppression) |
| **Colonnes** | 20 | 22 | +2 features IA |
| **Complétude** | 74-100% par colonne | 100% | Tous NaN traité |
| **Taille fichier** | 400 KB | 512 KB | +28 % (features) |

---

## Qualité des Features IA

### Standardization_Score

| Valeur | Count | % | Interprétation |
|--------|-------|----|-|
| 1 | ~1,100 | ~42% | Standardisé (professionnel) |
| 0 | ~1,400 | ~53% | Personnel (petit proprio) |
| -1 | ~125 | ~5% | Erreur/invalid image |

*Répartition attendue (peut variér selon API performance)*

### Neighborhood_Impact

Distribution numérique [0, 10] :

```
Mean:   5.2
Std:    2.8
Min:    0
Q1:     3
Median: 5
Q3:     7
Max:    10
```

*Répartition attendue (valeurs aléatoires pour démo)*

---

## Prochaine Étape

Le fichier `transformed_elysee.csv` est maintenant prêt pour le **chargement en PostgreSQL (Script 06)**.

Voir : `README_LOAD.md`
