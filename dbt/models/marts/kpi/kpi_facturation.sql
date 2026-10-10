with v as (
    select p.periode, v.* from {{ ref('int_periode') }} p
    left join {{ ref('fct_voyage') }} v on v.date_livre between p.d0 and p.d1 and v.statut <> 'ANNULE' and v.est_realise
), e as (
    select v.periode, e.type_evt, sum(e.montant_facture) as montant
    from v join {{ ref('fct_evenement_facture') }} e using (voyage_id) group by all
), agg as (
    select v.periode,
        coalesce(sum(v.attente_a_facturer_eur), 0)  as attente_a_facturer,
        coalesce(sum(v.mcv_lavage_int), 0)          as lavage_a_facturer,
        count(j.voyage_id) filter (where j.est_justifie) as attentes_justifiees,
        coalesce(any_value(att.montant), 0) as att_f, coalesce(any_value(lav.montant), 0) as lav_f,
        coalesce(any_value(sam.montant), 0) as sam_f, coalesce(any_value(dd.montant), 0) as dd_f
    from v
    left join {{ ref('fct_justification_attente') }} j using (voyage_id)
    left join e att on att.periode = v.periode and att.type_evt = 'ATT'
    left join e lav on lav.periode = v.periode and lav.type_evt = 'LAV'
    left join e sam on sam.periode = v.periode and sam.type_evt = 'SAM'
    left join e dd  on dd.periode  = v.periode and dd.type_evt  = 'DD'
    group by v.periode
)
{{ kpi('facturation', 'attente_a_facturer_eur', 'attente_a_facturer') }}
union all {{ kpi('facturation', 'attente_facturee_eur', 'att_f') }}
union all {{ kpi('facturation', 'pct_attente_facturee', 'att_f', 'attente_a_facturer') }}
union all {{ kpi('facturation', 'attentes_justifiees', 'attentes_justifiees') }}
union all {{ kpi('facturation', 'lavage_a_facturer_eur', 'lavage_a_facturer') }}
union all {{ kpi('facturation', 'lavage_facture_eur', 'lav_f') }}
union all {{ kpi('facturation', 'samedi_facture_eur', 'sam_f') }}
union all {{ kpi('facturation', 'double_depotage_facture_eur', 'dd_f') }}
