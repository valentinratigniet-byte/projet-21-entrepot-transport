"""Situation de départ de TransVal : le Power BI « tout-en-un », sans entrepôt.

Chaque rapport lit les sources EN DIRECT, applique ses propres étapes Power Query (M) puis ses mesures DAX.
Chaque fonction indique la mesure ou la requête qu'elle reproduit. Les incohérences de cette situation sont
conservées volontairement
(ex. deux rapports qui filtrent différemment la même table de pointage).

Sortie : data/legacy_kpis.csv (domaine, kpi, periode, valeur), comparée à l'entrepôt par tests/test_parity.py.
"""
import json
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import AS_OF, ROOT, SOURCES  # noqa: E402

TODAY = pd.Timestamp(AS_OF)  # TODAY() du DAX, figé pour la reproductibilité
_MOIS = TODAY.replace(day=1) - pd.offsets.MonthBegin(1)  # dernier mois complet
PERIODES = {_MOIS.strftime("%Y-%m"): (_MOIS, _MOIS + pd.offsets.MonthEnd(0)),
            str(TODAY.year): (pd.Timestamp(TODAY.year, 1, 1), TODAY)}
MOIS_EN_COURS = TODAY.strftime("%Y-%m")


# ------------------------------------------------------------------ connecteurs "Power Query"
def DB2(table):  # DB2.Database(...) sur l'export AS/400 : tout arrive en texte, culture fr
    return pd.read_csv(SOURCES / "erp" / f"{table}.csv", sep=";", encoding="cp1252", dtype=str, keep_default_na=False)


def SqlServer(db, query):
    con = sqlite3.connect(SOURCES / db)
    df = pd.read_sql_query(query, con)
    con.close()
    return df


def Oracle(view):
    return pd.DataFrame([json.loads(x) for x in open(SOURCES / "telematique" / f"{view}.jsonl", encoding="utf-8")])


def SharePoint(liste):
    return pd.read_excel(SOURCES / "sharepoint" / f"{liste}.xlsx")


def date_aaaammjj(s):  # #date(Number.From(Text.Start(txt,4)), Number.From(Text.Middle(txt,4,2)), ...)
    return pd.to_datetime(s.str.strip(), format="%Y%m%d")


def nombre_fr(s):  # Table.TransformColumnTypes(..., type number) en culture fr-FR
    return s.str.replace(",", ".").astype(float)


# ------------------------------------------------------------------ table 'Date' (DAX calculée)
FERIES = set(pd.to_datetime(pd.read_csv(ROOT / "dbt" / "seeds" / "jours_feries.csv")["date_ferie"]))


def jours_ouvres(d0, d1):  # [Jours ouvrés] = COUNTROWS('Date') avec 'Date'[IsBusinessDay] = TRUE
    return sum(1 for d in pd.date_range(d0, d1) if d.weekday() < 5 and d not in FERIES)


def entre(s, p):
    d0, d1 = PERIODES[p]
    return (s >= d0) & (s <= d1)


def div(a, b):  # DIVIDE()
    return np.nan if b == 0 or pd.isna(b) else a / b


# ------------------------------------------------------------------ rapports
def rapport_activite():
    """vue_Activite (SQL Server BI) : la vue exclut les voyages annulés."""
    v = SqlServer("tms.sqlite", "SELECT * FROM voyage WHERE statut <> 'ANNULE'")
    v["date_livre"] = pd.to_datetime(v["date_livre"])
    out = []
    for p in PERIODES:
        x = v[entre(v["date_livre"], p)]
        ca_n = x.loc[x["date_livre"] <= TODAY, "ca_facture"].sum()          # CA facturé à date
        rel = x[x["relation_cd"].notna() & (x["relation_cd"] != "")]        # FILTER(... relation renseignée)
        mcv = rel["mcv_marge_lissee"].fillna(rel["mcv_marge"]).sum()          # IF(NOT ISBLANK(MargeLissee), ..., Marge)
        autoroute = (x["mcv_peage_charge"] + x["mcv_ecot_charge"] + x["mcv_ecot_vide"] + x["mcv_peage_vide"]).sum()
        out += [("activite", "ca_facture", p, ca_n),
                ("activite", "nb_voyages", p, len(x)),                                         # nombre de voyages
                ("activite", "mcv_pct", p, div(mcv, rel["ca_reparti"].sum())),                 # MCV %
                ("activite", "appairage", p, div(x["km_charge"].sum(), x["km_total"].sum())),  # Appairage
                ("activite", "autoroute_eur_100km", p, div(autoroute, x["km_total"].sum()) * 100),
                ("activite", "ca_par_km", p, div(x["ca_facture"].sum(), x["km_total"].sum())),  # CA/KM€
                ("activite", "ca_par_heure", p, div(x["ca_facture"].sum(), x["tps_total_h"].sum())),  # CA/H
                ("activite", "ca_moyen_jour_ouvre", p, div(ca_n, jours_ouvres(*PERIODES[p]))),  # CA moyen par jour ouvré
                ("activite", "km_vide_eur", p, (x["km_total"].sum() - x["km_charge"].sum()) * 1.4)]  # Km à vide €
    return out


def rapport_controle_facturation():
    """Prestations à facturer : vue activité + événements facturés (table d'événements de voyage) + justifications SharePoint."""
    v = SqlServer("tms.sqlite", "SELECT * FROM voyage WHERE statut <> 'ANNULE'")
    v["date_livre"] = pd.to_datetime(v["date_livre"])
    e = SqlServer("tms.sqlite", "SELECT * FROM evenement_facture")
    j = SharePoint("justif_attentes")
    j["voyage_id"] = j["N° voyage"].astype(str).str.strip().astype(int)      # Text.Trim puis type number
    j["ok"] = j["Justifié"].astype(str).str.strip().str.upper() == "OUI"     # Text.Upper(Text.Trim(...))
    out = []
    for p in PERIODES:
        x = v[entre(v["date_livre"], p) & (v["date_livre"] <= TODAY)]
        ev = e[e["voyage_id"].isin(x["voyage_id"])]
        att = x["attente_a_facturer_eur"].sum()
        att_f = ev.loc[ev["type_evt"] == "ATT", "montant_facture"].sum()
        out += [("facturation", "attente_a_facturer_eur", p, att),
                ("facturation", "attente_facturee_eur", p, att_f),
                ("facturation", "pct_attente_facturee", p, div(att_f, att)),           # % Heures Attentes facturées
                ("facturation", "attentes_justifiees", p, int(j[j["ok"] & j["voyage_id"].isin(x["voyage_id"])].shape[0])),
                ("facturation", "lavage_a_facturer_eur", p, x["mcv_lavage_int"].sum()),
                ("facturation", "lavage_facture_eur", p, ev.loc[ev["type_evt"] == "LAV", "montant_facture"].sum()),
                ("facturation", "samedi_facture_eur", p, ev.loc[ev["type_evt"] == "SAM", "montant_facture"].sum()),
                ("facturation", "double_depotage_facture_eur", p, ev.loc[ev["type_evt"] == "DD", "montant_facture"].sum())]
    return out


def pointage(filtre_type):
    """Pointages : chaque rapport a SA requête. Le TBE filtre le type de saisie IN ('E','S'), le palmarès ne filtre pas."""
    pc = DB2("POINTAGE")
    pc = pc[(pc["PT_EXCLU"].str.strip() == "") & pc["PT_STATUT"].isin(["F", "V"])]
    if filtre_type:
        pc = pc[pc["PT_TYPE"].isin(["E", "S"])]
    pc["date"] = date_aaaammjj(pc["PT_DATE"])
    pc["lib"] = pc["PT_LIBACT"].str.strip()
    pc["h"] = pc["PT_DUREE_S"].astype(int) / 3600
    return pc


def rapport_heures():
    """Heures conducteurs (TBE + palmarès) : pointages, chronotachygraphe, compteurs de paie, nb voyages de l'activité."""
    tbe, palm = pointage(True), pointage(False)
    el = DB2("CHRONO")
    el["date"] = date_aaaammjj(el["CH_DATE"])
    for c in ("CH_CONDUITE_S", "CH_TRAVAIL_S", "CH_DISPO_S", "CH_REPOS_S", "CH_SERVICE_S"):
        el[c] = el[c].astype(int) / 3600
    cm = DB2("COMPTEUR_PAIE")
    cm["date"] = pd.to_datetime(dict(year=cm["PA_ANNEE"].astype(int), month=cm["PA_MOIS"].astype(int), day=1))
    cm["compensees"] = (nombre_fr(cm["PA_H_REAL"]) - nombre_fr(cm["PA_H_BASE"])) * -1
    v = SqlServer("tms.sqlite", "SELECT date_charge FROM voyage WHERE statut = 'LIVRE'")
    v["date_charge"] = pd.to_datetime(v["date_charge"])
    cd = ["Chargement", "Déchargement", "Chargement hors mission", "Livraison hors mission"]
    # garde-fou "jour >= 10" de la mesure Heures compensées : mois clos uniquement
    limite = pd.Timestamp(TODAY.year, TODAY.month, 1) if TODAY.day >= 10 else (pd.Timestamp(TODAY.year, TODAY.month, 1) - pd.offsets.MonthBegin(1))
    out = []
    for p in PERIODES:
        e = el[entre(el["date"], p)]
        hchc = (e["CH_TRAVAIL_S"] + e["CH_DISPO_S"] + e["CH_REPOS_S"]).sum()                  # heures hors conduite
        nb_v = int(entre(v["date_charge"], p).sum())
        t, pa = tbe[entre(tbe["date"], p)], palm[entre(palm["date"], p)]
        c = cm[entre(cm["date"], p) & (cm["date"] < limite)]
        out += [("heures", "hchc_heures", p, hchc),
                ("heures", "hchc_par_voyage", p, div(hchc, nb_v)),               # heures hors conduite par voyage
                ("heures", "heures_a_justifier", p, t.loc[t["lib"] == "Temps à justifier", "h"].sum()),
                ("heures", "heures_chargement_dechargement", p, t.loc[t["lib"].isin(cd), "h"].sum()),          # TBE
                ("heures", "heures_chargement_dechargement_palmares", p, pa.loc[pa["lib"].isin(cd), "h"].sum()),  # palmarès
                ("heures", "heures_decroche_raccroche", p, t.loc[t["lib"].isin(["Decrochage", "Décrochage", "Raccrochage"]), "h"].sum()),
                ("heures", "productivite_tc_ts", p, div(e["CH_CONDUITE_S"].sum(), e["CH_SERVICE_S"].sum())),
                ("heures", "heures_compensees", p, c["compensees"].sum())]
    # Chrono : projection de fin de mois (mois en cours uniquement)
    hier = TODAY - timedelta(1)
    m = el[(el["date"] >= pd.Timestamp(TODAY.year, TODAY.month, 1)) & (el["date"] <= hier)]
    h_real = m["CH_SERVICE_S"].sum()
    moy = div(h_real, m["date"].nunique())
    eom = TODAY + pd.offsets.MonthEnd(0)
    restants = int(np.busday_count(TODAY.date(), (eom + timedelta(1)).date()))  # NETWORKDAYS(TODAY(), EOMONTH()) : week-ends seulement
    out += [("heures", "heures_realisees_mtd", MOIS_EN_COURS, h_real),
            ("heures", "projection_fin_mois", MOIS_EN_COURS, h_real + moy * restants)]
    return out


def rapport_parc():
    """Productivité / nombre de tracteurs : table d'affectation, une ligne par tracteur et par jour."""
    a = DB2("AFFECTATION")
    a["date"] = date_aaaammjj(a["AF_DATE"])
    out = []
    for p in PERIODES:
        x = a[entre(a["date"], p)]
        actifs = x[x["AF_ACTIV"] != "MAIN"]
        out += [("parc", "nb_tracteurs_moyen_jour", p, div(len(actifs), jours_ouvres(*PERIODES[p]))),
                ("parc", "jours_tracteur_maintenance", p, int((x["AF_ACTIV"] == "MAIN").sum())),
                ("parc", "nb_conducteurs_actifs", p, actifs["AF_MATR"].str.strip().nunique())]
    return out


def rapport_atelier():
    """Indicateurs atelier (vues atelier et visites techniques) + KM de l'activité."""
    ot = SqlServer("tms.sqlite", "SELECT * FROM atelier_ot")
    ot["date_ot"] = pd.to_datetime(ot["date_ot"])
    vt = SqlServer("tms.sqlite", "SELECT * FROM visite_technique")
    vt["date_visite"] = pd.to_datetime(vt["date_visite"])
    v = SqlServer("tms.sqlite", "SELECT date_livre, km_total FROM voyage WHERE statut = 'LIVRE'")
    v["date_livre"] = pd.to_datetime(v["date_livre"])
    hors_st = ["VISITE TECHNIQUE", "VISITE OBLIGATOIRE", "LAVAGE", "LAVAGE INTERNE"]
    out = []
    for p in PERIODES:
        o, km = ot[entre(ot["date_ot"], p)], v.loc[entre(v["date_livre"], p), "km_total"].sum()
        st = o[(o["type_document"] == "Facture externe") & ~o["famille"].isin(hors_st)]["cout_total"].sum()
        x = vt[entre(vt["date_visite"], p)]
        out += [("atelier", "cout_maintenance_100km", p, div(o["cout_total"].sum(), km) * 100),
                ("atelier", "taux_sous_traitance", p, div(st, o["cout_total"].sum())),
                ("atelier", "pannes_10000km", p, div(o["raison"].isin(["COR", "DEP"]).sum(), km) * 10000),
                ("atelier", "tx_reussite_vt", p, div((x["resultat"] == "Valide").sum(), len(x)))]  # égalité stricte
    return out


def rapport_rapprochement():
    """État rapprochement FMS / CG : factures atelier (TMS) vs écritures comptables, table DAX d'identifiants (union des deux côtés)."""
    t2 = SqlServer("tms.sqlite", "SELECT num_facture AS id, cout_total AS ht FROM atelier_ot WHERE num_facture IS NOT NULL")
    t1 = SqlServer("compta.sqlite", "SELECT num_piece, montant_debit - montant_credit AS ht FROM ecriture WHERE compte = '615500'")
    t1["id"] = t1["num_piece"].str[2:].astype(int)                         # Number.From(Text.Range(num_piece, 2))
    t1, t2 = t1.groupby("id")["ht"].sum(), t2.groupby("id")["ht"].sum()
    dim = pd.DataFrame(index=t1.index.union(t2.index))                       # table d'identifiants = DISTINCT(UNION(...))
    dim["compta"], dim["atelier"] = t1, t2
    statut = np.select([dim["atelier"].isna(), dim["compta"].isna(), (dim["compta"] - dim["atelier"]).round(2) != 0],
                       ["Absent Atelier", "Absent Comptable", "Ecart montant"], "Ok")   # mesure Statut
    s = pd.Series(statut).value_counts()
    return [("rapprochement", f"nb_{k.lower().replace(' ', '_')}", "total", int(s.get(k, 0)))
            for k in ("Ok", "Absent Atelier", "Absent Comptable", "Ecart montant")]


def rapport_carburant():
    """Prix du gazole (prélèvements pompe + paramètres) et consommation FMS (vue Oracle)."""
    pr = DB2("PRELEVEMENT")
    pr["date"] = date_aaaammjj(pr["CB_DATE"])
    pr["qte"], pr["mont"] = nombre_fr(pr["CB_LITRES"]), nombre_fr(pr["CB_MONTANT"])
    f = Oracle("conso_fms")
    f["date"] = pd.to_datetime(f["DATE_JOUR"], format="%d/%m/%Y")
    f["ratio"] = f["LITRES_TOTAL"].astype(float) * 100 / f["DISTANCE_KM"]
    out = []
    for p in PERIODES:
        x, y = pr[entre(pr["date"], p) & (pr["qte"] != 0)], f[entre(f["date"], p)]
        out += [("carburant", "volume_litres", p, x["qte"].sum()),
                ("carburant", "prix_moyen_litre", p, div(x["mont"].sum(), x["qte"].sum())),
                ("carburant", "conso_moyenne_l100", p, y["ratio"].mean())]          # AVERAGEX : moyenne de ratios
    return out


def rapport_qhse():
    """QHSE : infractions (BI), anomalies / AT (SharePoint), autoroutes interdites (Oracle + SharePoint)."""
    inf = Oracle("infractions")
    inf["date"] = pd.to_datetime(inf["DATE_INFRACTION"], format="%d/%m/%Y")
    au = Oracle("autoroutes_interdites")
    au["date"] = pd.to_datetime(au["DATE_EVENEMENT"], format="%d/%m/%Y")
    ja = SharePoint("justif_autoroutes")
    at = SharePoint("accidents_travail")
    at["date"] = pd.to_datetime(at["Date"])
    an = SharePoint("anomalies_materiel")
    # Date.From(..., "fr-FR") : vraie date Excel conservée, texte lu en JJ/MM/AAAA
    an["date"] = an["Date signalement"].map(lambda x: pd.to_datetime(x, format="%d/%m/%Y") if isinstance(x, str) else pd.Timestamp(x))
    out = []
    for p in PERIODES:
        i, a, t, n = inf[entre(inf["date"], p)], au[entre(au["date"], p)], at[entre(at["date"], p)], an[entre(an["date"], p)]
        out += [("qhse", "nb_infractions", p, len(i)),
                ("qhse", "nb_infractions_classe5", p, int((i["CLASSE"] == 5).sum())),
                ("qhse", "nb_accidents_travail", p, len(t)),
                ("qhse", "jours_perdus", p, t["Jours d'arrêt"].fillna(0).sum()),         # IF(ISBLANK(SUM(...)), 0, ...)
                ("qhse", "passages_autoroutes_interdites", p, a["NB_PASSAGES"].sum()),
                ("qhse", "evenements_autoroutes_justifies", p, int(a["NUM_EVENEMENT"].isin(ja["ID événement"]).sum())),
                ("qhse", "nb_anomalies_materiel", p, len(n))]
    out.append(("qhse", "anomalies_a_traiter", "total", int((an["Statut"] == "A traiter").sum())))
    return out


def rapport_absences():
    """Absences des conducteurs (vue Oracle, une ligne par jour d'absence)."""
    ab = Oracle("absences")
    ab["date"] = pd.to_datetime(ab["DATE_ABSENCE"], format="%d/%m/%Y")
    out = []
    for p in PERIODES:
        x = ab[entre(ab["date"], p)]
        out += [("absences", "absents_uniques", p, x["CHAUFFEUR"].nunique()),               # DISTINCTCOUNT(CHAUFFEUR)
                ("absences", "jours_absence", p, len(x)),
                ("absences", "jours_absence_moyen_par_jour_ouvre", p, div(len(x), jours_ouvres(*PERIODES[p])))]
    return out


RAPPORTS = [rapport_activite, rapport_controle_facturation, rapport_heures, rapport_parc, rapport_atelier,
            rapport_rapprochement, rapport_carburant, rapport_qhse, rapport_absences]


def main():
    rows = [r for f in RAPPORTS for r in f()]
    df = pd.DataFrame(rows, columns=["domaine", "kpi", "periode", "valeur"])
    df.to_csv(ROOT / "data" / "legacy_kpis.csv", index=False)
    print(f"{len(df)} KPI calculés par le Power BI de départ")
    return df


if __name__ == "__main__":
    main()
