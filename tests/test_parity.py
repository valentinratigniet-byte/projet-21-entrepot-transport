"""Parité : chaque KPI du Power BI de départ (legacy) doit être retrouvé à l'identique dans l'entrepôt.

Les seuls écarts tolérés sont les corrections VOULUES de l'entrepôt ; pour chacune, le test ne se contente
pas de les ignorer : il recalcule l'écart depuis l'entrepôt et vérifie qu'il s'explique exactement.
Lancer : python tests/test_parity.py   (après run_all.py, ou au moins legacy + dbt build)
"""
import json
import math
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, WAREHOUSE  # noqa: E402
from legacy.rapports_powerbi import PERIODES  # noqa: E402

TOL = 1e-6


def same(a, b):
    if a is None or (isinstance(a, float) and math.isnan(a)):
        return b is None or (isinstance(b, float) and math.isnan(b))
    return b is not None and not (isinstance(b, float) and math.isnan(b)) and abs(a - b) <= TOL * max(1, abs(a))


def bornes(p):
    d0, d1 = PERIODES[p]
    return f"date '{d0.date()}' and date '{d1.date()}'"


# Écarts voulus : kpi legacy -> (kpi entrepôt de référence, SQL qui recalcule la valeur legacy depuis l'entrepôt, raison)
ECARTS_VOULUS = {
    "heures_chargement_dechargement_palmares": (
        "heures_chargement_dechargement",
        lambda p: f"""select sum(heures) from marts.fct_pointage where est_valide and categorie_hchc = 'chargement_dechargement'
                      and date_pointage between {bornes(p)}""",
        "Le rapport Palmarès ne filtrait pas les corrections manuelles (type 'M') contrairement au TBE : "
        "deux chiffres pour le même indicateur. L'entrepôt n'en garde qu'un (celui du TBE).",
    ),
    "tx_reussite_vt": (
        "tx_reussite_vt",
        lambda p: f"""select count(*) filter (where resultat_brut = 'Valide') / count(*) from marts.fct_visite_technique
                      where date_visite between {bornes(p)}""",
        "Le DAX comparait le texte strictement à \"Valide\" : les saisies 'valide ' ou 'VALIDE' comptaient comme des échecs.",
    ),
}


def main():
    legacy = pd.read_csv(ROOT / "data" / "legacy_kpis.csv")
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    dwh = {(k, p): v for k, p, v in con.sql("select kpi, periode, valeur from marts.mart_kpi").fetchall()}
    ok, voulus, erreurs = 0, [], []
    for r in legacy.itertuples():
        attendu = None if pd.isna(r.valeur) else float(r.valeur)
        if r.kpi in ECARTS_VOULUS:
            ref, sql, raison = ECARTS_VOULUS[r.kpi]
            recalcul = con.sql(sql(r.periode)).fetchone()[0]
            if not same(attendu, recalcul):
                erreurs.append(f"{r.kpi} {r.periode}: écart non expliqué (legacy {attendu} vs recalcul {recalcul})")
            else:
                voulus.append((r.kpi, r.periode, attendu, dwh.get((ref, r.periode)), raison))
            continue
        if (r.kpi, r.periode) not in dwh:
            erreurs.append(f"{r.kpi} {r.periode}: absent de l'entrepôt")
        elif not same(attendu, dwh[(r.kpi, r.periode)]):
            erreurs.append(f"{r.kpi} {r.periode}: legacy {attendu} != entrepôt {dwh[(r.kpi, r.periode)]}")
        else:
            ok += 1
    (ROOT / "data" / "parite.json").write_text(json.dumps(  # lu par ops/rapport_execution.py (alertes n8n)
        {"ok": ok, "total": len(legacy), "voulus": [[k, p, a, b] for k, p, a, b, _ in voulus], "erreurs": erreurs},
        ensure_ascii=False, default=float), encoding="utf-8")
    print(f"{ok}/{len(legacy)} KPI identiques au centime près entre le Power BI de départ et l'entrepôt")
    for k, p, a, b, raison in voulus:
        print(f"  écart voulu {k} [{p}] : Power BI {a:.4f} -> entrepôt {b:.4f} — {raison}")
    for e in erreurs:
        print("  ÉCHEC", e)
    assert not erreurs, f"{len(erreurs)} KPI divergent"
    assert ok + len(voulus) == len(legacy)


def test_parity():
    main()


if __name__ == "__main__":
    main()
