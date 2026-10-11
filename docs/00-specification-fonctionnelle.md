# 0. Spécification fonctionnelle — ce que le pilotage doit permettre, et comment on le vérifie

Ce document fixe le besoin **avant** la technique : qui utilise les chiffres, pour décider quoi, avec quelles règles de
calcul et quels critères d'acceptation. Chaque exigence renvoie à ce qui la livre et au test qui la prouve ; la recette
complète est rejouée en CI à chaque modification.

> Entreprise et utilisateurs fictifs (TransVal Logistique). Les rôles sont ceux d'un transporteur citerne de taille PME.

## 1. Objectifs métier

| # | Objectif | Indicateur de réussite | Atteint |
|---|---|---|---|
| O1 | **Un seul chiffre par indicateur**, quel que soit le rapport | 0 écart entre rapports sur un même KPI et une même période | ✅ 2 213 valeurs entrepôt ↔ Power BI, 0 écart |
| O2 | **Ne rien perdre** de ce que le Power BI de départ calculait juste | KPI identiques à ceux de départ, sauf erreurs prouvées | ✅ 93 / 97 identiques, 4 corrections expliquées au centime |
| O3 | **Chacun voit ce qui le concerne**, et seulement cela | un exploitant ne voit que ses activités | ✅ sécurité par ligne, testée |
| O4 | **Des chiffres à jour chaque matin** sans intervention | actualisation avant 7 h les jours ouvrés, alerte si problème | ✅ n8n, e-mail seulement en cas d'alerte ou d'échec |
| O5 | **Savoir si l'on peut faire confiance** à un chiffre | qualité des imports visible par les utilisateurs | ✅ rapport Qualité des données, seuils d'alerte |

## 2. Périmètre

**Dans le périmètre** : activité commerciale et facturation, exploitation et heures conducteurs, atelier et parc, carburant,
QHSE, contrôle de gestion (rapprochement, rentabilité), référentiel conducteurs ; six systèmes sources ; diffusion par
Power BI.

**Hors périmètre** : la paie elle-même (seuls ses compteurs sont lus), l'écriture dans les systèmes de gestion (l'entrepôt les
**lit sans jamais y écrire**), la planification des tournées, les prévisions de CA.

## 3. Utilisateurs et besoins

| Rôle | Décisions qu'il prend | Ce qui le bloquait | Rapports |
|---|---|---|---|
| **Direction** | tarifs clients, investissement parc, recrutement | deux réunions, deux chiffres ; pas de marge sur coûts réels | Activité clients, Rentabilité, Prix et indexation |
| **Responsable d'exploitation** (un par activité) | affecter conducteurs et tracteurs pour J+1, suivre les heures | voit toutes les activités, chiffres changeants d'un jour à l'autre | Tableau de bord exploitant, Heures, Projection, Missions, Absences |
| **Contrôleur de gestion** | facturer les prestations annexes, clôturer le mois | attentes non facturées, factures atelier non rapprochées | Prestations à facturer, Rapprochement, Rentabilité |
| **Responsable atelier** | préventif ou sous-traitance, renouvellement du parc | coût de maintenance mélangé au lavage ; pannes dispersées | Maintenance atelier, Parc matériel, Anomalies matériel |
| **Responsable QHSE** | actions de prévention, sanctions | infractions et autoroutes interdites dans des fichiers séparés | Tableau de bord QHSE, Infractions RSE, Autoroutes interdites |
| **RH** | contrats, heures supplémentaires | référentiel sans historique | Référentiel conducteurs, Heures conducteurs |
| **Équipe data** | corriger, faire évoluer, déployer | aucun test, aucune trace des imports, publication manuelle | Qualité des données, CI, n8n |

## 4. Exigences sous forme de récits utilisateur

Priorité MoSCoW : **M** = indispensable, **S** = important, **C** = souhaitable. Chaque critère d'acceptation est vérifié
par un test ou par un contrôle visuel noté dans la dernière colonne.

### E1 — Un chiffre, une définition

| ID | En tant que… je veux… afin de… | P | Critère d'acceptation | Livré dans · vérifié par |
|---|---|---|---|---|
| US-01 | contrôleur de gestion, **une seule définition des heures de chargement/déchargement**, afin que le palmarès et le tableau de bord exploitant ne se contredisent plus | M | août 2026 : les deux rapports affichent **1 286,2 h** ; l'écart de départ (1 343,5 h) est égal aux corrections manuelles | `fct_pointage.est_saisie_exploitation` · `tests/test_parity.py` |
| US-02 | direction, **rejouer un chiffre passé** à l'identique, afin de pouvoir le justifier en réunion | M | aucun `TODAY()` ; toute mesure se calcule à une date de référence ; deux exécutions donnent le même résultat | `parametres.date_reference` · parité DAX 2 213 / 0 |
| US-03 | responsable parc, un **taux de réussite des visites techniques** juste, quelle que soit la saisie | M | « Valide », « valide  », « VALIDE » comptent comme réussis : 2026 = **87,5 %** (75,0 % au départ) | `stg_tms__visite_technique` · `test_parity.py` |
| US-04 | tout utilisateur, **les mêmes noms d'indicateurs partout** | S | chaque KPI défini une fois dans `mart_kpi`, une mesure par KPI, variantes N-1 générées | `mart_kpi`, `powerbi/mesures.py` · test `mart_kpi_grain_unique` |

### E2 — Exploitation au quotidien

| ID | En tant que… je veux… afin de… | P | Critère d'acceptation | Livré dans · vérifié par |
|---|---|---|---|---|
| US-05 | responsable d'exploitation, **voir le prochain jour ouvré** : missions, CA prévu, tracteurs libres, conducteurs sans mission, afin de finir le planning | M | une page globale et une page par activité, même disposition, une couleur par activité | Tableau de bord exploitant › Exploitation J+1 · contrôle visuel |
| US-06 | responsable d'exploitation, **ne voir que mes activités**, remplaçants compris | M | exploitant chimie = **6 434 voyages** (tous ceux de l'activité) ; compte sans habilitation = 0 ; direction = tout | rôles Exploitant / Direction, seed `habilitations` · impersonation DAX |
| US-07 | responsable d'exploitation, **projeter les heures de fin de mois** par conducteur face aux repères légaux | S | repères 152 h, 186 h, 208 h ; variante hors jours fériés | Projection des heures · `test_parity.py` |
| US-08 | responsable d'exploitation, **suivre les absences** par conducteur et par motif | S | absents uniques par jour ouvré, détail par période | Absences conducteurs · contrôle visuel |

### E3 — Facturation et rentabilité

| ID | En tant que… je veux… afin de… | P | Critère d'acceptation | Livré dans · vérifié par |
|---|---|---|---|---|
| US-09 | contrôleur de gestion, **la liste des attentes facturables** au-delà de la franchise, afin de ne plus en oublier | M | voyage signalé si temps sur site > 3 h (RG-04) ; montant à facturer vs facturé ; justificatifs rattachés | `fct_voyage.est_hors_franchise` · Prestations à facturer |
| US-10 | contrôleur de gestion, **rapprocher factures atelier et comptabilité**, afin de clôturer sans pointage manuel | M | facture absente en compta ou écart de montant signalé, avec seuil d'alerte (RG-12) | `fct_rapprochement_atelier_compta` · rapport Qualité |
| US-11 | direction, **la marge directe sur coûts réels** par tracteur et par conducteur | S | CA − péages − carburant prélevé − atelier (tracteur) ; CA − salaire chargé − frais − carburant (conducteur) ; le CA ventilé retombe exactement sur le CA des voyages livrés | `fct_rentabilite_*_mois` · test `rentabilite_ca_complet` |
| US-12 | direction, **suivre prix et indexation gazole** par client | C | prix au km par client et relation, location distinguée | Prix et indexation clients · contrôle visuel |

### E4 — Atelier, parc, carburant, QHSE, RH

| ID | En tant que… je veux… afin de… | P | Critère d'acceptation | Livré dans · vérifié par |
|---|---|---|---|---|
| US-13 | responsable atelier, **un taux de sous-traitance qui exclut le lavage** | M | familles exclues dans une table versionnée, pas dans une formule | seed `ref_famille_atelier` · `kpi_atelier` |
| US-14 | responsable atelier, **savoir d'où vient un indicateur** | C | info-bulle : mesure DAX, modèle dbt, sources | Maintenance atelier · contrôle visuel |
| US-15 | responsable carburant, **une consommation qui ne surpondère pas les petits trajets** | S | consommation pondérée = litres totaux / km totaux (RG-06) | `conso_ponderee_l100` · `mart_kpi` |
| US-16 | responsable QHSE, **infractions RSE et passages sur autoroutes interdites** par conducteur | S | un rapport par sujet, filtrable par conducteur et période | Infractions RSE, Autoroutes interdites |
| US-17 | RH, **l'historique des contrats** de chaque conducteur | S | une version par changement observé, sans chevauchement de dates | `dim_conducteur_historique` (SCD2) · test `historique_conducteur_sans_chevauchement` |

### E5 — Confiance, exploitation, évolution

| ID | En tant que… je veux… afin de… | P | Critère d'acceptation | Livré dans · vérifié par |
|---|---|---|---|---|
| US-18 | tout utilisateur, **des chiffres à jour chaque matin** sans rien faire | M | actualisation à 6 h du lundi au vendredi ; données de moins d'un jour | n8n `0 6 * * 1-5` · test `sources_a_jour` |
| US-19 | équipe data, **être prévenue seulement s'il y a un problème** | M | e-mail si statut ALERTE ou échec ; aucun e-mail si tout est OK | `ops/rapport_execution.py`, workflows n8n · testés avec un serveur SMTP local |
| US-20 | tout utilisateur, **voir ce que l'import a corrigé** et la date d'actualisation | S | rapport Qualité : 14 contrôles à l'import, dont 9 avec seuil d'alerte ; pied de page de chaque rapport = date d'actualisation | `mart_qualite_donnees`, `ops/seuils_qualite.json` |
| US-21 | équipe data, **un import qui ne perd ni ne double rien**, même avec recouvrements et corrections tardives | M | chargement incrémental = recalcul complet ; chaque voyage une fois, dans sa dernière version | tests `incremental_egal_recalcul_complet`, `import_voyages_sans_perte_ni_doublon` |
| US-22 | équipe data, **savoir quels rapports sont touchés** par un changement de modèle | S | les 23 rapports déclarés comme exposures dbt, à jour (vérifié en CI) | `powerbi/exposures_dbt.py` · CI |
| US-23 | équipe data, **déployer en DEV puis PROD sans manipulation** | C | source et liens entre rapports réécrits par environnement | fabric-cicd, `parameter.yml` · **prêt, non exécuté (pas de tenant)** |

## 5. Règles de gestion

Avant le projet, ces règles n'existaient que dans des formules DAX ou des requêtes. Elles sont désormais nommées, écrites
une fois et testables.

| ID | Règle | Où elle est écrite |
|---|---|---|
| RG-01 | Heures de chargement/déchargement = pointages **valides** (non exclus, statut F ou V) **saisis par l'exploitation** (types E/S) ; les corrections manuelles M sont exclues | `fct_pointage` |
| RG-02 | Visite technique réussie = résultat « VALIDE » sans tenir compte des espaces ni de la casse | `stg_tms__visite_technique` |
| RG-03 | Km à vide valorisés au coût forfaitaire de **1,40 €/km** | `fct_voyage` |
| RG-04 | Franchise d'attente : **1 h 30 au chargement + 1 h 30 à la livraison = 3 h** (contrat type citerne), toutes activités ; au-delà, l'attente est facturable | `fct_voyage` |
| RG-05 | Le **lavage** ne compte pas dans le taux de sous-traitance (préventif, panne, sinistre oui) | seed `ref_famille_atelier` |
| RG-06 | Consommation = Σ litres / Σ km × 100 (pondérée), en plus de la moyenne des ratios conservée pour la parité | `kpi_carburant` |
| RG-07 | Jour ouvré = lundi-vendredi hors jours fériés français | seed `jours_feries`, `dim_date` |
| RG-08 | Marge sur coûts variables (MCV %) calculée **hors voyages spot** (sans relation contractuelle) | mesure « MCV % » |
| RG-09 | Heures compensées = base mensuelle du contrat − heures réalisées ; bases : 186 h (grand routier), 169 h (courte distance), 151,67 h et 121,33 h (remplaçants) | `fct_compteur_mois` |
| RG-10 | Tout calcul se fait à une **date de référence** (dernier import), jamais à la date du jour | `parametres`, variable dbt `as_of` |
| RG-11 | Un exploitant voit les activités de son habilitation **et** les remplaçants du pool partagé | rôle Exploitant, seed `habilitations` |
| RG-12 | Seuils d'alerte qualité (part des lignes) : doublons 5 %, versions CDC 2 %, facture absente 5 %, écart de montant 5 %, fraîcheur 1 jour… | `ops/seuils_qualite.json` |

## 6. Exigences non fonctionnelles

| Domaine | Exigence | Mesure |
|---|---|---|
| Fraîcheur | données de la veille disponibles à l'ouverture | actualisation 6 h, test de fraîcheur ≤ 1 jour |
| Performance | chaîne complète rejouable rapidement | ≈ 2 min (3 imports + 3 `dbt build` + parité) |
| Sécurité | moindre privilège ; aucune écriture dans les systèmes sources | sécurité par ligne ; aucune écriture vers les sources |
| Traçabilité | savoir ce qui a été chargé et quand | journal des lots `raw_meta.import_log`, rapport Qualité |
| Testabilité | toute règle de calcul vérifiable automatiquement | 48 tests dbt + 3 contrôles de parité + contrôles des rapports, en CI |
| Maintenabilité | une règle corrigée une fois, partout | 0 colonne calculée, 0 étape Power Query ; 352 mesures, une définition chacune |
| Ergonomie | trouver un chiffre sans formation | un rapport par sujet, pages nommées en clair, 3 niveaux de couleur (bon / moyen / mauvais) |

## 7. Recette

La recette ne repose pas sur un contrôle visuel « à l'œil » mais sur la **comparaison automatique** avec le Power BI de
départ : 97 KPI recalculés des deux côtés sur les mêmes données. 93 sont identiques ; pour les 4 autres, le test recalcule
l'écart depuis l'entrepôt et vérifie qu'il s'explique **exactement** par la règle corrigée (US-01, US-03). Le nouveau modèle
Power BI est ensuite comparé à l'entrepôt sur 2 213 valeurs (0 écart). Les 23 rapports ont été ouverts dans Power BI Desktop
et contrôlés page par page, et leurs champs, filtres et liens sont vérifiés statiquement à chaque modification.

## 8. Points ouverts et décisions

| Sujet | Décision ou proposition |
|---|---|
| Date d'effet des changements de contrat | aujourd'hui datés au lot qui les observe ; capter le journal RH à la source pour la date exacte |
| Déploiement en production | prêt (fabric-cicd, DEV / PROD) ; à exécuter dès qu'un espace de travail Power BI Service est disponible |
| Alertes par indicateur | ajouter des seuils métier (écart de rapprochement, taux de facturation des attentes) en tests dbt `warn` |
| Connecteurs | remplacer les imports simulés par de vrais connecteurs ; seule la source du modèle change |

→ Suite : [1. Situation de départ](01-situation-de-depart.md)
