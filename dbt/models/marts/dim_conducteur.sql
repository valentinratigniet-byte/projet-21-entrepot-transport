-- Référentiel unique : le matricule est conformé (int) quelle que soit sa forme dans la source
select c.matricule, c.matricule_oracle, c.nom, c.prenom, c.nom || ' ' || c.prenom as nom_complet,
       c.activite_cd, a.activite_libelle, a.type_activite, c.departement, c.code_effectif, c.type_contrat, c.base_mensuelle, c.date_entree, c.date_sortie,
       c.date_sortie is null or c.date_sortie > {{ as_of() }} as est_actif
from {{ ref('stg_telem__conducteur') }} c
left join {{ ref('ref_activite') }} a using (activite_cd)
