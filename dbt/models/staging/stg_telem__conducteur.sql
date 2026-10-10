select {{ matricule('MATRICULE') }} as matricule, MATRICULE as matricule_oracle,
       upper(trim(NOM)) as nom, trim(PRENOM) as prenom, ACTIVITE as activite_cd,
       {{ jjmmaaaa('DATE_ENTREE') }} as date_entree,
       case when DATE_SORTIE is not null then {{ jjmmaaaa('DATE_SORTIE') }} end as date_sortie,
       DEPARTEMENT as departement, TYPE_EFFECTIF as code_effectif,
       TYPE_CONTRAT as type_contrat, cast(BASE_MENSUELLE as double) as base_mensuelle
from ({{ latest_snapshot(source('telematique', 'conducteurs')) }})
