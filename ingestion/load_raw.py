"""Simule l'historique d'imports des 6 sources vers la couche RAW de l'entrepôt DuckDB.

Trois lots (CUTOFFS) : chargement initial puis deux deltas. La couche RAW garde TOUT, tel quel, en texte :
pas de typage, pas de nettoyage (c'est le rôle de dbt). Chaque ligne porte _batch_id / _loaded_at / _source.

Stratégies d'extraction, une par type de source (comme dans un vrai SI) :
  - ERP (exports CSV)     : fenêtre de dates avec 15 jours de recouvrement  -> doublons exacts à dédoublonner
  - TMS voyage            : CDC sur updated_at (watermark)                   -> plusieurs versions d'un même voyage
  - Compta                : append-only sur date de pièce (grand livre)
  - Télématique (JSONL)   : fenêtre de dates avec 7 jours de recouvrement
  - Référentiels, SharePoint, petites tables TMS : snapshot complet à chaque lot -> on garde le dernier
"""
import csv
import json
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb
import pandas as pd
from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CUTOFFS, SOURCES, WAREHOUSE  # noqa: E402

SCHEMAS = ["raw_erp", "raw_tms", "raw_compta", "raw_telematique", "raw_sharepoint"]


def ymd_to_date(v):
    s = str(v).strip()
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def ddmmyyyy(v):
    return datetime.strptime(v, "%d/%m/%Y").date()


def window(rows, key, lo, hi):
    return [r for r in rows if (lo is None or key(r) > lo) and key(r) <= hi]


def write(con, schema, table, rows, batch, cutoff, source):
    if not rows:  # import réussi sans nouvelle ligne : journalisé quand même (la fraîcheur se mesure sur le journal)
        con.execute("INSERT INTO raw_meta.import_log VALUES (?, ?, ?, ?, ?, ?)", [batch, cutoff, schema, table, 0, source])
        return 0
    df = pd.DataFrame(rows).astype("string")  # RAW = texte brut, typage en staging
    df["_batch_id"] = batch
    df["_loaded_at"] = datetime.combine(cutoff, datetime.min.time()) + timedelta(hours=23)
    df["_source"] = source
    con.register("df", df)
    con.execute(f"CREATE TABLE IF NOT EXISTS {schema}.{table} AS SELECT * FROM df WHERE false")
    con.execute(f"INSERT INTO {schema}.{table} BY NAME SELECT * FROM df")
    con.unregister("df")
    con.execute("INSERT INTO raw_meta.import_log VALUES (?, ?, ?, ?, ?, ?)",
                [batch, cutoff, schema, table, len(rows), source])
    return len(rows)


def read_csv(name):
    with open(SOURCES / "erp" / f"{name}.csv", encoding="cp1252", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def read_jsonl(name):
    return [json.loads(x) for x in open(SOURCES / "telematique" / f"{name}.jsonl", encoding="utf-8")]


def read_xlsx(name):
    ws = load_workbook(SOURCES / "sharepoint" / f"{name}.xlsx", read_only=True).active
    rows = list(ws.values)
    return [dict(zip(rows[0], r)) for r in rows[1:]]


def read_sqlite(db, sql):
    con = sqlite3.connect(SOURCES / db)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(sql)]
    con.close()
    return rows


def photo_conducteurs(hi):
    """Le référentiel RH n'expose que son état courant : la photo prise au lot est reconstituée en annulant les
    mouvements dont l'effet est postérieur à la date du lot (simulation d'un export réellement pris à cette date)."""
    etat = {r["MATRICULE"]: dict(r) for r in read_jsonl("conducteurs")}
    for m in sorted(read_jsonl("conducteurs_mouvements"), key=lambda x: ddmmyyyy(x["DATE_EFFET"]), reverse=True):
        if ddmmyyyy(m["DATE_EFFET"]) > hi:
            etat[m["MATRICULE"]][m["CHAMP"]] = m["ANCIENNE_VALEUR"]
    return list(etat.values())


def run(con, batch, lo, hi):
    n = 0
    over = lambda days: None if lo is None else lo - timedelta(days)  # noqa: E731

    # ERP : exports par fenêtre de dates, 15 j de recouvrement
    for name, key in (("POINTAGE", lambda r: ymd_to_date(r["PT_DATE"])), ("CHRONO", lambda r: ymd_to_date(r["CH_DATE"])),
                      ("AFFECTATION", lambda r: ymd_to_date(r["AF_DATE"])), ("PRELEVEMENT", lambda r: ymd_to_date(r["CB_DATE"])),
                      ("COMPTEUR_PAIE", lambda r: date(int(r["PA_ANNEE"]), int(r["PA_MOIS"]), 1)),
                      ("ACTIVITE_CHAUFFEUR", lambda r: date(int(r["FR_DATE"][:4]), int(r["FR_DATE"][4:6]), 1)),
                      ("HEURESMEC", lambda r: date(int(r["ANNEE"]), int(r["MOIS"]), 1)),
                      ("GMAO", lambda r: ymd_to_date(r["GM_DATE"]))):
        n += write(con, "raw_erp", name.lower(), window(read_csv(name), key, over(15), hi), batch, hi, f"erp/{name}.csv")
    n += write(con, "raw_erp", "param", read_csv("PARAM"), batch, hi, "erp/PARAM.csv")

    # TMS : CDC sur updated_at pour les voyages, fenêtre sur la date d'OT, snapshot pour le reste
    hi_ts = f"{hi.isoformat()} 23:59:59"
    lo_ts = None if lo is None else f"{lo.isoformat()} 23:59:59"
    where = f"updated_at <= '{hi_ts}'" + ("" if lo_ts is None else f" AND updated_at > '{lo_ts}'")
    # version courante + versions historiques qui étaient encore valides à la date du lot (table temporelle)
    sql = (f"SELECT * FROM voyage WHERE {where} UNION ALL "
           f"SELECT * EXCLUDE_VALID_TO FROM voyage_history WHERE {where} AND valid_to > '{hi_ts}'")
    cols = ", ".join(r[1] for r in sqlite3.connect(SOURCES / "tms.sqlite").execute("PRAGMA table_info(voyage)"))
    sql = sql.replace("* EXCLUDE_VALID_TO", cols)
    n += write(con, "raw_tms", "voyage", read_sqlite("tms.sqlite", sql), batch, hi, "tms.voyage")
    for t, col in (("atelier_ot", "date_ot"), ("visite_technique", "date_visite")):
        w = f"{col} <= '{hi}'" + ("" if lo is None else f" AND {col} > '{lo}'")
        n += write(con, "raw_tms", t, read_sqlite("tms.sqlite", f"SELECT * FROM {t} WHERE {w}"), batch, hi, f"tms.{t}")
    for t in ("client", "relation", "evenement_facture", "ville", "client_indexation", "entite", "atelier_ligne"):
        n += write(con, "raw_tms", t, read_sqlite("tms.sqlite", f"SELECT * FROM {t}"), batch, hi, f"tms.{t}")

    # Compta : grand livre append-only
    w = f"date_piece <= '{hi}'" + ("" if lo is None else f" AND date_piece > '{lo}'")
    n += write(con, "raw_compta", "ecriture", read_sqlite("compta.sqlite", f"SELECT * FROM ecriture WHERE {w}"), batch, hi, "compta.ecriture")

    # Télématique : JSONL par fenêtre, 7 j de recouvrement
    for name, col in (("conso_fms", "DATE_JOUR"), ("absences", "DATE_ABSENCE"), ("infractions", "DATE_INFRACTION"),
                      ("autoroutes_interdites", "DATE_EVENEMENT")):
        rows = window(read_jsonl(name), lambda r: ddmmyyyy(r[col]), over(7), hi)
        n += write(con, "raw_telematique", name, rows, batch, hi, f"telematique/{name}.jsonl")
    n += write(con, "raw_telematique", "conducteurs", photo_conducteurs(hi), batch, hi, "telematique/conducteurs.jsonl")

    # SharePoint : snapshot complet de chaque liste, tel qu'il était à la date du lot
    # (une justification n'existe pas avant le voyage qu'elle justifie)
    # date de première saisie du voyage dans le TMS (version initiale si le voyage a été régularisé depuis)
    saisie = {str(r["voyage_id"]): r["d"] for r in read_sqlite(
        "tms.sqlite", "SELECT voyage_id, min(updated_at) AS d FROM (SELECT voyage_id, updated_at FROM voyage "
                      "UNION ALL SELECT voyage_id, updated_at FROM voyage_history) GROUP BY voyage_id")}
    a_date = {"justif_attentes": lambda r: saisie.get(str(r["N° voyage"]).strip(), "9999") <= hi_ts,
              "justif_lavages": lambda r: saisie.get(str(r["N° CMR"]).replace("CMR", ""), "9999") <= hi_ts}
    for name in ("justif_attentes", "justif_lavages"):
        n += write(con, "raw_sharepoint", name, [r for r in read_xlsx(name) if a_date[name](r)], batch, hi, f"sharepoint/{name}.xlsx")
    for name in ("justif_autoroutes", "accidents_travail", "anomalies_materiel",
                 "anomalies_qhse", "objectifs", "couts_standards"):
        n += write(con, "raw_sharepoint", name, read_xlsx(name), batch, hi, f"sharepoint/{name}.xlsx")
    return n


def main(lots=None):
    """lots : numéros de lots à charger (défaut : tous). Le lot 1 réinitialise la couche RAW."""
    lots = lots or list(range(1, len(CUTOFFS) + 1))
    WAREHOUSE.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(WAREHOUSE))
    if 1 in lots:
        for s in SCHEMAS + ["raw_meta"]:
            con.execute(f"DROP SCHEMA IF EXISTS {s} CASCADE")
            con.execute(f"CREATE SCHEMA {s}")
        con.execute("""CREATE TABLE raw_meta.import_log (batch_id INT, cutoff DATE, schema_name VARCHAR, table_name VARCHAR,
                       rows_loaded INT, source VARCHAR)""")
    for batch in lots:
        lo = CUTOFFS[batch - 2] if batch > 1 else None
        print(f"lot {batch} -> {CUTOFFS[batch - 1]} : {run(con, batch, lo, CUTOFFS[batch - 1])} lignes")
    con.close()


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or None)
