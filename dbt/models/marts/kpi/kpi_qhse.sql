with p as (select * from {{ ref('int_periode') }}),
i as (select p.periode, count(x.matricule) as nb, count(x.matricule) filter (where x.classe = 5) as nb5
      from p left join {{ ref('fct_infraction') }} x on x.date_infraction between p.d0 and p.d1 group by 1),
a as (select p.periode, count(x.date_accident) as nb_at, coalesce(sum(x.jours_arret_retenus), 0) as jours
      from p left join {{ ref('fct_accident_travail') }} x on x.date_accident between p.d0 and p.d1 group by 1),
au as (select p.periode, coalesce(sum(x.nb_passages), 0) as passages, count(x.evenement_id) filter (where x.est_justifie) as justifies
       from p left join {{ ref('fct_autoroute_interdite') }} x on x.date_evenement between p.d0 and p.d1 group by 1),
an as (select p.periode, count(x.anomalie_id) as nb_ano,
              count(x.anomalie_id) filter (where p.periode = 'total' and x.statut = 'A traiter') as a_traiter
       from p left join {{ ref('fct_anomalie_materiel') }} x
         on (x.date_signalement between p.d0 and p.d1) or (p.periode = 'total')
       group by 1),
agg as (select * from i join a using (periode) join au using (periode) join an using (periode))
{{ kpi('qhse', 'nb_infractions', 'nb') }}
union all {{ kpi('qhse', 'nb_infractions_classe5', 'nb5') }}
union all {{ kpi('qhse', 'nb_accidents_travail', 'nb_at') }}
union all {{ kpi('qhse', 'jours_perdus', 'jours') }}
union all {{ kpi('qhse', 'passages_autoroutes_interdites', 'passages') }}
union all {{ kpi('qhse', 'evenements_autoroutes_justifies', 'justifies') }}
union all {{ kpi('qhse', 'nb_anomalies_materiel', 'nb_ano') }}
union all select 'qhse', 'anomalies_a_traiter', periode, a_traiter, a_traiter, null from agg where periode = 'total'
