select relation_cd, client_cd, depart_ville, arrivee_ville, depart_ville || ' → ' || arrivee_ville as relation_libelle,
       depart_nom, arrivee_nom, cast(distance_km as integer) as distance_km, activite_cd, cast(prix as double) as prix_tarif,
       cast(prix_date as date) as prix_date, cast(date_creation as date) as date_creation, type_relation,
       location = '1' as est_location, marchandise
from ({{ latest_snapshot(source('tms', 'relation')) }})
