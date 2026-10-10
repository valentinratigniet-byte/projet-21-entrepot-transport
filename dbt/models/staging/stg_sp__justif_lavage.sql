select trim("N° CMR") as cmr, upper(trim("Justifié")) = 'OUI' as est_justifie, nullif(trim(Commentaire), '') as commentaire
from ({{ latest_snapshot(source('sharepoint', 'justif_lavages')) }})
