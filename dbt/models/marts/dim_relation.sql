select r.*, c.client_nom, r.depart_nom || ' - ' || r.arrivee_nom as relation_sites,
       d.code_postal as depart_code_postal, d.departement as depart_departement, d.pays as depart_pays,
       d.latitude as depart_latitude, d.longitude as depart_longitude,
       a.code_postal as arrivee_code_postal, a.departement as arrivee_departement, a.pays as arrivee_pays,
       a.latitude as arrivee_latitude, a.longitude as arrivee_longitude,
       date_diff('month', r.prix_date, {{ as_of() }}) as age_prix_mois
from {{ ref('stg_tms__relation') }} r
left join {{ ref('stg_tms__client') }} c using (client_cd)
left join {{ ref('stg_tms__ville') }} d on d.ville = r.depart_ville
left join {{ ref('stg_tms__ville') }} a on a.ville = r.arrivee_ville
