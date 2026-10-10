-- Les tables alimentées lot par lot doivent être identiques à un recalcul complet depuis le staging
-- (le staging est une vue qui relit tout RAW) : aucune ligne en trop, en moins ou différente.
with inc as (select voyage_id, updated_at, ca_facture, statut from {{ ref('int_voyage_courant') }}),
     full_ as (select voyage_id, updated_at, ca_facture, statut from {{ ref('stg_tms__voyage') }}),
     pinc as (select pointage_id, heures, statut_validation, lot_import from {{ ref('fct_pointage') }}),
     pfull as (select pointage_id, heures, statut_validation, lot_import from {{ ref('stg_erp__pointage') }})
select 'voyage en trop' as ecart, voyage_id as cle from (select * from inc except select * from full_)
union all select 'voyage manquant', voyage_id from (select * from full_ except select * from inc)
union all select 'pointage en trop', pointage_id from (select * from pinc except select * from pfull)
union all select 'pointage manquant', pointage_id from (select * from pfull except select * from pinc)
