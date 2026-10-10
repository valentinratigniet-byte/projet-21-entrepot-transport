-- Prestations annexes des conducteurs (frais, heures hors carte, formation, trajets). Le jour '00' existe en source.
with src as ({{ dedup(source('erp', 'activite_chauffeur'), 'FR_DATE, FR_MATR, FR_LIBELLE, FR_COMPTE') }})
select
    make_date(cast(left(FR_DATE, 4) as integer), cast(substr(FR_DATE, 5, 2) as integer),
              greatest(cast(right(trim(FR_DATE), 2) as integer), 1))                     as date_activite,
    {{ matricule('FR_MATR') }}                                                             as matricule,
    trim(FR_PREST)                                                                         as type_prestation,
    trim(FR_COMPTE)                                                                         as nature_compte,
    trim(FR_LIBELLE)                                                                         as libelle,
    {{ nombre_fr('FR_QTE') }}                                                              as heures,
    {{ nombre_fr('FR_COUT_1') }} + {{ nombre_fr('FR_COUT_2') }} + {{ nombre_fr('FR_COUT_3') }}    as cout,
    trim(FR_VERIF) = 'N'                                                                   as est_en_attente_verification,
    trim(FR_LIBELLE) in ('Forfaitmensuel') or trim(FR_COMPTE) = '4000'                          as est_exclu
from src
