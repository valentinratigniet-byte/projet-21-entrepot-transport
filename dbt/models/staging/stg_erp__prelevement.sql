with src as ({{ dedup(source('erp', 'prelevement'), 'CB_DATE, NUM_TRACT, CB_POMPE') }})
select
    {{ aaaammjj('CB_DATE') }}      as date_prelevement,
    cast(CB_POMPE as integer)       as pompe_id,
    cast(NUM_TRACT as integer)       as tracteur_num,
    {{ matricule('NUM_MATR') }}      as matricule,
    {{ nombre_fr('CB_LITRES') }}       as quantite_litres,
    {{ nombre_fr('CB_MONTANT') }}      as montant_eur
from src
