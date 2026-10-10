select cast(cast("ID événement" as double) as integer) as evenement_id, Justification as justification, "Validé par" as valide_par,
       nullif(Commentaire, '') as commentaire
from ({{ latest_snapshot(source('sharepoint', 'justif_autoroutes')) }})
