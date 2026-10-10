select cast(cast("Date" as timestamp) as date) as date_anomalie, "Type d'anomalies" as type_anomalie, "Activité" as activite_cd
from ({{ latest_snapshot(source('sharepoint', 'anomalies_qhse')) }})
