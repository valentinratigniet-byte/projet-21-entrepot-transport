with p as (select * from {{ ref('int_periode') }}),
pr as (
    select p.periode, coalesce(sum(x.quantite_litres), 0) as litres, sum(x.montant_eur) as montant
    from p left join {{ ref('fct_prelevement_carburant') }} x on x.date_prelevement between p.d0 and p.d1 and x.est_prelevement_reel
    group by 1
), f as (
    select p.periode, avg(c.conso_l100) as moy_ratios, sum(c.conso_totale_l) * 100 as conso, sum(c.distance_km) as dist
    from p left join {{ ref('fct_conso_fms') }} c on c.date_jour between p.d0 and p.d1 group by 1
), agg as (select * from pr join f using (periode))
{{ kpi('carburant', 'volume_litres', 'litres') }}
union all {{ kpi('carburant', 'prix_moyen_litre', 'montant', 'litres') }}
union all {{ kpi('carburant', 'conso_moyenne_l100', 'moy_ratios') }}
union all {{ kpi('carburant', 'conso_ponderee_l100', 'conso', 'dist') }}
