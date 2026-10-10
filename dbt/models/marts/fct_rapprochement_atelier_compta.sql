-- Remplace les ~40 mesures DAX de la table DAX d'identifiants : le statut est calculé une fois, ligne à ligne
with compta as (
    select num_facture, sum(montant_ht) as ht_compta, min(date_piece) as date_piece
    from {{ ref('stg_compta__ecriture') }} where compte = '615500' group by num_facture
), atelier as (
    select num_facture, sum(cout_total) as ht_atelier, min(date_ot) as date_ot, min(tracteur_num) as tracteur_num
    from {{ ref('stg_tms__atelier_ot') }} where num_facture is not null group by num_facture
)
select coalesce(c.num_facture, a.num_facture) as num_facture, a.tracteur_num, a.date_ot, c.date_piece,
       coalesce(a.date_ot, c.date_piece) as date_reference,
       a.ht_atelier, c.ht_compta, round(c.ht_compta - a.ht_atelier, 2) as ecart_ht,
       case when a.num_facture is null then 'Absent Atelier'
            when c.num_facture is null then 'Absent Comptable'
            when round(c.ht_compta - a.ht_atelier, 2) <> 0 then 'Ecart montant'
            else 'Ok' end as statut
from compta c full outer join atelier a using (num_facture)
