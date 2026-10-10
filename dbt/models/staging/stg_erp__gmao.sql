with src as ({{ dedup(source('erp', 'gmao'), 'GM_DATE, GM_MECA, GM_ARTICLE, GM_COUT, GM_HEURES') }})
select {{ aaaammjj('GM_DATE') }} as date_gmao, cast(GM_MECA as integer) as matricule_mecanicien, trim(GM_ARTICLE) as article,
       {{ nombre_fr('GM_COUT') }} as cout, {{ nombre_fr('GM_HEURES') }} as heures
from src
