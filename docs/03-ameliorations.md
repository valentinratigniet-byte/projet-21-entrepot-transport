# 3. Améliorations — ce que l'entrepôt change, constat par constat

| # | Constat (situation de départ) | Réponse dans l'entrepôt | Où |
|---|---|---|---|
| 1 | Mêmes tables chargées par chaque rapport | Chaque source est importée **une fois** en RAW, puis exposée par un seul fait | `ingestion/`, `marts/fct_*` |
| 2 | Plusieurs versions de la vérité (filtres différents selon le rapport) | Les filtres deviennent des colonnes booléennes ; une seule définition par KPI dans `mart_kpi` | `fct_pointage.est_valide`, `est_saisie_exploitation` |
| 3 | Mesures recopiées d'un rapport à l'autre | 53 KPI définis une fois, réutilisables à toutes les périodes | `kpi_*.sql`, `mart_kpi` |
| 4 | `TODAY()` dans les mesures, fenêtre glissante de 3 ans | `as_of` figé (variable dbt), historique complet conservé | `dbt_project.yml`, `int_periode` |
| 5 | Nettoyage dans le DAX | Nettoyage en staging, testé (formats, accents, casse, matricules) | macros `helpers.sql`, `stg_*` |
| 6 | Règles métier enfouies dans les formules | Règles nommées, en colonnes ou en seeds versionnés, documentées | `seeds/`, `_marts.yml` |
| 7 | Tables de dates automatiques, relations bidirectionnelles | Une `dim_date` (fériés, jours ouvrés), schéma en étoile à filtrage simple | `dim_date`, dimensions conformes |
| 8 | Actualisation = 6 systèmes de production interrogés | Imports incrémentaux (CDC, fenêtres, snapshots), journal des lots | `raw_meta.import_log` |
| 9 | Aucun test : une erreur se voit dans le rapport, ou jamais | 48 tests dbt + tests de parité en CI | `dbt/tests`, `tests/`, `.github/workflows` |

## Les corrections chiffrées

Elles sont détectées par le test de parité, qui vérifie que **l'écart s'explique exactement** (et non qu'il est « à peu près »
justifiable).

### Heures de chargement/déchargement : deux rapports, deux chiffres

| Août 2026 | Heures |
|---|---|
| Palmarès conducteurs (sans filtre sur le type de saisie) | 1 343,5 |
| Tableau de bord exploitant (saisies d'exploitation `E`/`S`) | 1 286,2 |
| **Entrepôt (définition unique, celle du tableau de bord)** | **1 286,2** |

L'écart (≈ 57 h sur le mois) correspond exactement aux corrections manuelles (`M`). Le test le recalcule depuis `fct_pointage`.

### Taux de réussite des visites techniques

Le DAX comparait le texte strictement à `"Valide"`. Les saisies `valide ` (espace) ou `VALIDE` comptaient comme des refus.
Sur 2026 : **75,0 % dans le Power BI de départ contre 87,5 % en réalité** (staging : `upper(trim(resultat)) = 'VALIDE'`).

### Projection d'heures de fin de mois

La mesure de départ utilise `NETWORKDAYS()` sans liste de jours fériés : le 25 décembre est compté comme un jour travaillé.
L'entrepôt conserve cet indicateur (parité) **et** ajoute `projection_fin_mois_hors_feries` : au 30/09/2026 il ne reste
aucun férié dans le mois et les deux valeurs coïncident ; en décembre, en revanche, la première compterait le 25 comme un
jour travaillé.

### Consommation moyenne

La mesure de départ fait une moyenne de ratios (`AVERAGEX` de L/100 km par tracteur-jour) : un jour à 20 km pèse autant
qu'un jour à 500 km. L'entrepôt ajoute `conso_ponderee_l100` (litres totaux / km totaux). Sur ces données fictives l'écart
est faible car la consommation simulée est homogène ; avec beaucoup de petits trajets il devient sensible : l'indicateur
pondéré est le bon.

### Côté rapports : un rapport par sujet

L'entrepôt supprime les doublons de **données** ; le modèle sémantique et les rapports suppriment ceux de **présentation** :
23 rapports, un par sujet (le nom dit ce qu'on y trouve), des pages aux noms explicites, une page par famille
d'indicateurs avec un segment de thème au lieu d'une page par indicateur, des liens entre rapports résolus au déploiement,
et aucune ligne vide (voyages « Spot » nommés, jours d'immobilisation dans leur propre table). Le déploiement est décrit « as code »
(fabric-cicd, paramètre de source par environnement) au lieu d'une publication manuelle depuis Desktop.
Détail : [5. Power BI](05-power-bi.md#23-rapports-de-pilotage-un-par-sujet).

## Ce que l'entrepôt ne corrige pas (limites assumées)

- **Les données sont fictives.** Les volumes et les valeurs illustrent des mécanismes, pas des montants d'entreprise.
- **Les imports sont simulés** depuis des fichiers et des bases SQLite, pas depuis de vrais connecteurs DB2/Oracle/SharePoint.
  Les stratégies d'extraction (fenêtre avec recouvrement, CDC, snapshot) sont celles qu'on mettrait en production.
- **Le Power BI de départ est reproduit sur 9 rapports** (un par domaine métier : activité, facturation, heures, parc,
  atelier, rapprochement, carburant, QHSE, absences) : c'est ce qui sert de référence au test de parité.
- **DuckDB** remplace un SQL Server de production : même modèle, même SQL standard, choisi pour que le projet tourne en une
  commande sans serveur.

## Pistes suivantes

- Remplacer les imports simulés par de vrais connecteurs (Data Factory, Fivetran ou dlt) et l'entrepôt DuckDB par un
  Fabric Warehouse : seules l'expression `DossierDonnees` et la source des partitions du modèle changent.
- Ajouter des seuils d'alerte par KPI (tests dbt `warn`) : écart de rapprochement, taux de facturation des attentes.
- Capter le journal des mouvements RH à la source pour dater les changements de contrat à leur date d'effet.

→ Détail mesure par mesure : [4. Correspondance Power BI → entrepôt](04-correspondance-powerbi-entrepot.md)
