-- Contribution par conducteur et par mois : CA des voyages réalisés - salaire chargé - frais et activités annexes - carburant.
{% set charges_patronales = 1.45 %}
with ca as (
    select matricule, date_trunc('month', date_charge) as mois, sum(ca_facture) as ca, count(*) as nb_voyages
    from {{ ref('fct_voyage') }} where statut = 'LIVRE' and matricule is not null group by all
),
paie as (
    select matricule, date_trunc('month', mois) as mois, sum(salaire_brut) * {{ charges_patronales }} as salaire_charge,
           sum(heures_payees) as heures_payees
    from {{ ref('fct_compteur_mois') }} group by all
),
frais as (
    select matricule, date_trunc('month', date_activite) as mois, sum(cout) as frais
    from {{ ref('fct_activite_chauffeur') }} where not est_exclu group by all
),
carburant as (
    select matricule, date_trunc('month', date_prelevement) as mois, sum(montant_eur) as carburant
    from {{ ref('fct_prelevement_carburant') }} where matricule is not null group by all
),
cles as (select matricule, mois from ca union select matricule, mois from paie)
select cast(k.mois as date) as mois, k.matricule,
       coalesce(ca.ca, 0) as ca, coalesce(ca.nb_voyages, 0) as nb_voyages, coalesce(p.salaire_charge, 0) as salaire_charge,
       coalesce(p.heures_payees, 0) as heures_payees, coalesce(f.frais, 0) as frais, coalesce(c.carburant, 0) as carburant,
       coalesce(ca.ca, 0) - coalesce(p.salaire_charge, 0) - coalesce(f.frais, 0) - coalesce(c.carburant, 0) as contribution
from cles k
left join ca using (matricule, mois)
left join paie p using (matricule, mois)
left join frais f using (matricule, mois)
left join carburant c using (matricule, mois)
where k.mois <= {{ as_of() }}
