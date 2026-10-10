select ville, code_postal, departement, pays, cast(latitude as double) as latitude, cast(longitude as double) as longitude
from ({{ latest_snapshot(source('tms', 'ville')) }})
