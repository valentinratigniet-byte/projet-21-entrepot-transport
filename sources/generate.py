"""Génère l'état des 6 systèmes sources d'un transporteur citerne FICTIF ("TransVal Logistique").

Chaque système garde ses propres conventions (et ses défauts), comme dans un SI de PME :
  erp/          ERP legacy type AS/400 : CSV ';' cp1252, dates AAAAMMJJ numériques, durées en secondes,
                matricules sur 6 caractères zéro-paddés, décimales à virgule, libellés avec/sans accents.
  tms.sqlite    TMS (type SQL Server) : voyages, clients, relations, atelier, visites techniques.
  compta.sqlite Comptabilité (type Sage) : écritures, n° de pièce texte 'FA0070001'.
  telematique/  Télématique / RH (type Oracle) : JSON Lines, clés MAJUSCULES, dates JJ/MM/AAAA, matricule 'C0412'.
  sharepoint/   Listes SharePoint : xlsx saisis à la main (Oui/oui/OUI, dates mixtes, cellules vides).
Toutes les données sont aléatoires (graine fixe) : aucune donnée réelle.
"""
import csv
import json
import random
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import AS_OF, ROOT, SOURCES, START  # noqa: E402
from complements import ABS_LIBELLES, AUTOROUTES, R2, TYPE_ACTIVITE, VILLES as VILLES_REF, enrichir, nom_invente  # noqa: E402

R = random.Random(21)
RP = random.Random(2122)  # profils : clients, conducteurs, tracteurs, saisonnalité, prix du gazole
RC = random.Random(2124)  # conjoncture et profils d'exploitation (générateur séparé : référentiels et noms inchangés)
END = AS_OF + timedelta(days=3)  # quelques voyages planifiés après "aujourd'hui"

ACTIVITES = {"VL": "Vrac liquide", "PU": "Pulvérulent", "AL": "Alimentaire", "CH": "Chimie", "CT": "Conteneur"}
VILLES = ["Lyon", "Saint-Étienne", "Grenoble", "Clermont-Ferrand", "Valence", "Chambéry", "Annecy", "Roanne", "Feyzin",
          "Vienne", "Bourg-en-Bresse", "Genève", "Turin", "Milan", "Villeurbanne", "Montélimar", "Aurillac",
          "Le Puy-en-Velay", "Moulins", "Vichy"]


def personne():
    """Nom et prénom inventés. Les deux tirages de R historiques (choix dans 30 noms et 20 prénoms) sont conservés
    pour que la suite de la génération (et donc chaque chiffre) reste identique."""
    R.randrange(30), R.randrange(20)
    return nom_invente(), nom_invente((2, 2))


def nom_client():
    R.randrange(30)  # même tirage que l'ancien choix de nom
    return nom_invente()


SECTEURS = ["Chimie", "Agro", "Pétrole", "Matériaux", "Logistique", "Pharma"]

# Profils d'activité : distance chargée (km) et prix au km très différents d'un métier à l'autre
KM_ACTIVITE = {"VL": (220, 560), "PU": (110, 380), "AL": (60, 320), "CH": (160, 520), "CT": (30, 150)}
PRIX_KM = {"VL": (1.9, 2.5), "PU": (2.2, 2.9), "AL": (2.5, 3.2), "CH": (3.0, 3.9), "CT": (3.4, 4.6)}
# saisonnalité mensuelle : creux d'août et de fin d'année, récoltes (alimentaire), chantiers de printemps (pulvérulent)
_BASE = [0.92, 0.95, 1.02, 1.03, 1.0, 1.02, 0.9, 0.66, 1.05, 1.08, 1.04, 0.84]
SAISON = {a: list(_BASE) for a in ("VL", "PU", "AL", "CH", "CT")}
SAISON["AL"][8], SAISON["AL"][9] = 1.3, 1.28
for _m in (2, 3, 4):
    SAISON["PU"][_m] += 0.12
SAISON["CH"] = [0.97 + 0.03 * (x - 1) for x in _BASE]  # chimie : contrats lissés, peu saisonnière
# conjoncture mensuelle : (niveau, facteur de volume, probabilité) -> des mois franchement différents à analyser
CONJONCTURE = [("exceptionnel", 1.28, 0.08), ("bon", 1.10, 0.22), ("normal", 1.0, 0.32), ("médiocre", 0.86, 0.2),
               ("mauvais", 0.74, 0.12), ("catastrophique", 0.55, 0.06)]
# durée de déchargement : citernes chimie / vrac liquide plus longues (raccordements, nettoyage), conteneurs rapides
# franchise de mise à disposition (contrat type citerne, livraison sur plage horaire) : 1 h 30 au chargement
# + 1 h 30 à la livraison ; au-delà, l'attente est facturable au client
FRANCHISE_SITE_H, TARIF_ATTENTE_H = 3.0, 55.0
LIVRAISON_ACTIVITE = {"VL": 1.25, "PU": 1.1, "AL": 0.9, "CH": 1.35, "CT": 0.75}
TYPE_CONTRAT = {186.0: "Grand routier", 169.0: "Courte distance", 151.67: "Remplaçant 35 h", 121.33: "Remplaçant temps partiel"}
CONSO_MARQUE = [0.305, 0.292, 0.318, 0.334, 0.326]  # L/km de base par marque (index = numéro de tracteur % 5)


# ---------------------------------------------------------------- calendrier
def paques(y):
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    g = (8 * b + 13) // 25
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    mois = (h + l_ - 7 * m + 114) // 31
    return date(y, mois, (h + l_ - 7 * m + 114) % 31 + 1)


def feries(y):
    p = paques(y)
    return {date(y, 1, 1): "Jour de l'an", p + timedelta(1): "Lundi de Pâques", date(y, 5, 1): "Fête du travail",
            date(y, 5, 8): "Victoire 1945", p + timedelta(39): "Ascension", p + timedelta(50): "Lundi de Pentecôte",
            date(y, 7, 14): "Fête nationale", date(y, 8, 15): "Assomption", date(y, 11, 1): "Toussaint",
            date(y, 11, 11): "Armistice", date(y, 12, 25): "Noël"}


FERIES = {}
for _y in range(START.year, END.year + 2):
    FERIES.update(feries(_y))


def jours(a, b):
    d = a
    while d <= b:
        yield d
        d += timedelta(1)


def ouvre(d):
    return d.weekday() < 5 and d not in FERIES


def ymd(d):
    return int(d.strftime("%Y%m%d"))


def fr(x, n=2):  # décimale à virgule (export AS/400 en culture fr)
    return f"{x:.{n}f}".replace(".", ",")


# ---------------------------------------------------------------- référentiels
def referentiels():
    mats = R.sample(range(100, 3000), 60)
    tracteurs = [{"num": 1500 + i, "activite": list(ACTIVITES)[i % 5], "mise_service": date(2017 + i % 7, 1 + i % 12, 1),
                  "util": RP.uniform(0.72, 0.99), "conso": CONSO_MARQUE[(1500 + i) % 5] * RP.uniform(0.94, 1.08)}
                 for i in range(48)]
    conducteurs = []
    for i, m in enumerate(mats):
        titulaire = i < 48
        entree = date(2010 + i % 14, 1 + i % 12, 1 + i % 27)
        sortie = date(2025, 3, 31) if i in (7, 31) else None  # deux départs
        conducteurs.append({"mat": m, **dict(zip(("nom", "prenom"), personne())),
                            "activite": tracteurs[i]["activite"] if titulaire else list(ACTIVITES)[i % 5],
                            "tracteur": tracteurs[i]["num"] if titulaire else None, "entree": entree, "sortie": sortie})
    # remplacement des deux partants par deux embauches au 1er avril 2025
    for i in (7, 31):
        new = {"mat": 3000 + i, **dict(zip(("nom", "prenom"), personne())), "activite": conducteurs[i]["activite"],
               "tracteur": conducteurs[i]["tracteur"], "entree": date(2025, 4, 1), "sortie": None}
        conducteurs.append(new)
    clients = [{"cd": f"CLI{i:03d}", "nom": f"{R.choice(SECTEURS)} {nom_client()} {R.choice(['SA', 'SAS', 'SpA', 'GmbH'])}",
                "ville": R.choice(VILLES), "pays": "FR"} for i in range(1, 41)]
    # profils clients : quelques grands comptes et une longue traîne (loi de puissance), politique tarifaire propre
    rangs = RP.sample(range(1, 41), 40)
    for c, rg in zip(clients, rangs):
        c["poids"] = 1 / rg ** 0.8
        c["niveau_prix"] = RP.choice([0.8, 0.9, 1.0, 1.0, 1.0, 1.1, 1.22])
        c["attente"] = RP.choice([0.05, 0.12, 0.25, 0.4, 0.65])  # inutilisé (l'attente découle du temps sur site) : tiré pour garder la séquence des profils
        c["qte"] = RP.uniform(15, 29)
    relations = []
    for i in range(1, 121):
        dep, arr = R.sample(VILLES, 2)
        act = list(ACTIVITES)[i % 5]
        km = RP.randint(*KM_ACTIVITE[act])
        cli = RP.choice(clients)
        relations.append({"cd": f"REL{i:04d}", "client": cli["cd"], "dep": dep, "arr": arr, "km": km, "activite": act,
                          "prix": round(km * RP.uniform(*PRIX_KM[act]) * cli["niveau_prix"] + 180, 2),
                          "autoroute": R.uniform(0.2, 0.9), "creation": date(2018 + i % 6, 1 + i % 12, 1),
                          "poids": cli["poids"] * RP.uniform(0.4, 1.6)})
    # profils conducteurs : amplitude (grand routier -> heures sup), style de conduite, absentéisme, rigueur
    for c in conducteurs:
        c["amplitude"] = RP.choices([(0.4, 1.2), (1.6, 3.0), (2.8, 4.2)], (20, 45, 35))[0]
        # contrat mensualisé : grand routier 186 h (43 h/sem. avec équivalence), courte distance 169 h (39 h/sem.),
        # remplaçants à 151,67 h (35 h) ou à temps partiel (121,33 h = 28 h/sem.)
        if c["tracteur"] is None:
            c["base"] = RP.choice([151.67, 121.33])
        elif c["amplitude"][0] >= 2.8 or (c["activite"] in ("VL", "CH") and c["amplitude"][0] >= 1.6):
            c["base"] = 186.0
        else:
            c["base"] = 169.0
        c["effectif"] = RP.choices(["CDI", "CDD"], (85, 15))[0]
    # mouvements RH de 2026 : passages courte distance -> grand routier, titularisations CDD -> CDI
    mouvements = []
    titulaires_cd = [c for c in conducteurs if c["base"] == 169.0 and c["sortie"] is None]
    for c in RP.sample(titulaires_cd, 6):
        effet = date(AS_OF.year, RP.randint(4, AS_OF.month), 1)
        mouvements += [(c["mat"], effet, "TYPE_CONTRAT", "Courte distance", "Grand routier"),
                       (c["mat"], effet, "BASE_MENSUELLE", 169.0, 186.0)]
        c["base_avant"], c["effet"], c["base"] = 169.0, effet, 186.0
    for c in RP.sample([c for c in conducteurs if c["effectif"] == "CDD" and c["sortie"] is None], 3):
        mouvements.append((c["mat"], date(AS_OF.year, RP.randint(2, AS_OF.month), 1), "TYPE_EFFECTIF", "CDD", "CDI"))
        c["effectif"] = "CDI"
    for c in conducteurs:
        c["type_contrat"] = TYPE_CONTRAT[c["base"]]
        c["style"] = RP.choice([0.9, 0.95, 1.0, 1.0, 1.05, 1.12, 1.2])  # facteur de consommation
        c["maladie"] = RP.choices([0, 1, 2, 4, 8], (30, 30, 20, 13, 7))[0]  # arrêts maladie max par an
        c["a_justifier"] = RP.choice([0.05, 0.15, 0.3, 0.45, 0.7])
        c["infractions"] = RP.lognormvariate(0, 0.9)
    return tracteurs, conducteurs, clients, relations, mouvements


def absences(conducteurs):
    """Une ligne par conducteur et par jour d'absence (comme la vue Oracle des absences)."""
    out = {}
    for c in conducteurs:
        for y in range(START.year, AS_OF.year + 1):
            for motif, n, duree in (("CP", 3, (5, 10)), ("AM", RP.randint(0, c["maladie"]), (1, 9)),
                                    ("ABS", RP.randint(0, 1 + c["maladie"] // 4), (1, 1))):
                for _ in range(n):
                    d0 = date(y, 1, 1) + timedelta(R.randint(0, 360))
                    for k in range(R.randint(*duree)):
                        d = d0 + timedelta(k)
                        if START <= d <= AS_OF and ouvre(d):
                            out[(c["mat"], d)] = motif
    return out


# ---------------------------------------------------------------- génération
def main():
    tracteurs, conducteurs, clients, relations, mouvements = referentiels()
    rel_par_act = {a: [r for r in relations if r["activite"] == a] for a in ACTIVITES}
    poids_rel = {a: [r["poids"] for r in rs] for a, rs in rel_par_act.items()}
    client_de = {c["cd"]: c for c in clients}
    # prix du gazole : marche aléatoire mensuelle avec rappel vers 1,75 €/L (et non une pente régulière)
    prix_gazole, px = {}, 1.72
    for y in range(START.year, END.year + 1):
        for mo in range(1, 13):
            px += 0.25 * (1.75 - px) + RP.gauss(0, 0.045)
            prix_gazole[(y, mo)] = px
    absent = absences(conducteurs)
    remplacants = [c for c in conducteurs if c["tracteur"] is None]
    conj = {}
    for y in range(START.year, END.year + 1):
        for mo in range(1, 13):
            _, f, _ = RC.choices(CONJONCTURE, [x[2] for x in CONJONCTURE])[0]
            for a in ACTIVITES:  # chaque métier suit la tendance avec ses propres écarts
                conj[(y, mo, a)] = f * RC.uniform(0.92, 1.08)
    semaine = {}  # aléa hebdomadaire (météo, grèves, ponts, commandes groupées)
    for d in jours(START, END):
        semaine.setdefault(d.isocalendar()[:2], RC.uniform(0.88, 1.12))
    site = {c["cd"]: RC.choice([0.6, 0.9, 1.2, 1.6, 2.3]) for c in clients}  # rapidité du site de livraison (h)
    remplissage = {r["cd"]: RC.uniform(0.45, 1.0) for r in relations}  # taux de chargement propre à chaque flux

    def actif(c, d):
        return c["entree"] <= d and (c["sortie"] is None or d <= c["sortie"])

    def titulaire(t, d):
        cands = [c for c in conducteurs if c["tracteur"] == t["num"] and actif(c, d)]
        return cands[0] if cands else None

    # --- atelier d'abord : les pannes immobilisent les tracteurs
    ots, immobile, num_fact = [], set(), 70000
    ot_id = 500000
    for t in tracteurs:
        for m0 in jours(START, AS_OF):
            if m0.day != 1:
                continue
            evts = []
            if (m0.month + t["num"]) % 3 == 0:
                evts.append("PREVENTIF")
            age = (m0 - t["mise_service"]).days / 365
            evts += ["PANNE"] * sum(R.random() < 0.06 + 0.035 * age for _ in range(2))  # les vieux tracteurs cassent plus
            if R.random() < 0.04:
                evts.append("SINISTRE")
            if t["activite"] in ("AL", "CH"):
                evts.append("LAVAGE")
            if m0.month == t["mise_service"].month:
                evts.append("VISITE TECHNIQUE")
            if m0.month == (t["mise_service"].month + 5) % 12 + 1:
                evts.append("VISITE OBLIGATOIRE")
            for fam in evts:
                d = m0 + timedelta(R.randint(0, 27))
                if d > AS_OF:
                    continue
                externe = fam in ("VISITE TECHNIQUE", "VISITE OBLIGATOIRE", "LAVAGE") or (fam == "PANNE" and R.random() < 0.4) \
                    or (fam == "SINISTRE" and R2.random() < 0.6)  # 40 % des sinistres réparés en interne
                raison = {"PREVENTIF": "ENT", "SINISTRE": "SIN", "LAVAGE": "LAV", "VISITE TECHNIQUE": "VT",
                          "VISITE OBLIGATOIRE": "VO"}.get(fam) or R.choice(["COR", "COR", "DEP"])
                pieces = {"PREVENTIF": R.uniform(150, 600), "PANNE": R.uniform(80, 2500), "SINISTRE": R.uniform(800, 6000),
                          "LAVAGE": 0, "VISITE TECHNIQUE": 0, "VISITE OBLIGATOIRE": 0}[fam]
                h_mo = {"PREVENTIF": R.uniform(2, 5), "PANNE": R.uniform(1, 12), "SINISTRE": R.uniform(4, 30),
                        "LAVAGE": 0.0, "VISITE TECHNIQUE": 1.0, "VISITE OBLIGATOIRE": 0.5}[fam]
                presta = {"LAVAGE": R.uniform(70, 120), "VISITE TECHNIQUE": 165.0, "VISITE OBLIGATOIRE": 95.0}.get(fam, 0)
                cout = round(pieces + h_mo * 48 + presta, 2)
                ot_id += 1
                nf = None
                if externe:
                    num_fact += 1
                    nf = num_fact
                ots.append({"ot_id": ot_id, "date_ot": d, "tracteur": t["num"], "famille": fam, "raison": raison,
                            "type_document": "Facture externe" if externe else "Facture interne",
                            "cout_pieces": round(pieces, 2), "heures_mo": round(h_mo, 2), "cout_mo": round(h_mo * 48, 2),
                            "cout_total": cout, "num_facture": nf})
                if fam in ("PANNE", "SINISTRE"):
                    for k in range(R.randint(1, 3)):
                        immobile.add((t["num"], d + timedelta(k)))

    # --- voyages, pointages, chrono, affectations, carburant, FMS
    voyages, historique, pointages, chrono, affect, prelev, fms = [], [], [], [], [], [], []
    vid, seq = 1_000_000, 0
    for d in jours(START, END):
        if not ouvre(d):
            continue
        occupes = set()
        for t in tracteurs:
            if (t["num"], d) in immobile:
                affect.append({"date": d, "tract": t["num"], "mat": None, "activ": "MAIN", "type": "M"})
                continue
            cj = conj[(d.year, d.month, t["activite"])]
            if R.random() > min(0.99, t["util"] * SAISON[t["activite"]][d.month - 1] * cj * semaine[d.isocalendar()[:2]]):
                continue
            c = titulaire(t, d)
            if c is None or (c["mat"], d) in absent:
                libres = [x for x in remplacants if actif(x, d) and (x["mat"], d) not in absent and x["mat"] not in occupes]
                if not libres:
                    continue
                c = R.choice(libres)
            occupes.add(c["mat"])
            affect.append({"date": d, "tract": t["num"], "mat": c["mat"], "activ": t["activite"], "type": "M"})
            rel = R.choices(rel_par_act[t["activite"]], poids_rel[t["activite"]])[0] if R.random() > 0.04 else None  # 4 % de "spot"
            cli = client_de[rel["client"]] if rel else R.choice(clients)
            km_c = round((rel["km"] if rel else R.randint(80, 300)) * R.uniform(0.95, 1.05))
            approche = min(1.0, km_c / 250) + 0.15  # trajets à vide proportionnés à la distance (court = peu de vide)
            km_av, km_ap = round(R.randint(0, 90) * approche), round(R.randint(0, 120) * approche)
            km_t = km_c + km_av + km_ap
            # tension sur les prix les bons mois (spot mieux payé), remises les mauvais
            ca = round((rel["prix"] if rel else km_c * 2.6 + 150) * R.uniform(0.96, 1.06) * (1 + (cj - 1) * 0.35), 2)
            tps_c, tps_l = round(R.uniform(0.8, 2.4), 2), R.uniform(0.7, 2.0)
            hiver = 1.15 if d.month in (11, 12, 1, 2) else 1.0
            tps_l = round(min(6.0, site[cli["cd"]] * LIVRAISON_ACTIVITE[t["activite"]] * hiver * (1 + (cj - 1) * 0.5)
                              * (tps_l / 1.35) * RC.lognormvariate(0, 0.25)), 2)
            route = km_t / 62
            share = rel["autoroute"] if rel else 0.5
            peage_c, peage_v = round(km_c * share * 0.11, 2), round((km_av + km_ap) * share * 0.11, 2)
            ecot_c, ecot_v = round(km_c * 0.012, 2), round((km_av + km_ap) * 0.012, 2)
            lav = 85.0 if t["activite"] in ("AL", "CH") and R.random() < 0.6 else 0.0
            couts = round(km_t * 0.62 + (route + tps_c + tps_l) * 31 + peage_c + peage_v + ecot_c + ecot_v + lav, 2)
            ca_rep = round(ca * R.uniform(0.97, 1.03), 2)
            marge = round(ca_rep - couts, 2)
            attente = round(max(0.0, tps_c + tps_l - FRANCHISE_SITE_H), 2)  # temps sur site au-delà de la franchise
            d_livre = d + timedelta(1 if R.random() < 0.35 else 0)
            dd = R.random() < 0.05
            vid += 1
            statut = "PLANIFIE" if d_livre > AS_OF else ("ANNULE" if R.random() < 0.02 else "LIVRE")
            fin_jour = datetime.combine(AS_OF, datetime.min.time()) + timedelta(hours=23)
            if statut == "PLANIFIE":  # saisi la veille du chargement
                maj = min(datetime.combine(d - timedelta(1), datetime.min.time()) + timedelta(hours=17), fin_jour)
            else:
                maj = min(datetime.combine(d_livre + timedelta(1), datetime.min.time()) + timedelta(hours=R.randint(6, 20)), fin_jour)
            v = {"voyage_id": vid, "date_charge": d, "date_livre": d_livre, "client_cd": cli["cd"],
                 "relation_cd": rel["cd"] if rel else None, "activite_cd": t["activite"], "tracteur": t["num"],
                 "remorque": f"R{t['num'] + 2000}", "salarie_cd": c["mat"], "statut": statut,
                 "ca_facture": ca, "ca_reparti": ca_rep, "qt_livre": round(min(29.5, cli["qte"] * R.uniform(0.85, 1.15) * (remplissage[rel["cd"]] if rel else RC.uniform(0.4, 1.0))
                                       * (1 + (cj - 1) * 0.4)), 3),
                 "km_charge": km_c, "km_vide_av": km_av, "km_vide_ap": km_ap, "km_total": km_t,
                 "tps_charge_h": tps_c, "tps_livre_h": tps_l, "tps_total_h": round(route + tps_c + tps_l, 2),
                 "mcv_couts_variables": couts, "mcv_marge": marge,
                 "mcv_marge_lissee": None if R.random() < 0.3 else round(marge * R.uniform(0.9, 1.1), 2),
                 "mcv_peage_charge": peage_c, "mcv_peage_vide": peage_v, "mcv_ecot_charge": ecot_c, "mcv_ecot_vide": ecot_v,
                 "mcv_lavage_int": lav, "attente_h": attente, "attente_a_facturer_eur": round(attente * TARIF_ATTENTE_H, 2),
                 "livraison_samedi": int(d_livre.weekday() == 5), "double_depotage": int(dd), "updated_at": maj}
            regul = maj + timedelta(days=R.randint(20, 60))
            if statut == "LIVRE" and R.random() < 0.08 and regul <= fin_jour:  # régularisation tardive -> CDC à gérer à l'import
                historique.append({**v, "valid_to": regul})  # version initiale conservée (table temporelle)
                v["ca_facture"] = round(ca * R.uniform(0.9, 1.08), 2)
                v["updated_at"] = regul
            voyages.append(v)
            if d > AS_OF:
                continue

            # pointages (heures hors conduite) du conducteur
            def pt(lib, h, forf=False):
                nonlocal seq
                seq += 1
                pointages.append({"seq": seq, "date": d, "mat": c["mat"], "tract": t["num"], "lib": lib, "sec": int(h * 3600),
                                  "type": R.choices("ESM", (60, 35, 5))[0], "valid": R.choices("VFA", (80, 17, 3))[0],
                                  "exclu": "X" if R.random() < 0.02 else "", "forf": "F" if forf else "",
                                  "valf": int(h * 3600) if forf else 0})
            pt("Chargement" if rel else "Chargement hors mission", tps_c, R.random() < 0.1)
            pt("Déchargement", tps_l, R.random() < 0.1)
            if lav:
                pt("Lavage intérieur citerne", 1.0)
            if R.random() < 0.1:
                pt("Lavage extérieur citerne", 0.5)
            if R.random() < 0.35:
                pt("Plein gazole", R.uniform(0.25, 0.5))
            if R.random() < 0.25:
                pt(R.choice(["Décrochage", "Decrochage"]), 0.25)  # même activité, deux orthographes en source
                pt("Raccrochage", 0.25)
            if R.random() < c["a_justifier"]:
                pt("Temps à justifier", R.uniform(0.2, 1.5))
            if R.random() < 0.01:
                pt("Visite VT / VO", 1.5)
            travail = tps_c + tps_l + 0.3
            dispo = R.uniform(*c["amplitude"])
            repos = R.uniform(0, 0.3) if R.random() < 0.4 else 0
            dispo = max(0.0, min(dispo, 12 - route - travail - repos))  # temps de service plafonné à 12 h par jour
            chrono.append({"date": d, "mat": c["mat"], "con": int(route * 3600), "tra": int(travail * 3600),
                           "dis": int(dispo * 3600), "rep": int(repos * 3600)})
            fms.append({"TRACTEUR": t["num"], "DATE_JOUR": d.strftime("%d/%m/%Y"), "DISTANCE_KM": km_t,
                        "LITRES_CONDUITE": f"{km_t * t['conso'] * c['style'] * R.uniform(0.97, 1.03):.1f}", "LITRES_TOTAL": None})
            fms[-1]["LITRES_TOTAL"] = f"{float(fms[-1]['LITRES_CONDUITE']) * R.uniform(1.02, 1.08):.1f}"
            if R.random() < 0.3:
                pompe = R.randint(1, 4)
                qte = 0 if R.random() < 0.01 else round(R.uniform(250, 550), 2)
                base = prix_gazole[(d.year, d.month)] + 0.04 * pompe
                prelev.append({"date": d, "pompe": pompe, "qte": qte, "mont": round(qte * base, 2), "tract": t["num"], "mat": c["mat"]})

    # --- événements facturés, justifications
    evts, justif_att = [], []
    for v in voyages:
        if v["statut"] != "LIVRE":
            continue
        if v["attente_a_facturer_eur"] > 0:
            if R.random() < 0.65:
                evts.append((v["voyage_id"], "ATT", v["attente_a_facturer_eur"] if R.random() > 0.1 else round(v["attente_a_facturer_eur"] * 0.8, 2)))
            elif R.random() < 0.5:
                justif_att.append((f"{' ' if R.random() < 0.2 else ''}{v['voyage_id']}", R.choice(["Oui", "oui", "OUI "]),
                                   R.choice(["Attente imputable au transporteur", "Retard chauffeur", "Geste commercial", ""])))
            elif R.random() < 0.3:
                justif_att.append((str(v["voyage_id"]), "Non", "À refacturer"))
        if v["mcv_lavage_int"] and R.random() < 0.8:
            evts.append((v["voyage_id"], "LAV", 85.0))
        if v["livraison_samedi"] and R.random() < 0.7:
            evts.append((v["voyage_id"], "SAM", 120.0))
        if v["double_depotage"] and R.random() < 0.75:
            evts.append((v["voyage_id"], "DD", 90.0))

    # --- compléments pour les rapports (générateur séparé : ne change aucune valeur ci-dessus)
    cx = enrichir(tracteurs, conducteurs, clients, relations, voyages, historique, ots, prelev, fms, absent, chrono, AS_OF, START)
    factures = {(e[0], e[1]) for e in evts}
    cx["justif_lav"] = [(f"CMR{v['voyage_id']}", R2.choice(["Oui", "Non"]), R2.choice(["Lavage non réalisé", "Client équipé", "Oubli de facturation", ""]))
                        for v in voyages if v["statut"] == "LIVRE" and v["mcv_lavage_int"] and (v["voyage_id"], "LAV") not in factures and R2.random() < 0.5]

    # --- écrire les sources
    if SOURCES.exists():
        for f in sorted(SOURCES.rglob("*"), reverse=True):
            f.unlink() if f.is_file() else f.rmdir()
    for sub in ("erp", "telematique", "sharepoint"):
        (SOURCES / sub).mkdir(parents=True, exist_ok=True)

    write_erp(pointages, chrono, affect, prelev, conducteurs, absent, cx)
    write_tms(voyages, historique, clients, relations, ots, evts, cx)
    write_compta(ots, tracteurs)
    write_telematique(conducteurs, absent, fms, tracteurs, cx, mouvements)
    write_sharepoint(justif_att, conducteurs, tracteurs, cx)
    write_seed_feries()
    print(f"voyages={len(voyages)} pointages={len(pointages)} chrono={len(chrono)} ots={len(ots)} prelev={len(prelev)}")


def write_csv(name, header, rows):
    with open(SOURCES / "erp" / f"{name}.csv", "w", newline="", encoding="cp1252") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(header)
        w.writerows(rows)


HS_25 = 34.67  # heures sup. majorées à 25 % (8 h/sem. au-delà de la base), 50 % au-delà


def write_erp(pointages, chrono, affect, prelev, conducteurs, absent, cx):
    contrat = {c["mat"]: c for c in conducteurs}

    def base_du_mois(m, y, mo):
        c = contrat[m]
        return c["base_avant"] if "effet" in c and date(y, mo, 1) < c["effet"] else c["base"]
    write_csv("POINTAGE", ["PT_SEQ", "PT_DATE", "NUM_MATR", "NUM_TRACT", "PT_LIBACT", "PT_DUREE_S", "PT_TYPE", "PT_STATUT", "PT_EXCLU", "PT_FORFAIT", "PT_VALFORF"],
              [(p["seq"], ymd(p["date"]), f"{p['mat']:04d}".ljust(6), p["tract"], p["lib"].ljust(28), p["sec"], p["type"],
                p["valid"], p["exclu"].ljust(1), p["forf"].ljust(1), p["valf"]) for p in pointages])
    write_csv("CHRONO", ["CH_DATE", "CH_MATR", "CH_CONDUITE_S", "CH_TRAVAIL_S", "CH_DISPO_S", "CH_REPOS_S", "CH_SERVICE_S"],
              [(ymd(c["date"]), c["mat"], c["con"], c["tra"], c["dis"], c["rep"], c["con"] + c["tra"] + c["dis"] + c["rep"]) for c in chrono])
    write_csv("AFFECTATION", ["AF_DATE", "AF_MATR", "AF_TRACT", "AF_ACTIV", "AF_TYPE"],
              [(ymd(a["date"]), f"{a['mat']:04d}" if a["mat"] else "    ", a["tract"], a["activ"], a["type"]) for a in affect])
    # compteurs mensuels de paie : matricule sur 6 car. zéro-paddé, mois clos uniquement
    heures = {}
    for c in chrono:
        k = (c["mat"], c["date"].year, c["date"].month)
        heures[k] = heures.get(k, 0) + (c["con"] + c["tra"] + c["dis"] + c["rep"]) / 3600
    rows = []
    for (m, y, mo), h in sorted(heures.items()):
        if date(y, mo, 1) >= date(AS_OF.year, AS_OF.month, 1):
            continue
        b, taux = base_du_mois(m, y, mo), cx["taux"][m]
        hs = max(0.0, h - b)
        payees = max(h, b)  # mensualisation : la base est payée même si le réalisé est inférieur
        salaire = payees * taux + min(hs, HS_25) * taux * 0.25 + max(0.0, hs - HS_25) * taux * 0.5
        rows.append((f"{m:06d}", y, mo, fr(h), fr(b), fr(hs), fr(payees), fr(salaire)))
    write_csv("COMPTEUR_PAIE", ["PA_MATR", "PA_ANNEE", "PA_MOIS", "PA_H_REAL", "PA_H_BASE", "PA_H_SUP", "PA_H_PAYEES", "PA_SAL_BRUT"], rows)
    a = cx["activcha"]
    write_csv("ACTIVITE_CHAUFFEUR", list(a[0]), [(x["FR_DATE"], f"{x['FR_MATR']:04d}", x["FR_PREST"], x["FR_COMPTE"], x["FR_LIBELLE"].ljust(20), fr(x["FR_QTE"]),
                                        fr(x["FR_COUT_1"]), fr(x["FR_COUT_2"]), fr(x["FR_COUT_3"]), x["FR_VERIF"]) for x in a])
    write_csv("HEURESMEC", ["MATRICULE", "NOM", "PRENOM", "ANNEE", "MOIS", "HM_PAYEES"],
              [(h["matricule"], h["nom"], h["prenom"], h["annee"], h["mois"], fr(h["heures_payees"])) for h in cx["heures_mec"]])
    write_csv("GMAO", ["GM_DATE", "GM_MECA", "GM_ARTICLE", "GM_COUT", "GM_HEURES"],
              [(ymd(g["date"]), g["mecanicien"], g["article"], fr(g["cout"]), fr(g["heures"])) for g in cx["gmao"]])
    write_csv("PRELEVEMENT", ["CB_DATE", "CB_POMPE", "NUM_TRACT", "NUM_MATR", "CB_LITRES", "CB_MONTANT"],
              [(ymd(p["date"]), p["pompe"], p["tract"], f"{p['mat']:04d}", fr(p["qte"]), fr(p["mont"])) for p in prelev])
    four = {1: "TOTALENERGIES    FR", 2: "TOTALENERGIES    IT", 3: "ESSO DISTRIB     FR", 4: "DYNEFF           FR"}
    write_csv("PARAM", ["PR_CLE", "PR_LIB1", "PR_LIB2"], [(f"POMPE_GO_{k}", v, cx["pompe_ville"][k]) for k, v in four.items()])


def write_tms(voyages, historique, clients, relations, ots, evts, cx):
    db = SOURCES / "tms.sqlite"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE client (client_cd TEXT PRIMARY KEY, client_nom TEXT, client_ville TEXT, client_pays TEXT)")
    con.executemany("INSERT INTO client VALUES (?,?,?,?)", [(c["cd"], c["nom"], c["ville"], c["pays"]) for c in clients])
    con.execute("""CREATE TABLE relation (relation_cd TEXT PRIMARY KEY, client_cd TEXT, depart_ville TEXT, arrivee_ville TEXT,
                   distance_km INT, activite_cd TEXT, prix REAL, date_creation TEXT, type_relation TEXT, location INT,
                   marchandise TEXT, depart_nom TEXT, arrivee_nom TEXT, prix_date TEXT)""")
    con.executemany("INSERT INTO relation VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    [(r["cd"], r["client"], r["dep"], r["arr"], r["km"], r["activite"], r["prix"], r["creation"].isoformat(), r["type"],
                      r["location"], r["marchandise"], r["depart_nom"], r["arrivee_nom"], r["prix_date"].isoformat()) for r in relations])
    con.execute("CREATE TABLE ville (ville TEXT PRIMARY KEY, code_postal TEXT, departement TEXT, pays TEXT, latitude REAL, longitude REAL)")
    con.executemany("INSERT INTO ville VALUES (?,?,?,?,?,?)", [(k, *v) for k, v in VILLES_REF.items()])
    for name, rows in (("client_indexation", cx["indexation"]), ("entite", cx["materiel"]), ("atelier_ligne", cx["lignes"])):
        cols_ = list(rows[0])
        con.execute(f"CREATE TABLE {name} ({', '.join(cols_)})")
        con.executemany(f"INSERT INTO {name} VALUES ({','.join('?' * len(cols_))})",
                        [tuple(r[k].isoformat() if isinstance(r[k], date) else r[k] for k in cols_) for r in rows])
    cols = list(voyages[0])
    con.execute(f"CREATE TABLE voyage ({', '.join(cols)})")
    con.executemany(f"INSERT INTO voyage VALUES ({','.join('?' * len(cols))})",
                    [tuple(v[k].isoformat(sep=" ") if isinstance(v[k], datetime) else v[k].isoformat() if isinstance(v[k], date) else v[k]
                           for k in cols) for v in voyages])
    hcols = cols + ["valid_to"]
    con.execute(f"CREATE TABLE voyage_history ({', '.join(hcols)})")
    con.executemany(f"INSERT INTO voyage_history VALUES ({','.join('?' * len(hcols))})",
                    [tuple(v[k].isoformat(sep=" ") if isinstance(v[k], datetime) else v[k].isoformat() if isinstance(v[k], date) else v[k]
                           for k in hcols) for v in historique])
    con.execute("CREATE TABLE evenement_facture (voyage_id INT, type_evt TEXT, montant_facture REAL)")
    con.executemany("INSERT INTO evenement_facture VALUES (?,?,?)", evts)
    cols = list(ots[0])
    con.execute(f"CREATE TABLE atelier_ot ({', '.join(cols)})")
    con.executemany(f"INSERT INTO atelier_ot VALUES ({','.join('?' * len(cols))})",
                    [tuple(o[k].isoformat() if isinstance(o[k], date) else o[k] for k in cols) for o in ots])
    vts = [(o["ot_id"], o["date_ot"].isoformat(), o["tracteur"], "VT" if o["raison"] == "VT" else "VO",
            R.choices(["Valide", "valide ", "VALIDE", "Refus"], (78, 6, 4, 12))[0])
           for o in ots if o["raison"] in ("VT", "VO")]
    con.execute("CREATE TABLE visite_technique (ot_id INT, date_visite TEXT, tracteur INT, type_visite TEXT, resultat TEXT)")
    con.executemany("INSERT INTO visite_technique VALUES (?,?,?,?,?)", vts)
    con.commit()
    con.close()


def write_compta(ots, tracteurs):
    con = sqlite3.connect(SOURCES / "compta.sqlite")
    con.execute("""CREATE TABLE ecriture (ecriture_id INTEGER PRIMARY KEY, date_piece TEXT, num_piece TEXT, compte TEXT,
                   montant_debit REAL, montant_credit REAL, libelle TEXT, journal TEXT, compte_tiers TEXT, intitule_tiers TEXT,
                   code_analytique TEXT, libelle_analytique TEXT, code_frais TEXT, libelle_frais TEXT, societe TEXT, cloture TEXT)""")
    act = {t["num"]: t["activite"] for t in tracteurs}
    frais = {"6155": "Entretien et réparations", "6063": "Pièces détachées"}

    def compta_extra(fournisseur, activite, d):
        code = R2.choice(list(frais))
        return ("ACH", f"401{sum(map(ord, fournisseur)) % 900 + 100}", fournisseur.upper(), f"AN{activite}", f"Activité {activite}",
                code, frais[code], "01", "Oui" if d < date(AS_OF.year, 1, 1) else "Non")
    rows, eid = [], 0
    for o in ots:
        if o["num_facture"] is None or R.random() < 0.04:  # 4 % des factures atelier jamais saisies en compta
            continue
        ht = o["cout_total"]
        if R.random() < 0.03:  # 3 % d'écarts de saisie
            ht = round(ht + R.choice([-1, 1]) * R.uniform(0.5, 50), 2)
        eid += 1
        rows.append((eid, min(o["date_ot"] + timedelta(R.randint(0, 10)), AS_OF).isoformat(), f"FA{o['num_facture']:07d}", "615500",
                     ht, 0.0, f"Entretien tracteur {o['tracteur']} - {o['famille'].lower()}",
                     *compta_extra(o["fournisseur"], act[o["tracteur"]], o["date_ot"])))
    for k in range(int(len(rows) * 0.02)):  # 2 % de pièces comptables sans OT atelier
        eid += 1
        d = START + timedelta(R.randint(0, (AS_OF - START).days))
        rows.append((eid, d.isoformat(), f"FA{79000 + k:07d}", "615500", round(R.uniform(80, 1500), 2), 0.0, "Entretien divers",
                     *compta_extra(R2.choice(["PNEUS SERVICE GRENOBLE", "TRUCK SERVICES SAINT-ÉTIENNE"]), R2.choice(list(TYPE_ACTIVITE)), d)))
    con.executemany(f"INSERT INTO ecriture VALUES ({','.join('?' * 16)})", rows)
    con.commit()
    con.close()


def write_jsonl(name, rows):
    with open(SOURCES / "telematique" / f"{name}.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")


def write_telematique(conducteurs, absent, fms, tracteurs, cx, mouvements):
    write_jsonl("conducteurs", [{"MATRICULE": f"C{c['mat']:04d}", "NOM": c["nom"].upper(), "PRENOM": c["prenom"],
                                 "ACTIVITE": c["activite"], "DATE_ENTREE": c["entree"].strftime("%d/%m/%Y"),
                                 "DATE_SORTIE": c["sortie"].strftime("%d/%m/%Y") if c["sortie"] else None,
                                 "DEPARTEMENT": "CHA", "TYPE_EFFECTIF": c["effectif"], "TYPE_CONTRAT": c["type_contrat"],
                                 "BASE_MENSUELLE": c["base"]} for c in conducteurs])
    # journal RH (audit) : sert à reconstituer la photo du référentiel à la date de chaque import
    write_jsonl("conducteurs_mouvements", [{"MATRICULE": f"C{m:04d}", "DATE_EFFET": d.strftime("%d/%m/%Y"), "CHAMP": champ,
                                            "ANCIENNE_VALEUR": avant, "NOUVELLE_VALEUR": apres}
                                           for m, d, champ, avant, apres in sorted(mouvements, key=lambda x: (x[1], x[0]))])
    write_jsonl("absences", [{"CHAUFFEUR": f"C{m:04d}", "DATE_ABSENCE": d.strftime("%d/%m/%Y"), "MOTIF": mo, "LIBELLE": ABS_LIBELLES[mo]}
                             for (m, d), mo in sorted(absent.items(), key=lambda x: (x[0][1], x[0][0]))])
    write_jsonl("conso_fms", fms)
    mats = [c["mat"] for c in conducteurs]
    risque = [c["infractions"] for c in conducteurs]  # quelques conducteurs concentrent les infractions
    inf, aut, n = [], [], 0
    types = ["Dépassement conduite journalière", "Repos journalier insuffisant", "Pause insuffisante", "Dépassement conduite hebdo"]
    cumuls = {"Dépassement conduite journalière": ("Conduite journalière", None), "Repos journalier insuffisant": ("Repos journalier", None),
              "Pause insuffisante": ("Conduite continue", "Pause"), "Dépassement conduite hebdo": ("Conduite hebdomadaire", None)}
    for d in jours(START, AS_OF):
        if R.random() < 0.45:
            inf.append({"DATE_INFRACTION": d.strftime("%d/%m/%Y"), "MATRICULE": f"C{R.choices(mats, risque)[0]:04d}",
                        "TYPE_INFRACTION": R.choice(types), "CLASSE": R.choice([4, 4, 4, 5])})
            i1, i2 = cumuls[inf[-1]["TYPE_INFRACTION"]]
            inf[-1].update({"NUM_INFRACTION": len(inf), "HEURE": f"{R2.randint(4, 21):02d}:{R2.randint(0, 59):02d}",
                            "LIB_CUMUL_1": i1, "VAL_CUMUL_1": R2.randint(560, 1300) * 2,   # stocké en demi-minutes
                            "LIB_CUMUL_2": i2, "VAL_CUMUL_2": R2.randint(10, 40) * 2 if i2 else None})
        if R.random() < 0.07:
            n += 1
            aut.append({"NUM_EVENEMENT": 90000 + n, "DATE_EVENEMENT": d.strftime("%d/%m/%Y"), "TRACTEUR": R.choice(tracteurs)["num"],
                        "MATRICULE": f"C{R.choices(mats, risque)[0]:04d}", "AUTOROUTE": R.choice(["A7", "A43", "A41", "A48", "A89"]),
                        "NB_PASSAGES": R.randint(1, 3)})
            lat, lon = AUTOROUTES[aut[-1]["AUTOROUTE"]]
            aut[-1].update({"HEURE_EVENEMENT": f"{R2.randint(5, 20):02d}:{R2.randint(0, 59):02d}",
                            "LATITUDE": round(lat + R2.uniform(-0.15, 0.15), 5), "LONGITUDE": round(lon + R2.uniform(-0.15, 0.15), 5),
                            "ZONE": f"Zone {aut[-1]['AUTOROUTE']} - interdiction poids lourds"})
    write_jsonl("infractions", inf)
    write_jsonl("autoroutes_interdites", aut)


def write_xlsx(name, header, rows):
    wb = Workbook()
    ws = wb.active
    ws.append(header)
    for r in rows:
        ws.append(list(r))
    wb.save(SOURCES / "sharepoint" / f"{name}.xlsx")


def write_sharepoint(justif_att, conducteurs, tracteurs, cx):
    write_xlsx("justif_attentes", ["N° voyage", "Justifié", "Commentaire"], justif_att)
    write_xlsx("justif_lavages", ["N° CMR", "Justifié", "Commentaire"], cx["justif_lav"])
    aut = [json.loads(x) for x in open(SOURCES / "telematique" / "autoroutes_interdites.jsonl", encoding="utf-8")]
    write_xlsx("justif_autoroutes", ["ID événement", "Justification", "Validé par", "Commentaire"],
               [(a["NUM_EVENEMENT"], R.choice(["Déviation travaux", "Accident sur itinéraire", "Erreur GPS"]), R.choice(["Exploitation", "QHSE"]),
                 R2.choice(["", "Vu avec le conducteur", "Itinéraire bis imposé par le client"]))
                for a in aut if R.random() < 0.5])
    mats = [c["mat"] for c in conducteurs]
    act_cond = {c["mat"]: c["activite"] for c in conducteurs}
    act_tract = {t["num"]: t["activite"] for t in tracteurs}
    at = []
    for d in jours(START, AS_OF):
        if R.random() < 0.016:
            at.append((d, R.choice(mats), R.choice(["Chute de plain-pied", "Manutention flexible", "Projection produit", "Accident de trajet"]),
                       None if R.random() < 0.2 else R.randint(0, 30)))
            at[-1] = at[-1] + (act_cond[at[-1][1]],)
    write_xlsx("accidents_travail", ["Date", "Matricule", "Type accident", "Jours d'arrêt", "Activité"], at)
    anos, k = [], 0
    for d in jours(START, AS_OF):
        for _ in range(R.choice([0, 0, 1, 1, 2])):
            k += 1
            age = (AS_OF - d).days
            statut = "Traitée" if age > 30 or R.random() < 0.5 else R.choice(["A traiter", "En cours"])
            traite = d + timedelta(R.randint(1, 25)) if statut == "Traitée" else None
            anos.append((k, d if R.random() < 0.7 else d.strftime("%d/%m/%Y"), R.choice(tracteurs)["num"],
                         R.choice(["Pneumatique", "Éclairage", "Freinage", "Flexible", "Carrosserie", "Électrique"]),
                         statut, traite if traite is None or traite <= AS_OF else None))
            anos[-1] = anos[-1] + (cx["nom"][R2.choice(mats)], R2.choice(["Constaté au départ", "Signalé en route", "Constaté au retour"]),
                                   act_tract[anos[-1][2]], f"https://intranet.transval.example/anomalies/{k}")
    write_xlsx("anomalies_materiel", ["ID", "Date signalement", "Tracteur", "Type anomalie", "Statut", "Date traitement",
                                      "Déclarant", "Détail", "Activité", "URL"], anos)
    qhse = [(d, R2.choice(["Non-conformité chargement", "Fuite produit", "Port des EPI", "Documents de bord", "Propreté citerne"]),
             R2.choice(list(ACTIVITES))) for d in jours(START, AS_OF) if R2.random() < 0.12]
    write_xlsx("anomalies_qhse", ["Date", "Type d'anomalies", "Activité"], qhse)
    cs = cx["couts_standards"]
    write_xlsx("couts_standards", list(cs[0]), [tuple(r.values()) for r in cs])
    exploit = (("Appairage", 0.72), ("MCV %", 0.18), ("HCHC par voyage", 3.2), ("Km à vide €", 95000.0), ("CA/KM", 2.3),
               ("Heures à justifier / HP", 0.05), ("Heures compensées / HP", 0.08), ("Frais & primes / HP", 2.5),
               ("Coût total heure hors carte", 9000.0), ("Salaire brut / HP", 21.0))
    atelier = (("Coût maintenance / 100 km", 18.0), ("Coût maintenance / 100 km MOD", 4.0), ("Coût maintenance / 100 km pièces", 6.0),
               ("Coût maintenance / 100 km sous-traitance", 8.0), ("Coût heure prod direct", 48.0), ("Taux préventif", 0.35),
               ("Taux réussite VT", 0.95), ("Taux sous-traitance", 0.35), ("Pannes / 10000 km", 0.6), ("H qual", 0.9))
    obj = [(ind, a, y, v) for y in range(START.year, AS_OF.year + 1) for a in ACTIVITES for ind, v in exploit + atelier]
    write_xlsx("objectifs", ["Indicateur", "Activité", "Année", "Objectif"], obj)


def write_seed_feries():
    p = ROOT / "dbt" / "seeds" / "jours_feries.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date_ferie", "libelle"])
        w.writerows(sorted((d.isoformat(), lib) for d, lib in FERIES.items()))


if __name__ == "__main__":
    main()
