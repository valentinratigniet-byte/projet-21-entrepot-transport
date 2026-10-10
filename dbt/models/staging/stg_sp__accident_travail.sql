select cast(cast("Date" as timestamp) as date) as date_accident, {{ matricule('Matricule') }} as matricule,
       "Type accident" as type_accident,
       cast(cast("Jours d'arrêt" as double) as integer) as jours_arret,   -- vide = non renseigné (traité à 0 dans les KPI)
       "Activité" as activite_cd
from ({{ latest_snapshot(source('sharepoint', 'accidents_travail')) }})
