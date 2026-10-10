-- PARAM : clé 'POMPE_GO_<n>', libellé = fournisseur (16 car.) + pays (fin de chaîne), PR_LIB2 = ville du dépôt
select
    cast(replace(PR_CLE, 'POMPE_GO_', '') as integer)   as pompe_id,
    trim(left(PR_LIB1, 16))                          as fournisseur,
    right(trim(PR_LIB1), 2)                          as pays,
    trim(PR_LIB2)                                    as ville
from ({{ latest_snapshot(source('erp', 'param')) }})
