with p as (select * from {{ ref('int_periode') }}),
chrono as (
    select p.periode, sum(c.heures_hors_conduite) as hchc, sum(c.heures_conduite) as conduite, sum(c.heures_service) as service
    from p left join {{ ref('fct_chrono_jour') }} c on c.date_jour between p.d0 and p.d1 group by 1
), voy as (
    select p.periode, count(v.voyage_id) as nb_voyages
    from p left join {{ ref('fct_voyage') }} v on v.date_charge between p.d0 and p.d1 and v.statut = 'LIVRE' group by 1
), pt as (  -- définition unique (celle du TBE) : pointages valides et saisis par l'exploitation
    select p.periode,
        coalesce(sum(t.heures) filter (where t.categorie_hchc = 'a_justifier'), 0)             as a_justifier,
        coalesce(sum(t.heures) filter (where t.categorie_hchc = 'chargement_dechargement'), 0) as charg_dech,
        coalesce(sum(t.heures) filter (where t.categorie_hchc = 'decroche_raccroche'), 0)      as decro_racc
    from p left join {{ ref('fct_pointage') }} t
        on t.date_pointage between p.d0 and p.d1 and t.est_valide and t.est_saisie_exploitation
    group by 1
), cpt as (  -- règle métier : à partir du 10 du mois, le mois précédent est clos
    select p.periode, sum(c.heures_compensees) as compensees   -- vide tant qu'aucun mois n'est clos
    from p left join {{ ref('fct_compteur_mois') }} c on c.mois between p.d0 and p.d1
        and c.mois < case when day({{ as_of() }}) >= 10 then date_trunc('month', {{ as_of() }})
                          else date_trunc('month', {{ as_of() }}) - interval 1 month end
    group by 1
), agg as (
    select * from chrono join voy using (periode) join pt using (periode) join cpt using (periode)
), proj as (  -- projection de fin de mois (mois de as_of uniquement)
    select strftime({{ as_of() }}, '%Y-%m') as periode,
        (select sum(heures_service) from {{ ref('fct_chrono_jour') }}
          where date_jour between date_trunc('month', {{ as_of() }}) and {{ as_of() }} - 1) as h_real,
        (select count(distinct date_jour) from {{ ref('fct_chrono_jour') }}
          where date_jour between date_trunc('month', {{ as_of() }}) and {{ as_of() }} - 1) as nb_jours,
        (select count(*) from {{ ref('dim_date') }} where date_jour between {{ as_of() }} and last_day({{ as_of() }})
            and jour_semaine < 6) as restants_semaine,          -- NETWORKDAYS() de départ : ignore les fériés
        (select count(*) from {{ ref('dim_date') }} where date_jour between {{ as_of() }} and last_day({{ as_of() }})
            and est_jour_ouvre) as restants_ouvres
)
{{ kpi('heures', 'hchc_heures', 'hchc') }}
union all {{ kpi('heures', 'hchc_par_voyage', 'hchc', 'nb_voyages') }}
union all {{ kpi('heures', 'heures_a_justifier', 'a_justifier') }}
union all {{ kpi('heures', 'heures_chargement_dechargement', 'charg_dech') }}
union all {{ kpi('heures', 'heures_decroche_raccroche', 'decro_racc') }}
union all {{ kpi('heures', 'productivite_tc_ts', 'conduite', 'service') }}
union all {{ kpi('heures', 'heures_compensees', 'compensees') }}
union all {{ kpi('heures', 'heures_realisees_mtd', 'h_real', src='proj') }}
union all {{ kpi('heures', 'projection_fin_mois', 'h_real + h_real / nb_jours * restants_semaine', src='proj') }}
union all {{ kpi('heures', 'projection_fin_mois_hors_feries', 'h_real + h_real / nb_jours * restants_ouvres', src='proj') }}
