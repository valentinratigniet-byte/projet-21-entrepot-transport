with p as (select * from {{ ref('int_periode') }}),
ot as (
    select p.periode, coalesce(sum(o.cout_total), 0) as cout,
        coalesce(sum(o.cout_total) filter (where o.est_externe and o.compte_dans_sous_traitance), 0) as cout_st,
        count(o.ot_id) filter (where o.est_panne) as pannes
    from p left join {{ ref('fct_intervention_atelier') }} o on o.date_ot between p.d0 and p.d1 group by 1
), km as (
    select p.periode, sum(v.km_total) as km
    from p left join {{ ref('fct_voyage') }} v on v.date_livre between p.d0 and p.d1 and v.statut = 'LIVRE' group by 1
), vt as (
    select p.periode, count(t.ot_id) as nb_vt, count(t.ot_id) filter (where t.est_valide) as nb_vt_ok
    from p left join {{ ref('fct_visite_technique') }} t on t.date_visite between p.d0 and p.d1 group by 1
), agg as (select * from ot join km using (periode) join vt using (periode))
{{ kpi('atelier', 'cout_maintenance_100km', 'cout * 100', 'km') }}
union all {{ kpi('atelier', 'taux_sous_traitance', 'cout_st', 'cout') }}
union all {{ kpi('atelier', 'pannes_10000km', 'pannes * 10000', 'km') }}
union all {{ kpi('atelier', 'tx_reussite_vt', 'nb_vt_ok', 'nb_vt') }}
