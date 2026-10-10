select cast(trim("N° voyage") as integer) as voyage_id,
       upper(trim("Justifié")) = 'OUI'    as est_justifie,   -- 'Oui', 'oui', 'OUI ' saisis à la main
       nullif(trim(Commentaire), '')      as commentaire
from ({{ latest_snapshot(source('sharepoint', 'justif_attentes')) }})
