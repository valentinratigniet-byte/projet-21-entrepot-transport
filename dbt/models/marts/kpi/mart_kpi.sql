-- Table unique de tous les indicateurs, toutes périodes : la cible de Power BI et des tests de parité
{% set domaines = ['activite', 'facturation', 'heures', 'parc', 'atelier', 'rapprochement', 'carburant', 'qhse', 'absences'] %}
select k.*, p.type_periode, p.d0 as date_debut, p.d1 as date_fin
from (
    {% for d in domaines %}
    select * from {{ ref('kpi_' ~ d) }} {% if not loop.last %}union all{% endif %}
    {% endfor %}
) k
left join {{ ref('int_periode') }} p using (periode)
where k.periode <> 'total' or k.domaine in ('rapprochement', 'qhse') and k.kpi in
    ('nb_ok', 'nb_absent_atelier', 'nb_absent_comptable', 'nb_ecart_montant', 'anomalies_a_traiter')
