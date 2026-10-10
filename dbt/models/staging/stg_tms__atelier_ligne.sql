select cast(ligne_id as integer) as ligne_id, cast(ot_id as integer) as ot_id, type_ligne, libelle,
       cast(quantite as double) as quantite, cast(montant as double) as montant,
       cast(cast(mecanicien as double) as integer) as matricule_mecanicien
from ({{ latest_snapshot(source('tms', 'atelier_ligne')) }})
