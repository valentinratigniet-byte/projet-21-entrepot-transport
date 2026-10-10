-- Tracteurs et semi-remorques (référentiel TMS) ; km et heures d'usage calculés depuis les voyages
with usage as (
    select cast(tracteur_num as varchar) as code_materiel, sum(km_total) as km_parcourus, sum(tps_total_h) as heures_usage
    from {{ ref('stg_tms__voyage') }} where statut = 'LIVRE' group by 1
    union all
    select remorque, sum(km_total), sum(tps_total_h) from {{ ref('stg_tms__voyage') }} where statut = 'LIVRE' group by 1
)
select m.*, a.activite_libelle, u.km_parcourus, u.heures_usage
from {{ ref('stg_tms__materiel') }} m
left join {{ ref('ref_activite') }} a using (activite_cd)
left join usage u using (code_materiel)
