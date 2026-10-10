# 4. Correspondance Power BI → entrepôt

Pour chaque indicateur : ce que calcule le Power BI de départ ([`legacy/rapports_powerbi.py`](../legacy/rapports_powerbi.py)),
où sa logique vivait, et où elle vit maintenant.
Tous les KPI sont dans `marts.mart_kpi` (colonne `kpi`) ; ✅ = identique au centime près dans le test de parité, ⚠️ = correction voulue.

## Transformations Power Query / SQL natif → staging

| Transformation de départ (répétée dans chaque requête) | Entrepôt (écrite une fois) |
|---|---|
| Découpage de la date `AAAAMMJJ` avec `SUBSTR` et concaténation, sur chaque date AS/400 | macro `aaaammjj()` |
| `/ 3600` sur les durées en secondes | staging (`heures_*`) |
| Changement de type en culture `fr-FR` sur les décimales à virgule | macro `nombre_fr()` |
| Matricule tronqué à ses derniers caractères dans une seule requête | macro `matricule()` sur toutes les sources |
| `Text.Upper(Text.Trim([Justifié])) = "OUI"` | `stg_sp__justif_attente.est_justifie` |
| Filtre « année courante − 3 » en SQL | supprimé : historique complet, période choisie dans `int_periode` |
| Filtre « non exclu et validé » copié dans plusieurs requêtes | `fct_pointage.est_valide` |
| Filtre « saisie d'exploitation » présent dans une seule requête | `fct_pointage.est_saisie_exploitation` |
| Prix au litre calculé ligne à ligne avec un `CASE` sur la quantité nulle | `fct_prelevement_carburant.prix_litre`, `est_prelevement_reel` |
| Table DAX de dates + jours fériés + date/heure automatique | `dim_date` + seed `jours_feries` |

## Mesures DAX → `mart_kpi`

| Domaine | Indicateur | Logique de départ | KPI entrepôt | |
|---|---|---|---|---|
| Activité | CA facturé | `CALCULATE(SUM(CA), date de livraison <= TODAY())` | `ca_facture` (`fct_voyage.est_realise`) | ✅ |
| Activité | Nombre de voyages | `COUNTROWS` de la vue | `nb_voyages` | ✅ |
| Activité | Marge sur coûts variables (%) | somme de la marge lissée (ou brute si absente) / CA réparti, filtré sur relation non vide | `mcv_pct` (`fct_voyage.mcv_marge_retenue`) | ✅ |
| Activité | Appairage | km chargés / km totaux | `appairage` | ✅ |
| Activité | Coût autoroute aux 100 km | (péages + écotaxes chargé/vide) / km × 100 | `autoroute_eur_100km` (`fct_voyage.autoroute_eur`) | ✅ |
| Activité | CA par km, CA par heure | CA / km, idem heures | `ca_par_km`, `ca_par_heure` | ✅ |
| Activité | CA moyen par jour ouvré | CA à date / jours ouvrés, formaté en texte « k€ » | `ca_moyen_jour_ouvre` (numérique, formatage laissé au rapport) | ✅ |
| Activité | Coût des km à vide | (km total − km chargé) × coefficient forfaitaire | `km_vide_eur` (`fct_voyage.km_vide_eur`) | ✅ |
| Facturation | Attentes à facturer / taux d'attentes facturées | somme de la vue / somme des événements facturés | `attente_a_facturer_eur`, `attente_facturee_eur`, `pct_attente_facturee` | ✅ |
| Facturation | Lavages, samedis, doubles dépotages facturés | 4 tables d'événements chargées séparément | `lavage_*`, `samedi_facture_eur`, `double_depotage_facture_eur` (un seul `fct_evenement_facture`) | ✅ |
| Facturation | Justifications SharePoint | jointure texte sur n° de voyage | `attentes_justifiees` | ✅ |
| Heures | Heures hors conduite (total et par voyage) | travail + dispo + repos payé / nb voyages | `hchc_heures`, `hchc_par_voyage` (`fct_chrono_jour.heures_hors_conduite`) | ✅ |
| Heures | Heures à justifier, de chargement/déchargement, de décroche/raccroche | somme des durées / 3600 sur une liste de libellés en dur, deux orthographes comprises | `heures_a_justifier`, `heures_chargement_dechargement`, `heures_decroche_raccroche` (seed `ref_libelle_pointage`) | ✅ |
| Heures | Heures de chargement du palmarès conducteurs | même calcul sans filtre de type de saisie | remplacé par `heures_chargement_dechargement` | ⚠️ |
| Heures | Productivité (conduite / service) | conduite / service | `productivite_tc_ts` | ✅ |
| Heures | Heures compensées | (réalisé − base) × −1, avec une règle de clôture mensuelle sur `TODAY()` | `heures_compensees` (`fct_compteur_mois`, base = contrat de chaque conducteur ; règle sur `as_of`) | ✅ |
| Heures | Heures réalisées du mois et projection | réalisé + moyenne par jour × jours ouvrés restants (`NETWORKDAYS(TODAY(), EOMONTH())`) | `heures_realisees_mtd`, `projection_fin_mois` | ✅ |
| Heures | — | — | `projection_fin_mois_hors_feries` (nouveau) | ➕ |
| Parc | Tracteurs par jour ouvré, jours en maintenance | `COUNTROWS` / jours ouvrés | `nb_tracteurs_moyen_jour`, `jours_tracteur_maintenance` | ✅ |
| Parc | Nombre de conducteurs | `DISTINCTCOUNT` du matricule | `nb_conducteurs_actifs` | ✅ |
| Atelier | Coût maintenance aux 100 km | coût des OT / km × 100 | `cout_maintenance_100km` | ✅ |
| Atelier | Taux de sous-traitance | factures externes hors familles exclues (liste en dur) / coût total | `taux_sous_traitance` (seed `ref_famille_atelier`) | ✅ |
| Atelier | Pannes aux 10 000 km | OT de raison « panne » / km × 10 000 | `pannes_10000km` (`fct_intervention_atelier.est_panne`) | ✅ |
| Atelier | Taux de réussite des visites techniques | `résultat = "Valide"` (égalité stricte) | `tx_reussite_vt` (`upper(trim())`) | ⚠️ |
| Rapprochement | Statut et écart de montant (+ une quarantaine de mesures) | `SWITCH(TRUE(), ...)` évalué à l'affichage | `fct_rapprochement_atelier_compta.statut`, `nb_ok`, `nb_absent_*`, `nb_ecart_montant` | ✅ |
| Carburant | Prix moyen au litre | Σ montant / Σ quantité hors prélèvements à 0 L | `prix_moyen_litre`, `volume_litres` | ✅ |
| Carburant | Consommation moyenne | `AVERAGEX(conso × 100 / distance)` (moyenne de ratios) | `conso_moyenne_l100` | ✅ |
| Carburant | — | — | `conso_ponderee_l100` (nouveau, Σ L / Σ km) | ➕ |
| QHSE | Infractions, accidents du travail, jours perdus | `COUNTROWS`, `IF(ISBLANK(SUM()), 0, SUM())` | `nb_infractions`, `nb_infractions_classe5`, `nb_accidents_travail`, `jours_perdus` | ✅ |
| QHSE | Passages sur autoroutes interdites + justifications | somme Oracle + liste SharePoint | `passages_autoroutes_interdites`, `evenements_autoroutes_justifies` | ✅ |
| QHSE | Anomalies matériel, anomalies à traiter | dates texte et Excel mélangées | `nb_anomalies_materiel`, `anomalies_a_traiter` | ✅ |
| Absences | Absents uniques, jours d'absence moyens | `DISTINCTCOUNT`, `COUNTROWS / jours ouvrés` | `absents_uniques`, `jours_absence`, `jours_absence_moyen_par_jour_ouvre` | ✅ |

## Ce qui disparaît

- Les **copies** de mesures (` 1`, ` 2`, ` 3`) : un KPI = une ligne de `kpi_<domaine>.sql`.
- Les mesures de **mise en forme** (couleurs de fond, étiquettes, badges, textes « Du … au … ») : elles restent légitimes mais
  appartiennent au rapport, pas à l'entrepôt.
- Les **tables de mesures** et sélecteurs DAX : remplacés par le format long de `mart_kpi` (filtrer sur `kpi` suffit pour un
  sélecteur d'indicateur).

→ Suite : [5. Power BI — modèle et rapports](05-power-bi.md)
