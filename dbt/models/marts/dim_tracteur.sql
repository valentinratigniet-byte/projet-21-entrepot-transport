select cast(code_materiel as integer) as tracteur_num, immatriculation, marque, modele, activite_cd, activite_type,
       date_entree, compteur_km
from {{ ref('stg_tms__materiel') }} where est_tracteur
