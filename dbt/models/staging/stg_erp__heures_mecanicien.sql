with src as ({{ dedup(source('erp', 'heuresmec'), 'MATRICULE, ANNEE, MOIS') }})
select cast(MATRICULE as integer) as matricule_mecanicien, upper(trim(NOM)) || ' ' || trim(PRENOM) as mecanicien,
       make_date(cast(ANNEE as integer), cast(MOIS as integer), 1) as mois, {{ nombre_fr('HM_PAYEES') }} as heures_payees
from src
