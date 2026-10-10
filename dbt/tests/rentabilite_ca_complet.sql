-- Le CA ventilé par tracteur et par conducteur retombe exactement sur le CA des voyages livrés
with v as (select sum(ca_facture) as ca from {{ ref('fct_voyage') }} where statut = 'LIVRE' and date_charge <= {{ as_of() }}),
     t as (select sum(ca) as ca from {{ ref('fct_rentabilite_tracteur_mois') }}),
     c as (select sum(ca) as ca from {{ ref('fct_rentabilite_conducteur_mois') }})
select * from v, t, c where abs(v.ca - t.ca) > 0.01 or abs(v.ca - c.ca) > 0.01
