-- Ce que l'entrepôt absorbe ou corrige à chaque chargement, mesuré à partir de RAW (tout y est conservé tel quel).
-- Généré par la liste de contrôles ci-dessous : une ligne par contrôle.
select 1 as ordre, 'Import' as domaine, 'ERP - pointages' as source, 'Doublons de recouvrement' as controle, 'Fenêtre d''export avec 15 jours de recouvrement' as regle,
       cast((select count(*) from {{ source('erp', 'pointage') }}) as bigint) as lignes_brutes,
       cast((select count(*) from {{ source('erp', 'pointage') }}) - (select count(*) from {{ ref('stg_erp__pointage') }}) as bigint) as lignes_concernees, 'Dédoublonnage sur la clé métier, lot le plus récent conservé' as traitement
union all
select 2 as ordre, 'Import' as domaine, 'ERP - chronotachygraphe' as source, 'Doublons de recouvrement' as controle, 'Fenêtre d''export avec 15 jours de recouvrement' as regle,
       cast((select count(*) from {{ source('erp', 'chrono') }}) as bigint) as lignes_brutes,
       cast((select count(*) from {{ source('erp', 'chrono') }}) - (select count(*) from {{ ref('stg_erp__chrono') }}) as bigint) as lignes_concernees, 'Dédoublonnage sur conducteur + jour' as traitement
union all
select 3 as ordre, 'Import' as domaine, 'ERP - prélèvements carburant' as source, 'Doublons de recouvrement' as controle, 'Fenêtre d''export avec 15 jours de recouvrement' as regle,
       cast((select count(*) from {{ source('erp', 'prelevement') }}) as bigint) as lignes_brutes,
       cast((select count(*) from {{ source('erp', 'prelevement') }}) - (select count(*) from {{ ref('stg_erp__prelevement') }}) as bigint) as lignes_concernees, 'Dédoublonnage sur la clé métier' as traitement
union all
select 4 as ordre, 'Import' as domaine, 'Télématique - consommation FMS' as source, 'Doublons de recouvrement' as controle, 'Fenêtre d''export avec 7 jours de recouvrement' as regle,
       cast((select count(*) from {{ source('telematique', 'conso_fms') }}) as bigint) as lignes_brutes,
       cast((select count(*) from {{ source('telematique', 'conso_fms') }}) - (select count(*) from {{ ref('stg_telem__conso_fms') }}) as bigint) as lignes_concernees, 'Dédoublonnage sur tracteur + jour' as traitement
union all
select 5 as ordre, 'Import' as domaine, 'TMS - voyages' as source, 'Versions successives (CDC)' as controle, 'Un voyage modifié est réexporté à chaque modification' as regle,
       cast((select count(*) from {{ source('tms', 'voyage') }}) as bigint) as lignes_brutes,
       cast((select count(*) from {{ source('tms', 'voyage') }}) - (select count(*) from {{ ref('stg_tms__voyage') }}) as bigint) as lignes_concernees, 'Seule la dernière version (updated_at) est gardée' as traitement
union all
select 7 as ordre, 'Conformité' as domaine, 'ERP - pointages' as source, 'Matricule non conforme' as controle, 'Matricule sur 6 caractères complété d''espaces (ERP), de zéros (paie) ou préfixé C (télématique)' as regle,
       cast((select count(*) from {{ source('erp', 'pointage') }}) as bigint) as lignes_brutes,
       cast((select count(*) from {{ source('erp', 'pointage') }} where NUM_MATR <> trim(NUM_MATR) or NUM_MATR like '0%') as bigint) as lignes_concernees, 'Matricule conformé en entier (macro matricule)' as traitement
union all
select 8 as ordre, 'Conformité' as domaine, 'ERP - pointages' as source, 'Libellé en double orthographe' as controle, '« Decrochage » sans accent' as regle,
       cast((select count(*) from {{ ref('stg_erp__pointage') }}) as bigint) as lignes_brutes,
       cast((select count(*) from {{ ref('stg_erp__pointage') }} where trim(libelle_brut) = 'Decrochage') as bigint) as lignes_concernees, 'Rattaché à « Décrochage » par la table des libellés' as traitement
union all
select 9 as ordre, 'Conformité' as domaine, 'ERP - activités conducteurs' as source, 'Date au jour « 00 »' as controle, 'Date AAAAMM00 saisie en paie' as regle,
       cast((select count(*) from {{ source('erp', 'activite_chauffeur') }}) as bigint) as lignes_brutes,
       cast((select count(*) from {{ source('erp', 'activite_chauffeur') }} where right(trim(FR_DATE), 2) = '00') as bigint) as lignes_concernees, 'Ramenée au 1er du mois' as traitement
union all
select 10 as ordre, 'Conformité' as domaine, 'TMS - visites techniques' as source, 'Résultat saisi librement' as controle, '« valide », « VALIDE » au lieu de « Valide »' as regle,
       cast((select count(*) from {{ ref('stg_tms__visite_technique') }}) as bigint) as lignes_brutes,
       cast((select count(*) from {{ ref('stg_tms__visite_technique') }} where resultat_brut not in ('Valide', 'Refus')) as bigint) as lignes_concernees, 'Comparaison sur upper(trim()) : comptées comme réussies' as traitement
union all
select 11 as ordre, 'Conformité' as domaine, 'SharePoint - justifications d''attente' as source, 'Oui / Non saisi librement' as controle, '« oui », « OUI », espaces' as regle,
       cast((select count(*) from {{ source('sharepoint', 'justif_attentes') }}) as bigint) as lignes_brutes,
       cast((select count(*) from {{ source('sharepoint', 'justif_attentes') }} where "Justifié" not in ('Oui', 'Non')) as bigint) as lignes_concernees, 'Normalisé en booléen' as traitement
union all
select 12 as ordre, 'Conformité' as domaine, 'SharePoint - anomalies matériel' as source, 'Dates en deux formats' as controle, 'Date Excel ou texte JJ/MM/AAAA' as regle,
       cast((select count(*) from {{ source('sharepoint', 'anomalies_materiel') }}) as bigint) as lignes_brutes,
       cast((select count(*) from {{ source('sharepoint', 'anomalies_materiel') }} where "Date signalement" like '__/__/____') as bigint) as lignes_concernees, 'Les deux formats sont convertis' as traitement
union all
select 13 as ordre, 'Rapprochement' as domaine, 'Atelier / comptabilité' as source, 'Facture absente en comptabilité' as controle, 'Facture externe sans écriture' as regle,
       cast((select count(*) from {{ ref('fct_rapprochement_atelier_compta') }}) as bigint) as lignes_brutes,
       cast((select count(*) from {{ ref('fct_rapprochement_atelier_compta') }} where statut = 'Absent Comptable') as bigint) as lignes_concernees, 'Signalée (rapport Rapprochement)' as traitement
union all
select 14 as ordre, 'Rapprochement' as domaine, 'Atelier / comptabilité' as source, 'Écart de montant' as controle, 'Montant HT différent entre atelier et comptabilité' as regle,
       cast((select count(*) from {{ ref('fct_rapprochement_atelier_compta') }}) as bigint) as lignes_brutes,
       cast((select count(*) from {{ ref('fct_rapprochement_atelier_compta') }} where statut = 'Ecart montant') as bigint) as lignes_concernees, 'Signalé (rapport Rapprochement)' as traitement
union all
select 15 as ordre, 'Historique' as domaine, 'Télématique - conducteurs' as source, 'Changements de contrat observés' as controle, 'Photo du référentiel conservée à chaque lot' as regle,
       cast((select count(*) from {{ source('telematique', 'conducteurs') }}) as bigint) as lignes_brutes,
       cast((select count(*) from {{ ref('dim_conducteur_historique') }} where not est_version_courante) as bigint) as lignes_concernees, 'Historisés (SCD2) dans dim_conducteur_historique' as traitement
