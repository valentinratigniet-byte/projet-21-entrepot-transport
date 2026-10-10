-- Marge directe par tracteur et par mois, sur coûts RÉELS : CA - péages / écotaxe - carburant prélevé - atelier.
-- (La MCV des voyages repose sur des coûts standards ; ici chaque coût vient de son système source.)
with ca as (
    select tracteur_num, date_trunc('month', date_charge) as mois, sum(ca_facture) as ca,
           sum(mcv_peage_charge + mcv_peage_vide + mcv_ecot_charge + mcv_ecot_vide) as peages, sum(km_total) as km,
           count(*) as nb_voyages
    from {{ ref('fct_voyage') }} where statut = 'LIVRE' group by all
),
carburant as (
    select tracteur_num, date_trunc('month', date_prelevement) as mois, sum(montant_eur) as carburant
    from {{ ref('fct_prelevement_carburant') }} where tracteur_num is not null group by all
),
atelier as (
    select tracteur_num, date_trunc('month', date_ot) as mois, sum(cout_total) as atelier
    from {{ ref('fct_intervention_atelier') }} group by all
),
cles as (select tracteur_num, mois from ca union select tracteur_num, mois from carburant union select tracteur_num, mois from atelier)
select cast(k.mois as date) as mois, k.tracteur_num,
       coalesce(ca.ca, 0) as ca, coalesce(ca.peages, 0) as peages, coalesce(c.carburant, 0) as carburant,
       coalesce(a.atelier, 0) as atelier, coalesce(ca.km, 0) as km, coalesce(ca.nb_voyages, 0) as nb_voyages,
       coalesce(ca.ca, 0) - coalesce(ca.peages, 0) - coalesce(c.carburant, 0) - coalesce(a.atelier, 0) as marge_directe
from cles k
left join ca using (tracteur_num, mois)
left join carburant c using (tracteur_num, mois)
left join atelier a using (tracteur_num, mois)
where k.mois <= {{ as_of() }}
