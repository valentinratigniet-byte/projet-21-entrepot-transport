select Indicateur as indicateur, "Activité" as activite_cd, cast(cast("Année" as double) as integer) as annee,
       cast(Objectif as double) as objectif
from ({{ latest_snapshot(source('sharepoint', 'objectifs')) }})
