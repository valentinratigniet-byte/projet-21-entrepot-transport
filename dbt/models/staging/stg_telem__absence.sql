with src as ({{ dedup(source('telematique', 'absences'), 'CHAUFFEUR, DATE_ABSENCE') }})
select {{ matricule('CHAUFFEUR') }} as matricule, {{ jjmmaaaa('DATE_ABSENCE') }} as date_absence, MOTIF as motif, LIBELLE as libelle_motif
from src
