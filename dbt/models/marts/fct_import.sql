-- Journal des imports (un enregistrement par lot et par table source)
select batch_id as lot, cutoff as date_lot, schema_name as schema_raw, table_name as table_source, rows_loaded as lignes, source
from {{ source('meta', 'import_log') }}
