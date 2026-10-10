with agg as (
    select p.periode, j.jours_ouvres, count(distinct a.matricule) as absents, count(a.matricule) as jours
    from {{ ref('int_periode') }} p
    join {{ ref('int_periode_jours_ouvres') }} j using (periode)
    left join {{ ref('fct_absence_jour') }} a on a.date_absence between p.d0 and p.d1
    group by all
)
{{ kpi('absences', 'absents_uniques', 'absents') }}
union all {{ kpi('absences', 'jours_absence', 'jours') }}
union all {{ kpi('absences', 'jours_absence_moyen_par_jour_ouvre', 'jours', 'jours_ouvres') }}
