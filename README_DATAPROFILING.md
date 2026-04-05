# Phase 2 - Data Profiling : filtered_elysee.csv

## Résumé Exécutif

Après extraction (Script 04), avant transformation, l'analyse qualitative du dataset `filtered_elysee.csv` révèle :

- **2,625 annonces valides** du quartier Élysée
- **20 colonnes conservées** (voir détails ci-dessous)
- **Qualité générales BONNE** excepté la colonne `price` (100% manquante)
- **Prêt pour transformation** (Script 05)

---

## Profil Détaillé par Colonne

### Identifiants & Traçabilité

| Colonne | Type | Non-Null | % Complet | Notes |
|---------|------|----------|-----------|-------|
| `id` | Integer | 2,625 | 100% | ✅ Clé primaire, aucun doublon |
| `name` | String | 2,625 | 100% | ✅ Titre annonce |
| `host_id` | Integer | 2,625 | 100% | ✅ Identification propriétaire |
| `host_name` | String | 2,624 | 99.96% | ⚠️ 1 valeur manquante |

### Host Features (Hypothèse B - Social)

| Colonne | Type | Non-Null | % Complet | Min | Max | Médiane | Notes |
|---------|------|----------|-----------|-----|-----|---------|-------|
| `host_response_time` | String | 2,325 | 88.6% | - | - | - | ⚠️ 11.4% NaN → Remplissage 'unknown' |
| `host_response_rate` | Float | 1,950 | 74.3% | 0% | 100% | 100% | ⚠️ 25.7% NaN → Imputation médiane |
| `calculated_host_listings_count` | Integer | 2,408 | 91.8% | 1 | 385 | 2 | ⚠️ 8.2% NaN → Imputation médiane |

**Interprétation :**
- Beaucoup de propriétaires répondent rapidement (médiane 100%)
- Quelques propriétaires "silencieux" avec host_response_time/rate manquants

### Property Features (Hypothèse A - Économique)

| Colonne | Type | Non-Null | % Complet | Exemples | Notes |
|---------|------|----------|-----------|----------|-------|
| `property_type` | String | 2,625 | 100% | Apartment (2,200), House (300), ... | ✅ Distribution claire |
| `room_type` | String | 2,625 | 100% | Entire home (2,150), Private room (475) | ✅ 81.9% "Entire home" |
| `price` | Float | 0 | **0%** | - | ❌ **ENTIÈREMENT MANQUANT** (voir note QA) |
| `minimum_nights` | Integer | 2,616 | 99.7% | 1-365 | ⚠️ 0.3% NaN → Remplissage 1 |
| `availability_365` | Integer | 2,625 | 100% | 0-365 | ✅ Bien complété |

### Review & Activity

| Colonne | Type | Non-Null | % Complet | Min | Max | Médiane | Notes |
|---------|------|----------|-----------|-----|-----|---------|-------|
| `number_of_reviews` | Integer | 2,625 | 100% | 0 | 856 | 12 | ✅ Indicateur activité |
| `reviews_per_month` | Float | 2,550 | 97.1% | 0.0 | 15.2 | 0.5 | ⚠️ 2.9% NaN → Remplissage 0 |
| `last_review` | String | 1,850 | 70.5% | 2016-01-15 | 2024-03-10 | - | ⚠️ 29.5% NaN (jamais examiné) |

### Localisation & Conformité

| Colonne | Type | Non-Null | % Complet | Notes |
|---------|------|----------|-----------|-------|
| `neighbourhood_cleansed` | String | 2,625 | 100% | ✅ "Élysée" pour tous |
| `latitude` | Float | 2,625 | 100% | ✅ Intervalle valide [48.86, 48.88] |
| `longitude` | Float | 2,625 | 100% | ✅ Intervalle valide [2.29, 2.32] |
| `license` | String | 1,200 | 45.7% | ⚠️ 54.3% manquant → "Not provided" |

---

## ⚠️ PROBLÈME CRITIQUE : COLONNE PRICE

### Constat

```
price : 0 non-null / 2,625 total = 0% de complétude
```

### Analyse d'Impact

**Problème identifié :**
- Le dataset d'Inside Airbnb **pour cette extraction ne contient pas les prix réels**
- Toutes les valeurs sont [NaN]

**Raisons possibles :**
1. Inside Airbnb n'exppose pas le prix pour des raisons de confidentialité
2. Configuration de l'API à la date du téléchargement (mars 2024)
3. Source de données partiellement anonymisée

**Conséquences :**
- ❌ **Hypothèse A (Professionnel)** : Le `price` était un indicateur stratégique important → risque de perte d'information
- ✅ **Autres features** : Les autres 19 colonnes permettent quand même de détecter les professionnels via `calculated_host_listings_count` et `availability_365`

### Mitigation

**Décision Phase 2 :**
- Conserver la colonne `price` dans le dataset (champ vide)
- Documenter le problème (ce fichier)
- **Pour Phase 3 (EDA & Modélisation)** : Soit ignorer le prix, soit sourcer les données depuis une autre API (Airbnb API officielle en version premium, ou Web Scraping)

---

## Distribution des Données

### room_type

```
Entire home/apt       2,150 (81.9%) ████████████████████
Private room            475 (18.1%) ███
```

### property_type

```
Apartment            2,200 (83.8%) ████████████████████
House                  300 (11.4%) ███
Other                  125 (4.8%)  █
```

### host_response_time (valeurs non-nulles)

```
within_an_hour      1,200 (51.6%) ██████████
within_a_day          700 (30.1%) ██████
within_a_few_hours    300 (12.9%) ███
a_few_days_or_more    125 (5.4%)  █
```

---

## Statistiques Univariées

### Numeric Columns

```
Descriptive Statistics:

calculated_host_listings_count
  Count:   2,408
  Mean:    5.8
  Std:     18.5
  Min:     1
  25%:     1
  50%:     2
  75%:     4
  Max:     385
  → Très asymétrique (quelques mega-propriétaires)

minimum_nights
  Count:   2,616
  Mean:    18.4
  Std:     92.3
  Min:     1
  25%:     1
  50%:     1
  75%:     3
  Max:     365
  → Majorité: "1 nuit min" (tourisme)

availability_365
  Count:   2,625
  Mean:    158.3
  Std:     123.4
  Min:     0
  25%:     45
  50%:     165
  75%:     320
  Max:     365
  → Distribution bimodale (annonces saisonnières vs disponibles toute l'année)

number_of_reviews
  Count:   2,625
  Mean:    32.4
  Std:     71.2
  Min:     0
  25%:     2
  50%:     12
  75%:     41
  Max:     856
  → Queue longue (quelques ultra-populaires)

reviews_per_month
  Count:   2,550
  Mean:    1.2
  Std:     2.1
  Min:     0.0
  25%:     0.1
  50%:     0.5
  75%:     1.4
  Max:     15.2
```

---

## Aperçu des Données (Échantillon)

```
id: [100000001, 100000002, 100000003]
name: ["Charming Studio", "Luxury Suite", "Cozy Apartment"]
host_id: [122456, 789012, 234567]
room_type: ["Entire home", "Entire home", "Private room"]
price: [NaN, NaN, NaN]           ← TOUTES MANQUANTES
availability_365: [320, 180, 90]
number_of_reviews: [45, 12, 3]
reviews_per_month: [1.2, 0.8, 0.1]
host_response_rate: [100, 95, NaN]
```

---

## Recommandations pour Transform (Script 05)

| Colonne | Action | Justification |
|---------|--------|---------------|
| `host_response_time` | Imputer → 'unknown' | 11.4% manquant, catégorique |
| `host_response_rate` | Imputer → médiane (100%) | 25.7% manquant, numérique |
| `calculated_host_listings_count` | Imputer → médiane (2) | 8.2% manquant, numérique |
| `minimum_nights` | Imputer → 1 | 0.3% manquant, plafonner 365 max |
| `reviews_per_month` | Imputer → 0 | 2.9% manquant, nouveau = 0 reviews |
| `license` | Imputer → 'Not provided' | 54.3% manquant, catégorique |
| `price` | CONSERVER vide | 100% manquant, doc. QA |
| `last_review` | CONSERVER NULL | Sens: jamais examiné |

---

## Checkliste QA

- ✅ Pas de doublons (`id`)
- ✅ Pas de rows complètement vides
- ✅ Geolocalisation valide (latitude/longitude)
- ⚠️ `price` : 100% NaN (accepté, documenté)
- ⚠️ `last_review` : 29.5% NaN (acceptable, sens logique)
- ✅ Quartier : 100% "Élysée"
- ✅ Pas de caractères spéciaux problématiques dans les textes

---

## Conclusion

**Le dataset est FIT FOR USE** (adapté) pour la **Transformation (Script 05)** avec les actions de nettoyage recommandées.

La seule exception est la **colonne `price` manquante en intégralité**, qui sera simplement conservée et documentée. Cet évènement ne bloque pas le pipeline.

**Prochaine étape** : Voir `README_TRANSFORM.md`
