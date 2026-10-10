select ot_id, num_facture, date_ot as date_document, tracteur_num, fournisseur, famille, cout_total as montant_ht, 'Atelier' as provenance, '01' as societe,
       '401' || cast((select sum(ascii(substr(fournisseur, i, 1))) from range(1, length(fournisseur) + 1) t(i)) % 900 + 100 as varchar) as compte_tiers
from {{ ref('stg_tms__atelier_ot') }} where num_facture is not null
