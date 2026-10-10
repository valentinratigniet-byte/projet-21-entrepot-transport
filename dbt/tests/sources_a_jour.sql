-- Fraîcheur : le dernier import de chaque table doit dater au plus de la veille de la date de référence.
-- (`dbt source freshness` compare à l'horloge réelle ; ici l'horloge est figée sur as_of, d'où ce test équivalent.)
select schema_name, table_name, max(cutoff) as dernier_import
from {{ source('meta', 'import_log') }}
group by 1, 2
having max(cutoff) < {{ as_of() }} - interval 1 day
