select *, heures_base - heures_realisees as heures_compensees,
       case when heures_realisees >= 140 then '>140h' else 'Non' end as plus_de_140h from {{ ref('stg_erp__compteur_mois') }}
