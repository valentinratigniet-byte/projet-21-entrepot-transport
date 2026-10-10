-- Grain : ligne d'OT (pièce, main d'oeuvre, prestation externe), avec les attributs de l'OT
select l.ligne_id, l.type_ligne, l.libelle, l.quantite, l.montant, l.matricule_mecanicien,
       o.ot_id, o.date_ot, o.tracteur_num, o.famille, o.raison, o.type_document, o.est_externe, o.fournisseur, o.demandeur,
       o.motif_sous_traitance, o.num_facture_interne, o.num_facture, o.matricule_responsable,
       o.matricule_responsable is not null as est_casse_interne, f.compte_dans_sous_traitance, m.mecanicien
from {{ ref('stg_tms__atelier_ligne') }} l
join {{ ref('stg_tms__atelier_ot') }} o using (ot_id)
left join {{ ref('ref_famille_atelier') }} f using (famille)
left join (select distinct matricule_mecanicien, mecanicien from {{ ref('stg_erp__heures_mecanicien') }}) m using (matricule_mecanicien)
