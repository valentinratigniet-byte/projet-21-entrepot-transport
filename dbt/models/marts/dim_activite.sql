select activite_cd, activite_libelle, type_activite, type_activite || ' ' || activite_cd as activite_complete
from {{ ref('ref_activite') }}
