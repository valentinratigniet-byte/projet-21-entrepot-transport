with agg as (
    select 'total' as periode,
        count(*) filter (where statut = 'Ok')               as ok,
        count(*) filter (where statut = 'Absent Atelier')   as absent_atelier,
        count(*) filter (where statut = 'Absent Comptable') as absent_comptable,
        count(*) filter (where statut = 'Ecart montant')    as ecart
    from {{ ref('fct_rapprochement_atelier_compta') }}
)
{{ kpi('rapprochement', 'nb_ok', 'ok') }}
union all {{ kpi('rapprochement', 'nb_absent_atelier', 'absent_atelier') }}
union all {{ kpi('rapprochement', 'nb_absent_comptable', 'absent_comptable') }}
union all {{ kpi('rapprochement', 'nb_ecart_montant', 'ecart') }}
