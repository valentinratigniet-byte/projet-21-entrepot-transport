-- Version courante de chaque voyage, mise à jour lot par lot (CDC incrémental) :
-- un nouveau lot n'apporte que les voyages créés ou modifiés depuis le précédent ; delete+insert sur voyage_id
-- remplace l'ancienne version. Le test `incremental_egal_recalcul_complet` prouve l'égalité avec un recalcul complet.
{{ config(materialized='incremental', unique_key='voyage_id', incremental_strategy='delete+insert', schema='intermediate') }}
select * from {{ ref('stg_tms__voyage') }}
{% if is_incremental() %}
where lot_import > (select coalesce(max(lot_import), 0) from {{ this }})
{% endif %}
