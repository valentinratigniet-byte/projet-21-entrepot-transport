-- Coût standard en charge (barème annuel) et écart de chaque voyage à la médiane de sa relation
with v as (
    select v.*,
        v.date_livre <= {{ as_of() }}                                              as est_realise,
        coalesce(v.mcv_marge_lissee, v.mcv_marge)                                  as mcv_marge_retenue,
        v.mcv_peage_charge + v.mcv_peage_vide + v.mcv_ecot_charge + v.mcv_ecot_vide as autoroute_eur,
        v.mcv_peage_charge + v.mcv_ecot_charge                                     as peage_ecot_charge,
        v.km_vide * 1.4                                                            as km_vide_eur,   -- coût forfaitaire du km à vide (règle métier)
        (v.tps_cond_charge_h + v.tps_charge_h + v.tps_livre_h) * s.cout_chauffeur_heure
          + v.km_charge * (s.cout_gazole_adblue_km + s.cout_maintenance_parc_km + s.cout_pneus_km)
          + v.mcv_peage_charge + v.mcv_ecot_charge                                 as cout_total_charge,
        case when v.est_livraison_samedi then 82 end                               as samedi_a_facturer_eur
    from {{ ref('int_voyage_courant') }} v
    left join {{ ref('stg_sp__cout_standard') }} s on s.annee = year(v.date_charge)
), med as (
    select relation_cd,
        median(ca_reparti) as med_ca, median(cout_total_charge) as med_cout, median(km_charge) as med_km,
        median(peage_ecot_charge) as med_peage, median(tps_charge_h) as med_tps_charge,
        median(tps_cond_charge_h) as med_tps_cond, median(tps_livre_h) as med_tps_livre
    from v where statut = 'LIVRE' and relation_cd is not null group by 1
)
select v.*,
    v.ca_reparti - m.med_ca              as ecart_ca_reparti,
    v.cout_total_charge - m.med_cout     as ecart_cout_total_charge,
    v.km_charge - m.med_km               as ecart_km_charge,
    v.peage_ecot_charge - m.med_peage    as ecart_peage_ecot_charge,
    v.tps_charge_h - m.med_tps_charge    as ecart_tps_charge,
    v.tps_cond_charge_h - m.med_tps_cond as ecart_tps_cond_charge,
    v.tps_livre_h - m.med_tps_livre      as ecart_tps_livre,
    case when (select count(*) from v p where p.relation_cd = v.relation_cd and p.statut = 'LIVRE'
        and p.date_charge between v.date_charge - 90 and v.date_charge - 1) >= 5 then 'Oui' else 'Non' end as au_moins_5_transports_90j,
    -- règle métier : anomalie si la valeur sort de [0,5 ; 1,75] x la médiane de la relation
    case when v.tps_cond_charge_h <= m.med_tps_cond * 0.5 or v.tps_cond_charge_h >= m.med_tps_cond * 1.75 then 'Oui' else 'Non' end
        as anomalie_tps_cond_charge,
    case when v.km_charge <= m.med_km * 0.5 or v.km_charge >= m.med_km * 1.75 then 'Oui' else 'Non' end as anomalie_km_charge,
    v.cmr = v.tete_lot_cmr as est_tete_de_lot,
    -- temps sur site (chargement + livraison) ; franchise du contrat type citerne : 1 h 30 par opération sur plage horaire
    v.tps_charge_h + v.tps_livre_h as temps_sur_site_h,
    v.tps_charge_h + v.tps_livre_h > 3 as est_hors_franchise
from v left join med m using (relation_cd)
