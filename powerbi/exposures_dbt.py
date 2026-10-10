"""Déclare les rapports Power BI comme « exposures » dbt : le lignage dbt va de la source jusqu'au rapport.

Pour chaque rapport : tables et mesures utilisées par ses visuels -> tables du modèle (les mesures DAX sont suivies
récursivement jusqu'aux tables qu'elles lisent) -> marts dbt (d'après les requêtes de build_model.py).

    python powerbi/exposures_dbt.py      # écrit dbt/models/marts/_exposures.yml
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

PBI = Path(__file__).resolve().parent
sys.path.insert(0, str(PBI))
from build_model import TABLES  # noqa: E402
from mesures import MESURES  # noqa: E402

SORTIE = PBI.parent / "dbt" / "models" / "marts" / "_exposures.yml"
DOMAINES = {  # rapport -> (propriétaire métier, description courte)
    "Activité clients": ("Direction commerciale", "CA, voyages, marge et appairage par client"),
    "Activité par relation": ("Direction commerciale", "Indicateurs par relation (origine -> destination)"),
    "Coût des trajets": ("Contrôle de gestion", "Coût standard des trajets par relation et par conducteur"),
    "Prix et indexation clients": ("Direction commerciale", "Prix pratiqués et indexation gazole"),
    "Productivité hebdomadaire": ("Exploitation", "CA et tracteurs par jour, comparaison N / N-1"),
    "Tableau de bord exploitant": ("Exploitation", "Pilotage quotidien de l'activité et des coûts"),
    "Heures conducteurs": ("Exploitation", "Heures payées, compensées, à justifier, frais"),
    "Projection des heures": ("Exploitation", "Projection des heures du mois"),
    "Missions conducteurs": ("Exploitation", "Missions du jour par conducteur"),
    "Absences conducteurs": ("Ressources humaines", "Absences par motif et par activité"),
    "Maintenance atelier": ("Atelier", "Coûts de maintenance, productivité et qualité de l'atelier"),
    "Parc matériel": ("Atelier", "Parc tracteurs et semi-remorques, utilisation"),
    "Anomalies matériel": ("Atelier", "Anomalies signalées et leur traitement"),
    "Consommation carburant": ("Exploitation", "Consommation par conducteur, véhicule, activité"),
    "Prix du gazole": ("Achats", "Prix du gazole par fournisseur et par mois"),
    "Tableau de bord QHSE": ("QHSE", "Anomalies, accidents du travail, infractions"),
    "Infractions RSE": ("QHSE", "Infractions à la réglementation sociale européenne"),
    "Autoroutes interdites": ("QHSE", "Passages sur des autoroutes interdites aux poids lourds"),
    "Prestations à facturer": ("Contrôle de gestion", "Attentes, lavages, samedis, doubles dépotages à facturer"),
    "Rapprochement atelier et comptabilité": ("Contrôle de gestion", "Factures atelier rapprochées des écritures comptables"),
    "Qualité des données": ("Équipe data", "Contrôles à l'import, journal des lots, tests dbt"),
    "Rentabilité": ("Contrôle de gestion", "Marge directe par tracteur, contribution par conducteur (coûts réels)"),
    "Référentiel conducteurs": ("Ressources humaines", "Contrats et historique des contrats"),
}


def modele_de(table):
    """Table Power BI -> modèle dbt (ou seed) qu'elle lit."""
    sql = TABLES[table][0]
    return re.findall(r"\b(?:marts|referentiel)\.(\w+)", sql)


def tables_des_mesures():
    expr = {nom: e for _, nom, e, _ in MESURES}
    cache = {}

    def tables(nom, vus=()):
        if nom in cache:
            return cache[nom]
        e = expr.get(nom, "")
        res = set(re.findall(r"'([^']+)'\[", e)) | set(re.findall(r"(?<![\w'\]])([A-Za-z]\w*)\[", e))
        for m in re.findall(r"(?<!['\w\]])\[([^\]]+)\]", e):
            if m in expr and m not in vus:
                res |= tables(m, vus + (nom,))
        cache[nom] = {t for t in res if t in TABLES}
        return cache[nom]
    return tables


def parcourir(o):
    """Toutes les paires (clé, valeur) d'un JSON imbriqué."""
    if isinstance(o, dict):
        for k, v in o.items():
            yield k, v
            yield from parcourir(v)
    elif isinstance(o, list):
        for v in o:
            yield from parcourir(v)


def slug(texte):
    t = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


def main():
    tables_mesure = tables_des_mesures()
    lignes = ["# Généré par powerbi/exposures_dbt.py : un rapport Power BI = une exposure (lignage source -> rapport).",
              "version: 2", "", "exposures:"]
    for rapport, (proprietaire, description) in DOMAINES.items():
        dossier = PBI / f"{rapport}.Report"
        assert dossier.exists(), f"rapport introuvable : {rapport}"
        tables = set()
        for f in dossier.glob("definition/pages/*/visuals/*/visual.json"):
            for cle, valeur in parcourir(json.loads(f.read_text(encoding="utf-8"))):
                if cle == "Entity" and valeur in TABLES:
                    tables.add(valeur)
                elif cle == "Measure" and isinstance(valeur, dict):
                    tables |= tables_mesure(valeur.get("Property", ""))
        modeles = sorted({m for t in tables for m in modele_de(t)})
        lignes += [f"  - name: rapport_{slug(rapport)}", f"    label: \"{rapport}\"", "    type: dashboard", "    maturity: high",
                   f"    description: \"{description} (rapport Power BI `{rapport}.pbip`).\"",
                   f"    owner: {{name: \"{proprietaire}\", email: data@transval.example}}", "    depends_on:"]
        lignes += [f"      - ref('{m}')" for m in modeles]
        print(f"  {rapport:40} {len(modeles):2} modèles")
    SORTIE.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print(f"{len(DOMAINES)} exposures -> {SORTIE.relative_to(PBI.parent)}")


if __name__ == "__main__":
    main()
