{# Schémas lisibles : staging / intermediate / marts / referentiel (pas main_staging) #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ custom_schema_name if custom_schema_name else target.schema }}
{%- endmacro %}

{% macro as_of() -%} cast('{{ var("as_of") }}' as date) {%- endmacro %}

{# Imports avec recouvrement : on garde la version du lot le plus récent par clé métier #}
{% macro dedup(relation, key, order_by='_batch_id desc') -%}
    select * from {{ relation }}
    qualify row_number() over (partition by {{ key }} order by {{ order_by }}) = 1
{%- endmacro %}

{# Listes / référentiels envoyés en snapshot complet : seul le dernier lot fait foi #}
{% macro latest_snapshot(relation) -%}
    select * from {{ relation }} where _batch_id = (select max(_batch_id) from {{ relation }})
{%- endmacro %}

{# AS/400 : date numérique AAAAMMJJ #}
{% macro aaaammjj(col) -%} cast(strptime(trim({{ col }}), '%Y%m%d') as date) {%- endmacro %}

{# Export en culture fr : décimale à virgule #}
{% macro nombre_fr(col) -%} cast(replace(trim({{ col }}), ',', '.') as double) {%- endmacro %}

{# Oracle/télématique : JJ/MM/AAAA #}
{% macro jjmmaaaa(col) -%} cast(strptime(trim({{ col }}), '%d/%m/%Y') as date) {%- endmacro %}

{# Matricule conforme : '000412' (paie), '0412  ' (ERP), 412 (TMS), 'C0412' (Oracle), '412.0' (Excel) -> 412 #}
{% macro matricule(col) -%}
    cast(try_cast(regexp_replace(trim(cast({{ col }} as varchar)), '^[A-Za-z]+', '') as double) as integer)
{%- endmacro %}

{# Ligne de la table KPI long format : valeur + numérateur / dénominateur pour ré-agréger proprement dans Power BI #}
{% macro kpi(domaine, nom, num, den=none, src='agg') -%}
    select '{{ domaine }}' as domaine, '{{ nom }}' as kpi, periode,
        {% if den is not none %}({{ num }}) / nullif({{ den }}, 0){% else %}{{ num }}{% endif %} as valeur,
        cast({{ num }} as double) as numerateur,
        {% if den is not none %}cast({{ den }} as double){% else %}cast(null as double){% endif %} as denominateur
    from {{ src }}
{%- endmacro %}
