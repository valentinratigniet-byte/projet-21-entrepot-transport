select client_cd, type_indexation, cast(base_pct as double) as base_pct, cast(indice_reference as double) as indice_reference,
       cast(part_gasoil as double) as part_gasoil, cast(date_reference as date) as date_reference,
       cast(date_application as date) as date_application, sur_facture, a_la_baisse, applique, nullif(commentaire, '') as commentaire
from ({{ latest_snapshot(source('tms', 'client_indexation')) }})
