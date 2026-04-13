# 📜 Rapport de Diagnostic Final : Diagnostic de l'Offre Airbnb
**Secteur : Élysée (Paris 8ème)**  
**Projet : ImmoVision 360**  
**Auteur :** MOUSSAOUI Ismail — Avril 2026

---

## 1. Synthèse (Executive Summary)
Ce diagnostic révèle un marché locatif de courte durée dans le quartier de l'Élysée qui a largement basculé vers une **gestion professionnelle et industrielle**. 
- **58,1 %** des annonces appartiennent à des multi-hébergeurs (hôtes possédant plus d'une annonce).
- **59,0 %** des annonces (soit **1 548 biens**) dépassent la limite légale des **120 jours/an**, indiquant une perte nette de logements pour les résidents permanents.
- L'analyse par IA confirme que **35 % des annonces totales** (936 biens) sont de parfaits "hôtels déguisés" : standardisation visuelle forte et discours marketing purement hôtelier.

---

## 2. Méthodologie : Data Science & Intelligence Artificielle
Pour ce diagnostic, nous avons traité **2 625 annonces** via un pipeline technologique rigoureux :
1. **Ingestion & Filtrage :** Extraction des données brutes (Inside Airbnb) limitées au périmètre Élysée.
2. **Enrichissement IA (Vision & NLP) :** Utilisation de modèles de langage (Gemini) pour classer les images (Standardization_Score) et les descriptions (Neighborhood_Impact_Score) selon leur niveau de professionnalisation.
3. **Data Warehouse :** Stockage dans PostgreSQL pour une analyse croisée de précision et une intégrité des données garantie.

---

## 3. Résultats Clés de l'Analyse

### 3.1. Une professionnalisation dominante
Le mythe du particulier louant occasionnellement sa propre chambre est contredit par les chiffres. Avec près de **6 annonces sur 10** gérées par des hôtes multi-propriétaires ou des conciergeries, le quartier de l'Élysée est devenu un terrain d'investissement professionnel intense au détriment de l'habitat partagé.

### 3.2. Le non-respect massif du seuil de résidence principale
La loi limite à 120 jours par an la location d'une résidence principale. Notre analyse montre que **1 548 logements** sont disponibles au-delà de ce seuil. Ces biens fonctionnent comme des micro-unités hôtelières permanentes, retirant plus de **1 500 opportunités de logement** aux Parisiens qui souhaiteraient vivre dans le quartier.

### 3.3. L'industrialisation visuelle et textuelle
Le croisement de nos scores IA (Standardisation et Impact Quartier) montre une corrélation parfaite :
- Les annonces les plus standardisées ("Style Catalogue/Hôtel") sont celles qui exploitent le plus le marketing du quartier dans leurs textes.
- Le cluster le plus important (**936 annonces**) combine ces deux critères, signalant une offre formatée pour le tourisme de masse, loin de l'authenticité "chez l'habitant".

---

## 4. Limites de l'Étude
- **Source unique :** Les données proviennent exclusivement d'Airbnb. Les autres plateformes (Abritel, Booking) n'ont pas été auditées, ce qui signifie que l'impact réel sur le logement est probablement **encore plus élevé**.
- **Données de prix :** La colonne prix étant partiellement manquante dans la source, l'analyse économique n'a pu porter que sur les volumes de disponibilité et la typologie des acteurs.

---

## 5. Conclusion & Recommandations
Le quartier de l'Élysée est confronté à une hôtélisation massive et industrialisée qui vide le centre de Paris de ses habitants.

**Recommandations pour la Mairie de Paris :**
1. **Audit de Conformité :** Contrôler prioritairement les **1 548 annonces** identifiées au-delà du seuil des 120 jours.
2. **Régulation des Comptes Pros :** Imposer une licence spécifique et des quotas pour les comptes "multi-annonces" qui contrôlent désormais **58,1 %** du marché local.
3. **Défense du Logement Permanent :** Durcir les règles de changement d'usage pour préserver la fonction résidentielle du 8ème arrondissement face à la pression du marketing hôtelier.

---
*Fin du rapport diagnostic — ImmoVision 360*
