with src as ({{ dedup(source('erp', 'pointage'), 'PT_SEQ') }})
select
    cast(PT_SEQ as integer)               as pointage_id,
    {{ aaaammjj('PT_DATE') }}               as date_pointage,
    {{ matricule('NUM_MATR') }}              as matricule,
    cast(NUM_TRACT as integer)               as tracteur_num,
    trim(PT_LIBACT)                          as libelle_brut,
    cast(PT_DUREE_S as integer) / 3600.0      as heures,
    trim(PT_TYPE)                           as type_saisie,        -- E/S = exploitation, M = correction manuelle
    trim(PT_STATUT)                          as statut_validation,  -- V validé, F forfait, A annulé
    trim(PT_EXCLU) <> ''                    as est_exclu,
    trim(PT_FORFAIT) = 'F'                     as est_forfait,
    cast(PT_VALFORF as integer) / 3600.0       as heures_forfait,
    cast(_batch_id as integer)               as lot_import
from src
