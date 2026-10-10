"""Rapport d'exécution de l'actualisation : ce que n8n lit pour décider d'alerter.

Rassemble, après `run_all.py` : résultats des tests dbt, parité Power BI de départ <-> entrepôt, fraîcheur des imports (par rapport
à la date de référence), taux de chaque contrôle qualité comparé à son seuil (ops/seuils_qualite.json).
Écrit data/rapports_execution/<horodatage>.json et l'imprime sur la sortie standard (lue par le nœud n8n suivant).

    python ops/rapport_execution.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import AS_OF, WAREHOUSE  # noqa: E402

SEUILS = json.loads((ROOT / "ops" / "seuils_qualite.json").read_text(encoding="utf-8"))


def evaluer(con, parite):
    alertes = []
    tests = con.execute("select statut, count(*) from meta.resultats_dbt where type_noeud = 'test' group by 1").fetchall()
    tests = dict(tests)
    echecs = sum(n for s, n in tests.items() if s not in ("pass", "success"))
    if echecs:
        alertes.append(f"{echecs} test(s) dbt en échec")

    if parite.get("erreurs"):
        alertes.append(f"{len(parite['erreurs'])} KPI divergent(s) entre le Power BI de départ et l'entrepôt")

    retard = con.execute("""select table_name, max(cutoff) from raw_meta.import_log group by 1
                            having datediff('day', max(cutoff), ?::date) > ?""",
                         [AS_OF, SEUILS["fraicheur_max_jours"]]).fetchall()
    for table, dernier in retard:
        alertes.append(f"source en retard : {table} (dernier import {dernier})")

    controles = []
    for ordre, controle, source, brutes, concernees in con.execute(
            "select ordre, controle, source, lignes_brutes, lignes_concernees from marts.mart_qualite_donnees order by ordre").fetchall():
        taux = round(100.0 * concernees / brutes, 2) if brutes else 0.0
        seuil = SEUILS["controles"].get(controle)
        depasse = seuil is not None and taux > seuil
        controles.append({"controle": controle, "source": source, "taux_pct": taux, "seuil_pct": seuil, "depasse": depasse})
        if depasse:
            alertes.append(f"{controle} ({source}) : {taux} % > seuil {seuil} %")

    lots = con.execute("select batch_id, cutoff, sum(rows_loaded) from raw_meta.import_log group by 1, 2 order by 1").fetchall()
    return {
        "horodatage": datetime.now().isoformat(timespec="seconds"),
        "date_reference": AS_OF.isoformat(),
        "statut": "ALERTE" if alertes else "OK",
        "alertes": alertes,
        "imports": [{"lot": b, "date": str(d), "lignes": int(n)} for b, d, n in lots],
        "tests_dbt": {"reussis": tests.get("pass", 0), "echecs": echecs},
        "parite": {"identiques": parite.get("ok"), "total": parite.get("total"), "ecarts_voulus": len(parite.get("voulus", []))},
        "controles": controles,
    }


def main():
    parite = json.loads((ROOT / "data" / "parite.json").read_text(encoding="utf-8"))
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    rapport = evaluer(con, parite)
    con.close()
    dossier = ROOT / "data" / "rapports_execution"
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / f"{rapport['horodatage'].replace(':', '-')}.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=2),
                                                                             encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(rapport, ensure_ascii=False))


if __name__ == "__main__":
    main()
