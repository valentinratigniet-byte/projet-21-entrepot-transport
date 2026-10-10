with src as ({{ dedup(source('telematique', 'conso_fms'), 'TRACTEUR, DATE_JOUR') }})
select cast(TRACTEUR as integer) as tracteur_num, {{ jjmmaaaa('DATE_JOUR') }} as date_jour, {{ matricule('MATRICULE') }} as matricule,
       cast(DISTANCE_KM as double) as distance_km, cast(LITRES_CONDUITE as double) as conso_conduite_l,
       cast(LITRES_TOTAL as double) as conso_totale_l, cast(LITRES_PTO as double) as conso_pto_l, cast(CO2 as double) as co2_kg
from src
