-- Heures payées (paie) vs heures produites (GMAO), par mécanicien et par mois
with prod as (
    select matricule_mecanicien, date_trunc('month', date_gmao) as mois, sum(heures) as heures_produites, sum(cout) as cout_produit
    from {{ ref('stg_erp__gmao') }} group by all
)
select h.matricule_mecanicien, h.mecanicien, cast(h.mois as date) as mois, h.heures_payees,
       coalesce(p.heures_produites, 0) as heures_produites, coalesce(p.cout_produit, 0) as cout_produit
from {{ ref('stg_erp__heures_mecanicien') }} h
left join prod p on p.matricule_mecanicien = h.matricule_mecanicien and p.mois = h.mois
