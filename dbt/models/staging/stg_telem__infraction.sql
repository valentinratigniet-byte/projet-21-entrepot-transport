with src as ({{ dedup(source('telematique', 'infractions'), 'DATE_INFRACTION, MATRICULE, TYPE_INFRACTION') }})
select cast(NUM_INFRACTION as integer) as infraction_id, {{ jjmmaaaa('DATE_INFRACTION') }} as date_infraction, HEURE as heure,
       {{ matricule('MATRICULE') }} as matricule, TYPE_INFRACTION as type_infraction, cast(CLASSE as integer) as classe,
       TYPE_INFRACTION || ' (Classe ' || CLASSE || ')' as intitule,
       LIB_CUMUL_1 as intitule_cumul1, cast(VAL_CUMUL_1 as double) / 2 as cumul1_minutes,   -- stocké en demi-minutes
       LIB_CUMUL_2 as intitule_cumul2, cast(VAL_CUMUL_2 as double) / 2 as cumul2_minutes,
       case when VAL_CUMUL_1 is not null then LIB_CUMUL_1 || ' ' || cast(cast(VAL_CUMUL_1 as integer) // 120 as varchar) || ' h '
            || lpad(cast((cast(VAL_CUMUL_1 as integer) // 2) % 60 as varchar), 2, '0') end as valeur_cumul1,
       case when VAL_CUMUL_2 is not null then LIB_CUMUL_2 || ' ' || cast(cast(VAL_CUMUL_2 as integer) // 120 as varchar) || ' h '
            || lpad(cast((cast(VAL_CUMUL_2 as integer) // 2) % 60 as varchar), 2, '0') end as valeur_cumul2,
       case when HEURE between '06:00' and '20:59' then 'Jour' else 'Nuit' end as etat_heure
from src
