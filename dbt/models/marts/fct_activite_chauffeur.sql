select a.*,
    case when a.libelle in ('Frais conv', 'Frais non-conv') then 'Frais'
         when a.libelle = 'Heures hors carte' then 'Hors carte'
         when a.libelle in ('Formation', 'Trajet') then a.libelle else 'Autre' end as categorie
from {{ ref('stg_erp__activite_chauffeur') }} a
where not a.est_exclu
