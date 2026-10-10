-- Historique des contrats (SCD type 2) reconstruit à partir des photos du référentiel conservées par lot dans RAW.
-- Pourquoi pas `dbt snapshot` : l'entrepôt est reconstruit en --full-refresh depuis RAW (rejouable), et RAW garde déjà
-- chaque photo. Le résultat est le même qu'un snapshot pris à chaque import, sans état caché hors du dépôt.
-- Limite assumée (la même qu'un snapshot) : un changement est daté au lot qui l'observe, pas à sa date d'effet RH.
with photos as (
    select distinct _batch_id as lot, cast(_loaded_at as date) as date_lot, {{ matricule('MATRICULE') }} as matricule,
           TYPE_CONTRAT as type_contrat, cast(BASE_MENSUELLE as double) as base_mensuelle,
           TYPE_EFFECTIF as code_effectif, ACTIVITE as activite_cd
    from {{ source('telematique', 'conducteurs') }}
),
versions as (
    select *, type_contrat || '|' || base_mensuelle || '|' || code_effectif || '|' || activite_cd as cle,
           lag(type_contrat || '|' || base_mensuelle || '|' || code_effectif || '|' || activite_cd)
               over (partition by matricule order by lot) as cle_precedente,
           min(lot) over (partition by matricule) as premier_lot
    from photos
),
changements as (
    select * from versions where cle_precedente is null or cle <> cle_precedente
)
select ch.matricule, d.nom_complet, ch.type_contrat, ch.base_mensuelle, ch.code_effectif, ch.activite_cd,
       case when ch.lot = ch.premier_lot then d.date_entree else ch.date_lot end as valide_du,
       cast(lead(ch.date_lot) over (partition by ch.matricule order by ch.lot) - interval 1 day as date) as valide_au,
       lead(ch.date_lot) over (partition by ch.matricule order by ch.lot) is null as est_version_courante,
       ch.lot as lot_observe
from changements ch
join {{ ref('dim_conducteur') }} d using (matricule)
