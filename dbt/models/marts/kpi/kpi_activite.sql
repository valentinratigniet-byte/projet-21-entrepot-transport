with agg as (
    select p.periode, j.jours_ouvres,
        coalesce(sum(v.ca_facture) filter (where v.est_realise), 0)               as ca_facture,
        count(v.voyage_id)                                                         as nb_voyages,
        sum(v.mcv_marge_retenue) filter (where v.relation_cd is not null)          as mcv,
        sum(v.ca_reparti) filter (where v.relation_cd is not null)                 as ca_reparti_relation,
        sum(v.km_charge) as km_charge, sum(v.km_total) as km_total, sum(v.autoroute_eur) as autoroute,
        sum(v.ca_facture) as ca_tout, sum(v.tps_total_h) as heures, coalesce(sum(v.km_vide_eur), 0) as km_vide_eur
    from {{ ref('int_periode') }} p
    join {{ ref('int_periode_jours_ouvres') }} j using (periode)
    left join {{ ref('fct_voyage') }} v on v.date_livre between p.d0 and p.d1 and v.statut <> 'ANNULE'
    group by p.periode, j.jours_ouvres
)
{{ kpi('activite', 'ca_facture', 'ca_facture') }}
union all {{ kpi('activite', 'nb_voyages', 'nb_voyages') }}
union all {{ kpi('activite', 'mcv_pct', 'mcv', 'ca_reparti_relation') }}
union all {{ kpi('activite', 'appairage', 'km_charge', 'km_total') }}
union all {{ kpi('activite', 'autoroute_eur_100km', 'autoroute * 100', 'km_total') }}
union all {{ kpi('activite', 'ca_par_km', 'ca_tout', 'km_total') }}
union all {{ kpi('activite', 'ca_par_heure', 'ca_tout', 'heures') }}
union all {{ kpi('activite', 'ca_moyen_jour_ouvre', 'ca_facture', 'jours_ouvres') }}
union all {{ kpi('activite', 'km_vide_eur', 'km_vide_eur') }}
