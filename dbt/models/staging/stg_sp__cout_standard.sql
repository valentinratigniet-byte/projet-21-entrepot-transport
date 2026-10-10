select cast(cast(annee as double) as integer) as annee, cast(cout_chauffeur_heure as double) as cout_chauffeur_heure,
       cast(cout_gazole_adblue_km as double) as cout_gazole_adblue_km, cast(cout_maintenance_parc_km as double) as cout_maintenance_parc_km,
       cast(cout_pneus_km as double) as cout_pneus_km
from ({{ latest_snapshot(source('sharepoint', 'couts_standards')) }})
