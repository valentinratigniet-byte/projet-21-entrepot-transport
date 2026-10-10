-- Une seule version courante par conducteur, et des périodes de validité qui ne se chevauchent pas
select matricule from {{ ref('dim_conducteur_historique') }}
group by matricule having sum(case when est_version_courante then 1 else 0 end) <> 1
union all
select a.matricule from {{ ref('dim_conducteur_historique') }} a
join {{ ref('dim_conducteur_historique') }} b on a.matricule = b.matricule and a.valide_du < b.valide_du
where a.valide_au is null or a.valide_au >= b.valide_du
