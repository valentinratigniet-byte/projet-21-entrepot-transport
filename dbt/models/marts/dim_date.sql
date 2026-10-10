-- Calendrier du 01/01/2023 à la fin de l'année de as_of. Les indicateurs « relatifs » (semaine en cours, 12 mois glissants...) sont calculés
-- par rapport à as_of et non à TODAY() : un rapport rejoué affiche toujours la même chose.
with d as (
    select cast(t.d as date) as date_jour, f.libelle as jour_ferie
    from generate_series(date '2023-01-01', date_trunc('year', {{ as_of() }}) + interval 1 year - interval 1 day, interval 1 day) t(d)
    left join {{ ref('jours_feries') }} f on f.date_ferie = cast(t.d as date)
)
select
    date_jour,
    year(date_jour)                                                         as annee,
    month(date_jour)                                                        as mois,
    strftime(date_jour, '%Y-%m')                                            as annee_mois,
    ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'][month(date_jour)]
        || ' ' || year(date_jour)                                           as mois_annee,
    ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'][month(date_jour)]
                                                                            as nom_mois,
    quarter(date_jour)                                                      as trimestre,
    'T' || quarter(date_jour)                                               as nom_trimestre,
    'T' || quarter(date_jour) || ' ' || year(date_jour)                     as trimestre_annee,
    weekofyear(date_jour)                                                   as semaine,
    yearweek(date_jour)                                                     as annee_semaine_num,
    isoyear(date_jour) || '-S' || lpad(cast(weekofyear(date_jour) as varchar), 2, '0') as annee_semaine,
    'S' || lpad(cast(weekofyear(date_jour) as varchar), 2, '0') || ' ' || isoyear(date_jour) as semaine_affichage,
    isodow(date_jour)                                                       as jour_semaine,
    ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'][isodow(date_jour)] as nom_jour,
    jour_ferie,
    jour_ferie is not null                                                  as est_ferie,
    isodow(date_jour) < 6 and jour_ferie is null                            as est_jour_ouvre,
    date_jour <= {{ as_of() }}                                               as est_passe,
    date_jour between {{ as_of() }} - interval 12 month and {{ as_of() }}     as est_12_mois_glissants,
    date_jour <= {{ as_of() }} and yearweek(date_jour) = yearweek({{ as_of() }}) as est_semaine_en_cours,
    date_jour between {{ as_of() }} - interval 27 day and {{ as_of() }}       as est_4_dernieres_semaines,
    year(date_jour) = year({{ as_of() }})                                    as est_annee_en_cours,
    date_trunc('month', date_jour) = date_trunc('month', {{ as_of() }})      as est_mois_en_cours,
    case when date_jour <= {{ as_of() }} and yearweek(date_jour) = yearweek({{ as_of() }}) then 'oui' else 'non' end as semaine_en_cours,
    case when weekofyear(date_jour) = weekofyear({{ as_of() }}) then 'non' else 'oui' end as hors_semaine_en_cours,
    case when date_jour between {{ as_of() }} - interval 27 day and {{ as_of() }} then 'oui' else 'non' end as quatre_dernieres_semaines,
    case when date_jour between {{ as_of() }} - interval 12 month and {{ as_of() }} then '12 mois glissants' else 'Non' end as periode_12_mois,
    case when date_jour <= {{ as_of() }} then 1 else 0 end as passe,
    case when date_jour <= {{ as_of() }} then 'Oui' else 'Non' end as date_passee
from d
