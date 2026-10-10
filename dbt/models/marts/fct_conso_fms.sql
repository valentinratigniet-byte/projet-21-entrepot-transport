select *, conso_totale_l * 100 / nullif(distance_km, 0) as conso_l100 from {{ ref('stg_telem__conso_fms') }}
