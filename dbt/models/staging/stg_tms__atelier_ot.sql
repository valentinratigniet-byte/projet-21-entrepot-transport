with src as ({{ dedup(source('tms', 'atelier_ot'), 'ot_id') }})
select cast(ot_id as integer) as ot_id, cast(date_ot as date) as date_ot, cast(tracteur as integer) as tracteur_num,
       famille, raison, type_document, type_document = 'Facture externe' as est_externe,
       cast(cout_pieces as double) as cout_pieces, cast(heures_mo as double) as heures_mo,
       cast(cout_mo as double) as cout_mo, cast(cout_total as double) as cout_total,
       cast(cast(num_facture as double) as integer) as num_facture,
       fournisseur, demandeur, motif_sous_traitance, num_facture_interne,
       {{ matricule('matricule_responsable') }} as matricule_responsable
from src
