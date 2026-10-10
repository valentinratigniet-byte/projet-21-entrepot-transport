with src as ({{ dedup(source('compta', 'ecriture'), 'ecriture_id') }})
select cast(ecriture_id as integer) as ecriture_id, cast(date_piece as date) as date_piece, num_piece,
       cast(substr(num_piece, 3) as integer) as num_facture,   -- 'FA0070001' -> 70001, clé commune avec l'atelier
       compte, cast(montant_debit as double) - cast(montant_credit as double) as montant_ht, libelle,
       journal, compte_tiers, intitule_tiers, code_analytique, libelle_analytique, code_frais, libelle_frais, societe,
       cloture = 'Oui' as est_cloture
from src
