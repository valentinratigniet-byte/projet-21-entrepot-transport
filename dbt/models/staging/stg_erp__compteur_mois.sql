with src as ({{ dedup(source('erp', 'compteur_paie'), 'PA_MATR, PA_ANNEE, PA_MOIS') }})
select
    {{ matricule('PA_MATR') }}                                         as matricule,
    make_date(cast(PA_ANNEE as integer), cast(PA_MOIS as integer), 1)    as mois,
    {{ nombre_fr('PA_H_REAL') }}                                        as heures_realisees,
    {{ nombre_fr('PA_H_BASE') }}                                        as heures_base,
    {{ nombre_fr('PA_H_SUP') }}                                        as heures_sup_50,
    {{ nombre_fr('PA_H_PAYEES') }}                                        as heures_payees,
    {{ nombre_fr('PA_SAL_BRUT') }}                                        as salaire_brut
from src
