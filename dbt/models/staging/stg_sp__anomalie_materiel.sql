-- La colonne date mélange de vraies dates Excel et du texte JJ/MM/AAAA saisi à la main
select cast(cast(ID as double) as integer) as anomalie_id,
       cast(coalesce(try_strptime("Date signalement", '%Y-%m-%d %H:%M:%S'), try_strptime("Date signalement", '%d/%m/%Y')) as date) as date_signalement,
       cast(cast(Tracteur as double) as integer) as tracteur_num, "Type anomalie" as type_anomalie, Statut as statut,
       cast(coalesce(try_strptime("Date traitement", '%Y-%m-%d %H:%M:%S'), try_strptime("Date traitement", '%Y-%m-%d')) as date) as date_traitement,
       "Déclarant" as declarant, "Détail" as detail, "Activité" as activite_cd, URL as url
from ({{ latest_snapshot(source('sharepoint', 'anomalies_materiel')) }})
