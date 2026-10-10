select ent_code as code_materiel, immat as immatriculation, type_materiel, marque, modele, activite_type, activite_cd,
       nullif(equipement, '') as equipement, cast(date_entree as date) as date_entree, cast(date_sortie as date) as date_sortie,
       statut, cast(cast(compteur_km as double) as bigint) as compteur_km, cast(date_compteur as date) as date_compteur,
       type_materiel = 'TRACTEUR' as est_tracteur
from ({{ latest_snapshot(source('tms', 'entite')) }})
