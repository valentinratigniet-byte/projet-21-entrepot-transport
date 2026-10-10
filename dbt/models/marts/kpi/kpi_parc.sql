with agg as (
    select p.periode, j.jours_ouvres,
        count(a.tracteur_num) filter (where not a.est_maintenance) as jours_tracteur_actifs,
        count(a.tracteur_num) filter (where a.est_maintenance)     as jours_maintenance,
        count(distinct a.matricule) filter (where not a.est_maintenance) as nb_conducteurs
    from {{ ref('int_periode') }} p
    join {{ ref('int_periode_jours_ouvres') }} j using (periode)
    left join {{ ref('fct_affectation_jour') }} a on a.date_jour between p.d0 and p.d1
    group by all
)
{{ kpi('parc', 'nb_tracteurs_moyen_jour', 'jours_tracteur_actifs', 'jours_ouvres') }}
union all {{ kpi('parc', 'jours_tracteur_maintenance', 'jours_maintenance') }}
union all {{ kpi('parc', 'nb_conducteurs_actifs', 'nb_conducteurs') }}
