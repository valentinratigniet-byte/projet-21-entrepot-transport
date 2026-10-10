select *, heures_travail + heures_dispo + heures_repos_paye as heures_hors_conduite
from {{ ref('stg_erp__chrono') }}
