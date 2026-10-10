with src as ({{ dedup(source('erp', 'affectation'), 'AF_DATE, AF_TRACT') }})
select
    {{ aaaammjj('AF_DATE') }}        as date_jour,
    cast(AF_TRACT as integer)        as tracteur_num,
    {{ matricule('AF_MATR') }}       as matricule,      -- vide si tracteur immobilisé
    trim(AF_ACTIV)                   as activite_cd,    -- 'MAIN' = immobilisation atelier
    trim(AF_ACTIV) = 'MAIN'          as est_maintenance
from src
