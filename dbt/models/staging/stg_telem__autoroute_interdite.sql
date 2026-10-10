with src as ({{ dedup(source('telematique', 'autoroutes_interdites'), 'NUM_EVENEMENT') }})
select cast(NUM_EVENEMENT as integer) as evenement_id, {{ jjmmaaaa('DATE_EVENEMENT') }} as date_evenement, HEURE_EVENEMENT as heure,
       cast(TRACTEUR as integer) as tracteur_num, {{ matricule('MATRICULE') }} as matricule,
       AUTOROUTE as autoroute, ZONE as zone, cast(NB_PASSAGES as integer) as nb_passages,
       cast(LATITUDE as double) as latitude, cast(LONGITUDE as double) as longitude
from src
