select *, coalesce(jours_arret, 0) as jours_arret_retenus from {{ ref('stg_sp__accident_travail') }}
