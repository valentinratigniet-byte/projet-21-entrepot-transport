select cast(voyage_id as integer) as voyage_id, type_evt, cast(montant_facture as double) as montant_facture
from ({{ latest_snapshot(source('tms', 'evenement_facture')) }})
