"""Construit le modèle sémantique Power BI (format PBIP / TMDL) à partir de l'entrepôt.

1. exporte chaque table utile de l'entrepôt en Parquet (powerbi/donnees/), colonnes renommées en français ;
2. écrit le modèle TMDL (tables, colonnes typées, relations, mesures de mesures.py) dans TransVal.SemanticModel/.

Le modèle ne contient AUCUNE transformation : tout est fait dans l'entrepôt. Power Query se contente de lire
les fichiers Parquet (paramètre DossierDonnees).
"""
import os
import re
import sys
import uuid
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import WAREHOUSE  # noqa: E402
from mesures import MESURES, PARAMETRES_CHAMPS, TABLES_SELECTEURS  # noqa: E402

PBI = Path(__file__).resolve().parent
DONNEES = PBI / "donnees"
# Chemin lu par Power BI (paramètre DossierDonnees) : neutre et stable dans le dépôt (pas de chemin machine dans le TMDL),
# à surcharger localement par la variable d'environnement TRANSVAL_DONNEES, ou dans Power BI (Paramètres > DossierDonnees).
CHEMIN_POWERBI = os.environ.get("TRANSVAL_DONNEES", r"C:\TransVal\powerbi\donnees")
SM = PBI / "TransVal.SemanticModel"

# mots -> libellés français (le reste : premier mot capitalisé, '_' -> ' ')
MOTS = {"ca": "CA", "mcv": "MCV", "cmr": "CMR", "ot": "OT", "id": "ID", "co2": "CO2", "pto": "PTO", "ht": "HT", "km": "km",
        "tps": "temps", "qt": "qté", "eur": "€", "pct": "%", "l100": "L/100 km", "h": "h", "vt": "VT", "num": "n°",
        "activite": "activité", "depart": "départ", "arrivee": "arrivée", "realise": "réalisé", "realisees": "réalisées",
        "payees": "payées", "produites": "produites", "ecart": "écart", "entree": "entrée", "categorie": "catégorie",
        "periode": "période", "libelle": "libellé", "mecanicien": "mécanicien", "materiel": "matériel", "evenement": "événement",
        "debut": "début", "reference": "référence", "prelevement": "prélèvement", "quantite": "quantité", "cloture": "clôturé",
        "ecriture": "écriture", "piece": "pièce", "frais": "frais", "intitule": "intitulé", "annee": "année", "ferie": "férié",
        "ouvre": "ouvré", "passe": "passé", "derniere": "dernière", "dernieres": "dernières", "verification": "vérification",
        "exclu": "exclu", "anomalie": "anomalie", "presta": "prestation", "rupture": "rupture", "depotages": "dépôtages",
        "tete": "tête", "lot": "lot", "facturee": "facturée", "justifiee": "justifiée", "facture": "facturé", "declarant": "déclarant",
        "detail": "détail", "equipement": "équipement", "immatriculation": "immatriculation", "repos": "repos", "paye": "payé",
        "complete": "complète", "decroche": "décroche", "remorque": "remorque", "creation": "création", "age": "âge",
        "cout": "coût", "couts": "coûts", "peage": "péage", "ecot": "écotaxe", "lissee": "lissée", "depotage": "dépotage",
        "justifie": "justifié", "arret": "arrêt", "compensees": "compensées", "prenom": "prénom", "departement": "département",
        "modele": "modèle", "resultat": "résultat", "societe": "société", "applique": "appliqué", "reel": "réel",
        "numerateur": "numérateur", "denominateur": "dénominateur", "url": "URL", "hchc": "HCHC", "dd": "DD",
        "reparti": "réparti", "a": "à", "peages": "péages", "concernees": "concernées", "controle": "contrôle",
        "regle": "règle", "valide": "valide", "observe": "observé", "echecs": "échecs", "duree": "durée",
        "execute": "exécuté", "noeud": "nœud", "brutes": "brutes"}
# renommages explicites (colonne d'entrepôt -> nom Power BI)
RENOMS = {"date_jour": "Date", "num_facture": "N° facture", "num_facture_interne": "N° facture interne", "voyage_id": "N° voyage",
          "ca_facture": "CA facturé", "statut": "Statut", "matricule": "Matricule", "est_realise": "Est réalisé",
          "client_cd": "Code client", "relation_cd": "Code relation", "activite_cd": "Code activité", "date_ot": "Date OT",
          "code_materiel": "Code matériel", "tracteur_num": "N° tracteur", "nom_complet": "Conducteur", "client_nom": "Client",
          "relation_libelle": "Relation", "activite_libelle": "Activité", "kpi": "KPI", "valeur": "Valeur",
          "date_charge": "Date chargement", "date_livre": "Date livraison", "qt_livre": "Qté livrée", "qt_facture": "Qté facturée",
          "km_charge": "Km chargé", "tps_charge_h": "Temps chargement h", "tps_livre_h": "Temps livraison h",
          "tps_cond_charge_h": "Temps conduite chargé h", "mcv_peage_charge": "MCV péage chargé", "mcv_ecot_charge": "MCV écotaxe chargé",
          "peage_ecot_charge": "Péage écotaxe chargé", "cout_total_charge": "Coût total chargé", "ecart_km_charge": "Écart km chargé",
          "ecart_peage_ecot_charge": "Écart péage écotaxe chargé", "ecart_tps_charge": "Écart temps chargement",
          "ecart_tps_cond_charge": "Écart temps conduite chargé", "ecart_tps_livre": "Écart temps livraison",
          "ecart_cout_total_charge": "Écart coût total chargé", "sur_facture": "Sur facture", "type_evt": "Type événement",
          "au_moins_5_transports_90j": "Au moins 5 transports 90 j", "est_tete_de_lot": "Est tête de lot", "nb_depotages": "Nb dépotages",
          "tete_lot_cmr": "CMR tête de lot", "anomalie_km_charge": "Anomalie km chargé", "anomalie_tps_cond_charge": "Anomalie temps conduite chargé", "etat_heure": "État heure", "date_passee": "Date passée", "date_reference": "Date référence", "objectif_vl": "Objectif VL", "objectif_pu": "Objectif PU", "objectif_al": "Objectif AL", "objectif_ch": "Objectif CH", "objectif_ct": "Objectif CT", "objectif_global": "Objectif global", "est_double_depotage": "Est double dépotage", "type_activite": "Type activité",
          "salaire_charge": "Salaire chargé", "email": "E-mail", "schema_raw": "Schéma RAW", "km": "Km",
          "est_version_courante": "Version courante", "valide_du": "Valide du", "valide_au": "Valide au"}


def libelle(col):
    if col in RENOMS:
        return RENOMS[col]
    mots = [MOTS.get(m, m) for m in col.split("_")]
    if mots[0] == "est":
        mots[0] = "Est"
    txt = " ".join(mots)
    return txt[0].upper() + txt[1:]


# nom Power BI -> (requête SQL sur l'entrepôt, colonnes cachées)
TABLES = {
    "Date": ("select * from marts.dim_date", []),
    "Activité": ("select * from marts.dim_activite", []),
    "Conducteur": ("select * from marts.dim_conducteur", []),
    "Matériel": ("select * from marts.dim_materiel", []),
    "Client": ("select * from marts.dim_client", []),
    # voyages spot (sans relation tarifaire) : membre nommé plutôt qu'une ligne vide dans les rapports ; attributs renseignés
    # pour qu'aucun segment n'affiche de valeur vide (un voyage spot est ponctuel et n'est pas une location)
    "Relation": ("""select *, case when est_location then 'En location' else 'Hors location' end as location
                    from (select * exclude (client_nom) from marts.dim_relation union all by name
                    select 'SPOT' as relation_cd, 'Spot (sans relation)' as relation_libelle, 'Ponctuelle' as type_relation,
                           false as est_location, 'Non renseignée' as depart_ville, 'Non renseignée' as arrivee_ville,
                           'Non renseigné' as depart_departement, 'Non renseigné' as arrivee_departement,
                           'Non renseigné' as depart_pays, 'Non renseigné' as arrivee_pays)""", []),
    "Voyage": ("""select v.* exclude (updated_at, relation_cd), coalesce(v.relation_cd, 'SPOT') as relation_cd,
                    cast(v.tracteur_num as varchar) as code_tracteur,
                    v.attente_a_facturer_eur > 0 as est_attente, e.montant_att as attente_facturee_eur, e.montant_att is not null as est_attente_facturee,
                    coalesce(j.est_justifie, false) as est_attente_justifiee,
                    e.montant_lav is not null as est_lavage_facture, coalesce(jl.est_justifie, false) as est_lavage_justifie,
                    e.montant_sam is not null as est_samedi_facture, e.montant_dd is not null as est_dd_facture,
                    -- libellés affichés par les segments des rapports
                    case when e.montant_att is null then 'Attente devant être facturée' else 'Attente facturée' end as affichage_attente,
                    case when e.montant_lav is null then 'Lavage devant être facturé' else 'Lavage facturé' end as affichage_lavage,
                    case when e.montant_sam is null then 'Samedi devant être facturé' else 'Samedi facturé' end as affichage_samedi,
                    case when e.montant_dd is null then 'DD devant être facturé' else 'DD facturé' end as affichage_dd,
                    case when coalesce(j.est_justifie, false) then 'Attente justifié' else 'Attente non facturé justifié' end as affichage_justifie,
                    case when jl.cmr is not null then 'Lavage justifié' else 'Lavage non justifié' end as affichage_lavage_justifie,
                    case when v.attente_a_facturer_eur > 0 then 'oui' else 'non' end as attentes_oui_non
                  from marts.fct_voyage v
                  left join (select voyage_id, sum(montant_facture) filter (where type_evt = 'ATT') as montant_att,
                                    sum(montant_facture) filter (where type_evt = 'LAV') as montant_lav,
                                    sum(montant_facture) filter (where type_evt = 'SAM') as montant_sam,
                                    sum(montant_facture) filter (where type_evt = 'DD') as montant_dd
                             from marts.fct_evenement_facture group by 1) e using (voyage_id)
                  left join marts.fct_justification_attente j using (voyage_id)
                  left join marts.fct_justification_lavage jl using (cmr)
                  where v.statut <> 'ANNULE'""", ["code_tracteur"]),
    "Événement facturé": ("select * from marts.fct_evenement_facture", []),
    "Justification attente": ("select * from marts.fct_justification_attente", []),
    "Justification lavage": ("select * from marts.fct_justification_lavage", []),
    "Pointage": ("select *, cast(tracteur_num as varchar) as code_tracteur from marts.fct_pointage", ["code_tracteur"]),
    "Chrono": ("select * from marts.fct_chrono_jour", []),
    "Compteur paie": ("select * from marts.fct_compteur_mois", []),
    "Activité chauffeur": ("select * from marts.fct_activite_chauffeur", []),
    # tracteur-jour affecté à un conducteur ; les jours d'immobilisation (sans conducteur) ont leur propre table
    "Affectation": ("""select *, cast(tracteur_num as varchar) as code_tracteur from marts.fct_affectation_jour
                       where not est_maintenance""", ["code_tracteur"]),
    "Immobilisation": ("""select a.date_jour, a.tracteur_num, t.activite_cd, cast(a.tracteur_num as varchar) as code_tracteur
                          from marts.fct_affectation_jour a join marts.dim_tracteur t using (tracteur_num)
                          where a.est_maintenance""", ["code_tracteur"]),
    "Atelier": ("select *, cast(tracteur_num as varchar) as code_tracteur from marts.fct_atelier_ligne", ["code_tracteur"]),
    "Visite technique": ("select *, cast(tracteur_num as varchar) as code_tracteur from marts.fct_visite_technique", ["code_tracteur"]),
    "Heures mécanicien": ("select * from marts.fct_heures_mecanicien", []),
    "Carburant": ("select *, cast(tracteur_num as varchar) as code_tracteur from marts.fct_prelevement_carburant", ["code_tracteur"]),
    "Conso FMS": ("select *, cast(tracteur_num as varchar) as code_tracteur from marts.fct_conso_fms", ["code_tracteur"]),
    "Absence": ("select * from marts.fct_absence_jour", []),
    "Infraction": ("select * from marts.fct_infraction", []),
    "Autoroute interdite": ("select *, cast(tracteur_num as varchar) as code_tracteur from marts.fct_autoroute_interdite", ["code_tracteur"]),
    "Accident travail": ("select * from marts.fct_accident_travail", []),
    "Anomalie matériel": ("select *, cast(tracteur_num as varchar) as code_tracteur from marts.fct_anomalie_materiel", ["code_tracteur"]),
    "Anomalie QHSE": ("select * from marts.fct_anomalie_qhse", []),
    "Écriture comptable": ("select * from marts.fct_ecriture_comptable", []),
    "Facture atelier": ("select * from marts.fct_facture_atelier", []),
    "Rapprochement": ("select * from marts.fct_rapprochement_atelier_compta", []),
    "Objectif": ("select * from marts.fct_objectif", []),
    "Objectif exploitant": ("select * from marts.fct_objectif_exploitant", []),
    "Coût standard": ("select * from marts.ref_cout_standard", []),
    "Indicateurs": ("select * from marts.mart_kpi", []),
    "Paramètres": ("select * from marts.parametres", []),
    # ajouts : rentabilité réelle, historique des contrats, qualité des données, habilitations (sécurité par ligne)
    "Rentabilité tracteur": ("select *, cast(tracteur_num as varchar) as code_tracteur from marts.fct_rentabilite_tracteur_mois",
                             ["code_tracteur"]),
    "Rentabilité conducteur": ("select * from marts.fct_rentabilite_conducteur_mois", []),
    "Historique conducteur": ("select * from marts.dim_conducteur_historique", []),
    "Contrôle qualité": ("select * from marts.mart_qualite_donnees", ["ordre"]),
    "Import": ("select * from marts.fct_import", []),
    "Résultat dbt": ("select * from meta.resultats_dbt", ["unique_id"]),
    "Habilitation": ("select * from referentiel.habilitations", []),
}
TABLES_CACHEES = {"Habilitation"}

# Sécurité par ligne : un exploitant ne voit que les activités qui lui sont attribuées (table Habilitation, par e-mail).
# Conducteur, Matériel et Activité filtrent à eux trois tous les faits du modèle. « Direction » voit tout.
FILTRE_HABILITATION = ("{col} IN CALCULATETABLE(VALUES('Habilitation'[Code activité]), "
                       "'Habilitation'[E-mail] = USERPRINCIPALNAME())")
ROLES = {
    # les remplaçants forment un pool partagé : visibles de tous les exploitants (sinon leurs voyages disparaîtraient)
    "Exploitant": {"Conducteur": FILTRE_HABILITATION.format(col="'Conducteur'[Code activité]")
                                 + " || (LEFT('Conducteur'[Type contrat], 10) = \"Remplaçant\" && NOT ISEMPTY("
                                 + "CALCULATETABLE(VALUES('Habilitation'[Code activité]), 'Habilitation'[E-mail] = USERPRINCIPALNAME())))",
                   "Matériel": FILTRE_HABILITATION.format(col="'Matériel'[Code activité]"),
                   "Activité": FILTRE_HABILITATION.format(col="'Activité'[Code activité]"),
                   "Habilitation": "'Habilitation'[E-mail] = USERPRINCIPALNAME()"},
    "Direction": {},
}

# (table many, colonne many, table one, colonne one, active)
RELATIONS = [
    ("Voyage", "date_livre", "Date", "date_jour", True), ("Voyage", "date_charge", "Date", "date_jour", False),
    ("Voyage", "matricule", "Conducteur", "matricule", True), ("Voyage", "code_tracteur", "Matériel", "code_materiel", True),
    ("Voyage", "remorque", "Matériel", "code_materiel", False),
    ("Voyage", "client_cd", "Client", "client_cd", True), ("Voyage", "relation_cd", "Relation", "relation_cd", True),
    ("Voyage", "activite_cd", "Activité", "activite_cd", True),
    ("Événement facturé", "voyage_id", "Voyage", "voyage_id", True),
    ("Justification attente", "voyage_id", "Voyage", "voyage_id", True),
    ("Justification lavage", "cmr", "Voyage", "cmr", True),
    ("Pointage", "date_pointage", "Date", "date_jour", True), ("Pointage", "matricule", "Conducteur", "matricule", True),
    ("Pointage", "code_tracteur", "Matériel", "code_materiel", True),
    ("Chrono", "date_jour", "Date", "date_jour", True), ("Chrono", "matricule", "Conducteur", "matricule", True),
    ("Compteur paie", "mois", "Date", "date_jour", True), ("Compteur paie", "matricule", "Conducteur", "matricule", True),
    ("Activité chauffeur", "date_activite", "Date", "date_jour", True), ("Activité chauffeur", "matricule", "Conducteur", "matricule", True),
    ("Affectation", "date_jour", "Date", "date_jour", True), ("Affectation", "matricule", "Conducteur", "matricule", True),
    ("Affectation", "code_tracteur", "Matériel", "code_materiel", True), ("Affectation", "activite_cd", "Activité", "activite_cd", True),
    ("Immobilisation", "date_jour", "Date", "date_jour", True), ("Immobilisation", "code_tracteur", "Matériel", "code_materiel", True),
    ("Immobilisation", "activite_cd", "Activité", "activite_cd", True),
    ("Atelier", "date_ot", "Date", "date_jour", True), ("Atelier", "code_tracteur", "Matériel", "code_materiel", True),
    ("Visite technique", "date_visite", "Date", "date_jour", True), ("Visite technique", "code_tracteur", "Matériel", "code_materiel", True),
    ("Heures mécanicien", "mois", "Date", "date_jour", True),
    ("Carburant", "date_prelevement", "Date", "date_jour", True), ("Carburant", "matricule", "Conducteur", "matricule", True),
    ("Carburant", "code_tracteur", "Matériel", "code_materiel", True),
    ("Conso FMS", "date_jour", "Date", "date_jour", True), ("Conso FMS", "matricule", "Conducteur", "matricule", True),
    ("Conso FMS", "code_tracteur", "Matériel", "code_materiel", True),
    ("Absence", "date_absence", "Date", "date_jour", True), ("Absence", "matricule", "Conducteur", "matricule", True),
    ("Infraction", "date_infraction", "Date", "date_jour", True), ("Infraction", "matricule", "Conducteur", "matricule", True),
    ("Autoroute interdite", "date_evenement", "Date", "date_jour", True), ("Autoroute interdite", "matricule", "Conducteur", "matricule", True),
    ("Autoroute interdite", "code_tracteur", "Matériel", "code_materiel", True),
    ("Accident travail", "date_accident", "Date", "date_jour", True), ("Accident travail", "matricule", "Conducteur", "matricule", True),
    ("Anomalie matériel", "date_signalement", "Date", "date_jour", True), ("Anomalie matériel", "code_tracteur", "Matériel", "code_materiel", True),
    ("Anomalie QHSE", "date_anomalie", "Date", "date_jour", True), ("Anomalie QHSE", "activite_cd", "Activité", "activite_cd", True),
    # le rapprochement porte la date ; écritures et factures le filtrent dans les deux sens (une ligne d'écriture -> son statut)
    ("Rapprochement", "date_reference", "Date", "date_jour", True),
    ("Écriture comptable", "num_facture", "Rapprochement", "num_facture", "both"),
    ("Facture atelier", "num_facture", "Rapprochement", "num_facture", "both"),
    ("Objectif", "activite_cd", "Activité", "activite_cd", True),
    ("Rentabilité tracteur", "mois", "Date", "date_jour", True),
    ("Rentabilité tracteur", "code_tracteur", "Matériel", "code_materiel", True),
    ("Rentabilité conducteur", "mois", "Date", "date_jour", True),
    ("Rentabilité conducteur", "matricule", "Conducteur", "matricule", True),
    ("Historique conducteur", "matricule", "Conducteur", "matricule", True),
]

TYPES = {"VARCHAR": "string", "BOOLEAN": "boolean", "DATE": "dateTime", "TIMESTAMP": "dateTime", "TIMESTAMP WITH TIME ZONE": "dateTime",
         "DOUBLE": "double", "FLOAT": "double", "INTEGER": "int64", "BIGINT": "int64", "SMALLINT": "int64", "TINYINT": "int64",
         "HUGEINT": "int64"}


def q(name):  # nom TMDL (quoté si nécessaire)
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else "'" + name.replace("'", "''") + "'"


def tag():
    tag.n += 1
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"transval/{tag.n}"))


tag.n = 0
TRI = {"nom_mois": "mois", "mois_annee": "annee_mois", "semaine_affichage": "annee_semaine_num", "annee_semaine": "annee_semaine_num",
       "nom_jour": "jour_semaine"}


def main():
    DONNEES.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    schema = {}
    for t, (sql, hidden) in TABLES.items():
        cols = con.sql(f"describe ({sql})").fetchall()
        sel = ", ".join(f'"{c[0]}" as "{libelle(c[0])}"' for c in cols)
        fichier = DONNEES / f"{t}.parquet"
        con.execute(f"copy (select {sel} from ({sql})) to '{fichier.as_posix()}' (format parquet)")
        schema[t] = [(c[0], libelle(c[0]), TYPES.get(c[1], "string"), c[0] in hidden) for c in cols]
    con.close()

    tables_dir = SM / "definition" / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    for f in tables_dir.glob("*.tmdl"):
        f.unlink()
    for t, cols in schema.items():
        lines = [f"table {q(t)}", f"\tlineageTag: {tag()}", ""]
        if t in TABLES_CACHEES:
            lines[2:2] = ["\tisHidden"]
        if t == "Date":
            lines[2:2] = ["\tdataCategory: Time"]
        for src, nom, typ, hidden in cols:
            lines += [f"\tcolumn {q(nom)}", f"\t\tdataType: {typ}"]
            if typ == "dateTime":
                lines.append("\t\tformatString: dd/mm/yyyy")
            if typ in ("int64", "double") and (src.endswith("_id") or src in ("matricule", "tracteur_num", "num_facture", "annee", "mois",
                                                                             "semaine", "trimestre", "jour_semaine", "annee_semaine_num")):
                lines.append("\t\tsummarizeBy: none")
            elif typ in ("int64", "double"):
                lines.append("\t\tsummarizeBy: sum")
            else:
                lines.append("\t\tsummarizeBy: none")
            if hidden:
                lines.append("\t\tisHidden")
            if t == "Date" and src in TRI:  # libellés triés chronologiquement (S01 2024 après S52 2023, pas après S01 2023)
                lines.append(f"\t\tsortByColumn: {q(libelle(TRI[src]))}")
            if t == "Date" and src == "date_jour":
                lines.append("\t\tisKey")
            lines += [f"\t\tlineageTag: {tag()}", f"\t\tsourceColumn: {nom}", ""]
        if t == "Date":  # hiérarchie de dates explicite (pas de tables de dates automatiques)
            lines += ["\thierarchy 'Hiérarchie de dates'", f"\t\tlineageTag: {tag()}", ""]
            for niveau, col in (("Année", "annee"), ("Trimestre", "nom_trimestre"), ("Mois", "nom_mois"), ("Jour", "date_jour")):
                lines += [f"\t\tlevel {q(niveau)}", f"\t\t\tlineageTag: {tag()}", f"\t\t\tcolumn: {q(libelle(col))}", ""]
        lines += [f"\tpartition {q(t)} = m", "\t\tmode: import", "\t\tsource =",
                  "\t\t\t\tlet",
                  f'\t\t\t\t    Source = Parquet.Document(File.Contents(DossierDonnees & "\\{t}.parquet"))',
                  "\t\t\t\tin", "\t\t\t\t    Source", ""]
        (tables_dir / f"{t}.tmdl").write_text("\n".join(lines), encoding="utf-8")

    # tables de sélecteurs (paramètres d'affichage) + table des mesures
    for t, (colonne, valeurs) in TABLES_SELECTEURS.items():
        rows = ", ".join("{" + ", ".join(f'"{v}"' if isinstance(v, str) else str(v) for v in r) + "}" for r in valeurs)
        lines = [f"table {q(t)}", f"\tlineageTag: {tag()}", "",
                 f"\tcolumn {q(colonne)}", "\t\tdataType: string", "\t\tsummarizeBy: none", f"\t\tlineageTag: {tag()}",
                 f"\t\tsourceColumn: [{colonne}]", "\t\tsortByColumn: Ordre", "", "\tcolumn Ordre", "\t\tdataType: int64", "\t\tsummarizeBy: none", "\t\tisHidden",
                 f"\t\tlineageTag: {tag()}", "\t\tsourceColumn: [Ordre]", "",
                 f"\tpartition {q(t)} = calculated", "\t\tmode: import",
                 f'\t\tsource = DATATABLE("{colonne}", STRING, "Ordre", INTEGER, {{{rows}}})', ""]
        (tables_dir / f"{t}.tmdl").write_text("\n".join(lines), encoding="utf-8")

    for t, champs in PARAMETRES_CHAMPS.items():  # paramètres de champs (NAMEOF), même structure que Power BI Desktop
        ordre_col, champs_col, theme_col, theme_ordre = f"{t} Ordre", f"{t} Champs", f"{t} Thème", f"{t} Thème ordre"
        avec_theme = len(champs[0]) == 3  # une même mesure peut figurer dans plusieurs thèmes
        rang = {}  # ordre par libellé (tri obligatoirement 1 pour 1) : première apparition
        themes = {}
        lignes = []
        for lib, ref, *th in champs:
            rang.setdefault(lib, len(rang))
            extra = f', "{th[0]}", {themes.setdefault(th[0], len(themes))}' if avec_theme else ""
            lignes.append(f'\t\t\t\t    ("{lib}", NAMEOF({ref}), {rang[lib]}{extra})')
        valeurs = ",\n".join(lignes)
        lines = [f"table {q(t)}", f"\tlineageTag: {tag()}", "",
                 f"\tcolumn {q(t)}", "\t\tdataType: string", "\t\tsummarizeBy: none", f"\t\tlineageTag: {tag()}",
                 "\t\tsourceColumn: [Value1]", f"\t\tsortByColumn: {q(ordre_col)}", "",
                 "\t\trelatedColumnDetails", f"\t\t\tgroupByColumn: {q(champs_col)}", "",
                 f"\tcolumn {q(champs_col)}", "\t\tdataType: string", "\t\tisHidden", "\t\tsummarizeBy: none",
                 f"\t\tlineageTag: {tag()}", "\t\tsourceColumn: [Value2]", f"\t\tsortByColumn: {q(ordre_col)}", "",
                 "\t\textendedProperty ParameterMetadata =", "\t\t\t\t{", '\t\t\t\t  "version": 3,', '\t\t\t\t  "kind": 2', "\t\t\t\t}", "",
                 f"\tcolumn {q(ordre_col)}", "\t\tdataType: int64", "\t\tisHidden", "\t\tsummarizeBy: none",
                 f"\t\tlineageTag: {tag()}", "\t\tsourceColumn: [Value3]", ""]
        if avec_theme:
            lines += [f"\tcolumn {q(theme_col)}", "\t\tdataType: string", "\t\tsummarizeBy: none", f"\t\tlineageTag: {tag()}",
                      "\t\tsourceColumn: [Value4]", f"\t\tsortByColumn: {q(theme_ordre)}", "",
                      f"\tcolumn {q(theme_ordre)}", "\t\tdataType: int64", "\t\tisHidden", "\t\tsummarizeBy: none",
                      f"\t\tlineageTag: {tag()}", "\t\tsourceColumn: [Value5]", ""]
        lines += [f"\tpartition {q(t)} = calculated", "\t\tmode: import", "\t\tsource =", "\t\t\t\t{", valeurs, "\t\t\t\t}", ""]
        (tables_dir / f"{t}.tmdl").write_text("\n".join(lines), encoding="utf-8")

    lines = ["table Mesures", f"\tlineageTag: {tag()}", ""]
    for dossier, nom, expr, fmt in MESURES:
        body = expr.strip()
        if "\n" in body:
            lines.append(f"\tmeasure {q(nom)} =")
            lines += ["\t\t\t" + l_ for l_ in body.splitlines()]
        else:
            lines.append(f"\tmeasure {q(nom)} = {body}")
        if fmt:
            lines.append(f"\t\tformatString: {fmt}")
        lines += [f"\t\tdisplayFolder: {dossier}", f"\t\tlineageTag: {tag()}", ""]
    lines += ["\tcolumn Colonne", "\t\tdataType: string", "\t\tisHidden", "\t\tsummarizeBy: none", f"\t\tlineageTag: {tag()}",
              "\t\tsourceColumn: [Colonne]", "", "\tpartition Mesures = calculated", "\t\tmode: import",
              '\t\tsource = DATATABLE("Colonne", STRING, {{""}})', ""]
    (tables_dir / "Mesures.tmdl").write_text("\n".join(lines), encoding="utf-8")

    noms = {t: dict((s, n) for s, n, _, _ in cols) for t, cols in schema.items()}
    rel = []
    for i, (tm, cm, to, co, actif) in enumerate(RELATIONS):
        rel += [f"relationship {uuid.uuid5(uuid.NAMESPACE_URL, f'rel/{tm}/{cm}/{to}')}"]
        if not actif:
            rel.append("\tisActive: false")
        if actif == "both":
            rel.append("\tcrossFilteringBehavior: bothDirections")
        rel += [f"\tfromColumn: {q(tm)}.{q(noms[tm][cm])}", f"\ttoColumn: {q(to)}.{q(noms[to][co])}", ""]
    (SM / "definition" / "relationships.tmdl").write_text("\n".join(rel), encoding="utf-8")

    (SM / "definition" / "expressions.tmdl").write_text(
        f'expression DossierDonnees = "{CHEMIN_POWERBI}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n'
        f"\tlineageTag: {tag()}\n\n\tannotation PBI_ResultType = Text\n", encoding="utf-8")
    ordre = list(TABLES) + list(TABLES_SELECTEURS) + list(PARAMETRES_CHAMPS) + ["Mesures"]
    (SM / "definition" / "model.tmdl").write_text(
        "model Model\n\tculture: fr-FR\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tdiscourageImplicitMeasures\n"
        "\tsourceQueryCulture: fr-FR\n\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n"
        "\tannotation __PBI_TimeIntelligenceEnabled = 0\n\n"
        + "".join(f"ref table {q(t)}\n" for t in ordre) + "".join(f"ref role {q(r)}\n" for r in ROLES), encoding="utf-8")
    roles_dir = SM / "definition" / "roles"
    roles_dir.mkdir(exist_ok=True)
    for f in roles_dir.glob("*.tmdl"):
        f.unlink()
    for role, filtres in ROLES.items():
        lines = [f"role {q(role)}", "\tmodelPermission: read", ""]
        for t, expr in filtres.items():
            lines += [f"\ttablePermission {q(t)} = {expr}", ""]
        (roles_dir / f"{role}.tmdl").write_text("\n".join(lines), encoding="utf-8")
    (SM / "definition" / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1600\n", encoding="utf-8")
    (SM / "definition.pbism").write_text('{\n  "version": "4.0",\n  "settings": {}\n}\n', encoding="utf-8")
    print(f"{len(TABLES)} tables exportées, {len(RELATIONS)} relations, {len(MESURES)} mesures")


if __name__ == "__main__":
    main()
