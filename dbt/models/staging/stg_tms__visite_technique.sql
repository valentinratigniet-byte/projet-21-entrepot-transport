with src as ({{ dedup(source('tms', 'visite_technique'), 'ot_id') }})
select cast(ot_id as integer) as ot_id, cast(date_visite as date) as date_visite, cast(tracteur as integer) as tracteur_num,
       type_visite,
       resultat                              as resultat_brut,
       upper(trim(resultat)) = 'VALIDE'      as est_valide   -- 'Valide', 'valide ', 'VALIDE' = même résultat
from src
