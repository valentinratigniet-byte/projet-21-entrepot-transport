select p.*, f.fournisseur, f.pays, f.ville, v.latitude, v.longitude,
       p.montant_eur / nullif(p.quantite_litres, 0) as prix_litre,
       p.quantite_litres <> 0 as est_prelevement_reel   -- les saisies à 0 L sont des tests de pompe
from {{ ref('stg_erp__prelevement') }} p
left join {{ ref('stg_erp__pompe') }} f using (pompe_id)
left join {{ ref('stg_tms__ville') }} v on v.ville = f.ville
