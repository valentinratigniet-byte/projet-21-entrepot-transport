"""Une commande : sources fictives -> 3 imports simulés -> entrepôt dbt -> Power BI de départ -> test de parité."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
DBT = str(Path(PY).with_name("dbt.exe" if os.name == "nt" else "dbt"))


def step(titre, cmd, cwd=ROOT):
    print(f"\n=== {titre}")
    subprocess.run(cmd, cwd=cwd, check=True)


step("1. Génération des 6 sources fictives", [PY, "sources/generate.py"])
sys.path.insert(0, str(ROOT))
from common import AS_OF, CUTOFFS  # noqa: E402
for lot in range(1, len(CUTOFFS) + 1):  # comme en production : un import, puis une mise à jour de l'entrepôt
    step(f"2.{lot} Import du lot {lot} ({CUTOFFS[lot - 1]}) -> couche RAW", [PY, "ingestion/load_raw.py", str(lot)])
    mode = ["--full-refresh"] if lot == 1 else []  # lot 1 : construction complète ; ensuite : incrémental
    date_lot = CUTOFFS[lot - 1]  # le build tourne le jour de l'import : sa date de référence est celle du lot
    step(f"3.{lot} Entrepôt : dbt build {'complet' if lot == 1 else 'incrémental'} au {date_lot} (seeds, modèles, tests)",
         [DBT, "build", *mode, "--profiles-dir", ".", "--vars", f"as_of: '{date_lot}'"], cwd=ROOT / "dbt")
assert CUTOFFS[-1] == AS_OF  # le dernier lot est la date de référence des rapports


def charger_resultats_dbt():
    """Résultats du dernier `dbt build` (tests compris) -> meta.resultats_dbt, lus par le rapport Qualité des données."""
    import json
    import duckdb
    import pandas as pd
    from common import WAREHOUSE
    rr = json.loads((ROOT / "dbt" / "target" / "run_results.json").read_text(encoding="utf-8"))
    df = pd.DataFrame([{"unique_id": r["unique_id"], "type_noeud": r["unique_id"].split(".")[0],
                        "nom": r["unique_id"].split(".")[2], "statut": r["status"], "echecs": r.get("failures") or 0,
                        "duree_s": round(r["execution_time"], 3), "execute_le": rr["metadata"]["generated_at"][:19]}
                       for r in rr["results"]])
    con = duckdb.connect(str(WAREHOUSE))
    con.execute("create schema if not exists meta")
    con.execute("create or replace table meta.resultats_dbt as select * from df")
    con.close()
    print(f"{len(df)} résultats dbt chargés ({(df.statut == 'pass').sum()} tests réussis)")


print("\n=== 3 bis. Résultats dbt -> entrepôt (meta.resultats_dbt)")
charger_resultats_dbt()
step("4. Situation de départ : Power BI branché en direct sur les sources", [PY, "legacy/rapports_powerbi.py"])
step("5. Parité Power BI <-> entrepôt", [PY, "tests/test_parity.py"])
