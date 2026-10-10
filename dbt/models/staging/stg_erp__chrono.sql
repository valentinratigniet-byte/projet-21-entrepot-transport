with src as ({{ dedup(source('erp', 'chrono'), 'CH_DATE, CH_MATR') }})
select
    {{ aaaammjj('CH_DATE') }}             as date_jour,
    {{ matricule('CH_MATR') }}            as matricule,
    cast(CH_CONDUITE_S as integer) / 3600.0   as heures_conduite,
    cast(CH_TRAVAIL_S as integer) / 3600.0   as heures_travail,
    cast(CH_DISPO_S as integer) / 3600.0   as heures_dispo,
    cast(CH_REPOS_S as integer) / 3600.0   as heures_repos_paye,
    cast(CH_SERVICE_S as integer) / 3600.0   as heures_service
from src
