-- Une seule définition des flags : chaque rapport choisit explicitement ses filtres au lieu de les réécrire en SQL
-- Incrémental : à chaque import, seuls les pointages du nouveau lot (nouveaux ou ré-exportés) sont traités.
{{ config(materialized='incremental', unique_key='pointage_id', incremental_strategy='delete+insert') }}
select p.*, r.categorie_hchc,
       not p.est_exclu and p.statut_validation in ('F', 'V')   as est_valide,
       p.type_saisie in ('E', 'S')                              as est_saisie_exploitation
from {{ ref('stg_erp__pointage') }} p
left join {{ ref('ref_libelle_pointage') }} r using (libelle_brut)
{% if is_incremental() %}
where p.lot_import > (select coalesce(max(lot_import), 0) from {{ this }})
{% endif %}
