# 1. Situation de départ — Power BI branché en direct sur la gestion

**TransVal Logistique** est un transporteur citerne fictif (48 tracteurs, 62 conducteurs, 40 clients, cinq activités :
vrac liquide, pulvérulent, alimentaire, chimie, conteneur) basé en Auvergne-Rhône-Alpes. Son pilotage repose sur Power BI,
construit au fil des besoins : chaque service a demandé son rapport, chaque rapport a ses propres requêtes sur les systèmes
de gestion. Il n'y a **aucun entrepôt de données**.

Ce fonctionnement est reproduit tel quel dans [`legacy/rapports_powerbi.py`](../legacy/rapports_powerbi.py) : neuf rapports,
un par domaine, qui lisent les sources en direct et appliquent leur logique Power Query + DAX, défauts compris.

## Six familles de sources, interrogées en direct

| Famille | Rôle | Particularités |
|---|---|---|
| ERP legacy **IBM DB2 / AS/400** | paie, pointages, chronotachygraphe, carburant | Dates stockées en nombres `AAAAMMJJ`, durées en secondes, champs à largeur fixe complétés d'espaces, matricules de longueurs variables. Toute la conversion se fait en SQL écrit à la main dans chaque requête. |
| **TMS** (SQL Server) | voyages, clients, relations, atelier, visites techniques | Voyages régularisés après coup ; relation vide pour les voyages « spot ». |
| **Comptabilité** (type Sage) | écritures fournisseurs | N° de pièce texte, différent du n° de facture saisi à l'atelier. |
| **Télématique / RH** (Oracle) | conducteurs, consommation, infractions, autoroutes | Matricule préfixé, dates texte. |
| **Listes SharePoint** | justifications, objectifs, QHSE, coûts standard | Saisie libre (`Oui`/`oui`/`OUI `), dates mélangées texte/date. |
| Tables calculées DAX | calendrier, sélecteurs | Paramètres et menus figés dans le fichier. |

## Constats

1. **Les mêmes données sont chargées plusieurs fois.** Chaque rapport importe la même table source avec sa propre requête :
   affectations, activités, pointages, compteurs mensuels existent en plusieurs exemplaires, chacun avec ses colonnes, ses
   filtres et ses mesures.
2. **Plusieurs versions de la vérité.** Les copies ne filtrent pas pareil : la requête de pointage du tableau de bord
   exploitant garde les saisies d'exploitation (type de saisie `E`/`S`), celle du palmarès conducteurs non. Les deux rapports
   affichent donc un nombre d'heures de chargement/déchargement **différent pour le même mois**
   (voir [3. Améliorations](03-ameliorations.md)).
3. **Mesures recopiées.** Une même formule existe en plusieurs exemplaires rattachés à des tables différentes. Corriger une
   règle de calcul oblige à la corriger partout, sans garantie de cohérence.
4. **Le temps n'est pas figé.** `TODAY()` dans les mesures et une fenêtre glissante de trois ans en SQL : un même rapport
   ouvert deux jours différents donne deux résultats, et l'historique disparaît chaque 1er janvier. Impossible de rejouer
   un chiffre passé ou de le tester.
5. **Le nettoyage est fait au moment de l'affichage.** `TRIM`, `SUBSTITUTE`, `CONTAINSSTRING` dans les mesures, libellés
   d'activité orthographiés de deux façons (avec et sans accent), matricule tronqué dans une requête mais pas dans les autres.
6. **Règles métier cachées dans des formules.** Un coût forfaitaire du km à vide, la liste des familles d'atelier exclues du
   taux de sous-traitance, une règle de clôture mensuelle (« à partir du 10 du mois, le mois précédent est clos »), une
   franchise d'attente : elles n'existent que dans le DAX, sans documentation.
7. **Modèle lourd et fragile.** Tables de dates automatiques, relations bidirectionnelles (ambiguïtés de filtrage), aucune
   sécurité par ligne, et une actualisation qui interroge six systèmes de production.

## Ce qui marche (et qu'il faut garder)

- Le **catalogue d'indicateurs** est riche et pertinent : CA, marge sur coûts variables, appairage, coût autoroute, heures hors
  conduite par voyage, coût maintenance aux 100 km, taux de sous-traitance, pannes, contrôle des prestations à facturer,
  rapprochement atelier/comptabilité, QHSE, absences.
- Les **règles métier** sont justes dans l'ensemble : elles ont été validées par l'usage. L'objectif n'est pas de les
  réinventer mais de les **sortir du DAX**, de les écrire une fois et de les tester.

→ Suite : [2. Fonctionnement](02-fonctionnement.md)
