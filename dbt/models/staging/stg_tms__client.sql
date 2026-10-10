select client_cd, client_nom, client_ville, client_pays
from ({{ latest_snapshot(source('tms', 'client')) }})
