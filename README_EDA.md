# 📊 Phase 3 : EDA & Exploration (Mairie de Paris)

Ce document détaille la Phase 3 du projet ImmoVision 360, consacrée à l'analyse exploratoire des données (EDA) stockées dans le Data Warehouse PostgreSQL.

---

## 🎯 Objectifs de l'Analyse

L'objectif principal est de transformer les données brutes consolidées en **récit vérifiable** pour répondre aux préoccupations de la Mairie de Paris concernant l'impact d'Airbnb sur le quartier de l'Élysée.

### 🗺️ Feuille de Route (Roadmap)

| Question Métier | Variables Proxy | Graphique |
| :--- | :--- | :--- |
| **1. Professionnalisation** | `calculated_host_listings_count` | Histogramme |
| **2. Intensité (Hôtels déguisés)** | `availability_365` | Histogramme (seuil 120j) |
| **3. Hôtélisation du quartier** | `standardization_score` vs `impact_score` | Heatmap |
| **4. Réactivité du Service** | `room_type_code` vs `host_response_time` | Barres empilées |
| **5. Performance Commerciale** | `host_response_rate` vs `availability_365` | Scatter Plot |

---

## 🛠️ Méthodologie

### 1. Connexion au Data Warehouse
L'analyse s'appuie sur la table `elysee_tabular` importée dans PostgreSQL (`immovision`).
- **Outil :** Jupyter Notebook (`scripts/07_eda.ipynb`)
- **Bibliothèques :** Pandas, Matplotlib, Seaborn, SQLAlchemy.

### 2. Nettoyage des données (Mandat Chapitre 5)
Toutes les valeurs manquantes (`NULL`) ont été remplacées par **-1** pour signifier « Information non disponible », évitant ainsi les biais de calcul tout en conservant l'intégrité du dataset.

---

## 📈 Résultats Clés

### A. Concentration du Marché
- Analyse de la distribution des hôtes multi-annonces.
- Identification des acteurs "industriels" possédant plusieurs dizaines de biens.

### B. Respect de la Limite Légale (120 jours)
- Visualisation de la proportion d'annonces dépassant le seuil de résidence principale.
- Identification des logements fonctionnant comme des hôtels permanents.

### C. Corrélation Standardisation / Impact
- Mise en évidence du lien entre le style "catalogue" des photos (IA Vision) et le discours "hôtelier" des descriptions (IA NLP).

---

## 🚀 Comment exécuter l'analyse

1. Assurez-vous que PostgreSQL est lancé et que la base `immovision` contient la table `elysee_tabular`.
2. Ouvrez VS Code dans le dossier racine.
3. Allez dans `scripts/07_eda.ipynb`.
4. Sélectionnez le noyau Python (`myenv`).
5. Exécutez toutes les cellules.

---

## 📂 Livrables
- **Notebook :** `scripts/07_eda.ipynb`
- **Rapport Final (Phase 4) :** À venir (PDF).

---
**Dernière mise à jour :** Avril 2026
