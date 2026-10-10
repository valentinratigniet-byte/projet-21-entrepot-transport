"""Compléments de données dont les rapports Power BI ont besoin (cartes, matériel, frais, atelier détaillé, compta...).

Tirés avec un générateur aléatoire SÉPARÉ (graine 2121) : ajouter ces compléments ne modifie aucune des valeurs
déjà produites par generate.py, donc aucun KPI existant.
"""
import random
import unicodedata
from datetime import date, timedelta

R2 = random.Random(2121)

# Référentiel adresses (coordonnées publiques des villes)
VILLES = {  # Auvergne-Rhône-Alpes + 3 villes frontalières (Suisse, Italie) pour les relations internationales
    "Lyon": ("69000", "69", "FR", 45.7640, 4.8357), "Saint-Étienne": ("42000", "42", "FR", 45.4397, 4.3872),
    "Grenoble": ("38000", "38", "FR", 45.1885, 5.7245), "Clermont-Ferrand": ("63000", "63", "FR", 45.7772, 3.0870),
    "Valence": ("26000", "26", "FR", 44.9334, 4.8924), "Chambéry": ("73000", "73", "FR", 45.5646, 5.9178),
    "Annecy": ("74000", "74", "FR", 45.8992, 6.1294), "Roanne": ("42300", "42", "FR", 46.0347, 4.0726),
    "Feyzin": ("69320", "69", "FR", 45.6717, 4.8586), "Vienne": ("38200", "38", "FR", 45.5255, 4.8740),
    "Bourg-en-Bresse": ("01000", "01", "FR", 46.2052, 5.2255), "Genève": ("1201", "CH", "CH", 46.2044, 6.1432),
    "Turin": ("10121", "IT", "IT", 45.0703, 7.6869), "Milan": ("20121", "IT", "IT", 45.4642, 9.1900),
    "Villeurbanne": ("69100", "69", "FR", 45.7719, 4.8902), "Montélimar": ("26200", "26", "FR", 44.5581, 4.7509),
    "Aurillac": ("15000", "15", "FR", 44.9264, 2.4396), "Le Puy-en-Velay": ("43000", "43", "FR", 45.0434, 3.8858),
    "Moulins": ("03000", "03", "FR", 46.5660, 3.3330), "Vichy": ("03200", "03", "FR", 46.1278, 3.4258),
}

# Noms de personnes inventés syllabe par syllabe (graine séparée) : aucune liste de vrais noms
RN = random.Random(2123)
_CONSONNES, _VOYELLES = "bcdfgjlmnprstvz", ["a", "e", "i", "o", "u", "é", "ou", "an", "on", "in", "ar", "el", "or"]


# Tirages qui existent comme vrais noms ou prénoms (fichiers INSEE des prénoms et des noms de famille), ou à une lettre
# d'un nom courant : rejetés, pour qu'aucun nom ne ressemble à une personne réelle
EXCLUS = {"badan", "bafin", "barcin", "becar", "beda", "bedon", "bicel", "borjel", "bouve", "bude", "cartel",
          "cejar", "contel", "corde", "corpe", "couca", "couso", "dame", "dede", "dega", "difon", "dine", "dinsa",
          "dogan", "dorme", "dular", "dusar", "fanor", "garnon", "garou", "garpar", "gaso", "gelu", "gere", "gigon",
          "gorge", "gorjin", "jamar", "janpe", "jare", "jarna", "jidon", "jodon", "joudon", "larcou", "leco",
          "lecou", "licou", "livon", "lizar", "loman", "loni", "losu", "louni", "mante", "marcin", "marcon", "mece",
          "mepu", "mivon", "morde", "morna", "moza", "mubar", "nador", "narra", "nelcon", "nepi", "nerel", "netel",
          "nini", "noman", "noupe", "parga", "parrin", "pebe", "pemin", "pese", "peta", "pisan", "pise", "pize",
          "ponjin", "pounin", "pouri", "poze", "pufel", "rancou", "rarvin", "razou", "relvel", "repou", "resel",
          "retel", "rilo", "rirel", "roudin", "sade", "sava", "sedu", "sefan", "sonta", "sorlel", "tabo", "tatel",
          "tedo", "tene", "tenesi", "tepin", "tesu", "tintin", "titon", "torro", "vacere", "vason", "vavon", "vere",
          "vonle", "vore", "zamar", "zava", "zevi", "zinca", "zongin", "zorre", "zouvin"}


def nom_invente(syllabes=(2, 3)):
    while True:
        n = "".join(RN.choice(_CONSONNES) + RN.choice(_VOYELLES) for _ in range(RN.randint(*syllabes))).capitalize()
        if unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode().lower() not in EXCLUS:
            return n
TYPE_ACTIVITE = {"VL": "TAD", "PU": "TAD", "CH": "TAD", "AL": "LOG", "CT": "LOG"}
MARQUES_TRACTEUR = [("RENAULT TRUCKS", "T 480"), ("VOLVO", "FH 500"), ("SCANIA", "R 450"), ("DAF", "XF 480"), ("MERCEDES", "ACTROS 1845")]
REMORQUES = {"VL": ("SEMI CITERNE INOX", "FELDBINDER", "TSA 34"), "PU": ("SEMI PULVE", "SPITZER", "SF 2740"),
             "AL": ("SEMI CITERNE ALIMENTAIRE", "MAGYAR", "SR3B"), "CH": ("SEMI CITERNE CHIMIE", "LAG", "O-3-38"),
             "CT": ("PORTE-CONTENEUR", "KÄSSBOHRER", "SHG.AM")}
EQUIPEMENTS = {"VL": "Pompe", "PU": "Compresseur", "AL": "Chauffage", "CH": "Pompe", "CT": ""}
MARCHANDISES = {"VL": ["Huile végétale", "Lubrifiant", "Bitume"], "PU": ["Ciment", "Farine", "Chaux"],
                "AL": ["Lait", "Jus de fruit", "Vin"], "CH": ["Soude", "Acide sulfurique", "Solvant"], "CT": ["Conteneur 20'", "Conteneur 40'"]}
GARAGES = ["Garage Poids Lourds du Rhône", "Pneus Service Grenoble", "Truck Services Saint-Étienne", "Carrosserie Industrielle 69"]
MOTIFS_ST = ["Spécifique constructeur", "Sous effectif", "Pas équipé/formé", "Site externe",
             "Dépannage impossible par nos soins", "Initiative chauffeur réalisable en interne"]
PIECES = {"PREVENTIF": ["Filtre à huile", "Filtre à air", "Huile moteur 10W40", "Filtre gasoil"],
          "PANNE": ["Plaquettes de frein", "Alternateur", "Durite", "Capteur ABS", "Pneu 385/65 R22.5", "Batterie"],
          "SINISTRE": ["Pare-chocs", "Rétroviseur", "Optique avant", "Aile avant"]}
MECANICIENS = [(5000 + i, nom_invente().upper(), nom_invente((2, 2))) for i in range(1, 7)]
ABS_LIBELLES = {"CP": "Congés payés", "AM": "Maladie", "ABS": "Absence injustifiée", "RM": "Repos maison", "SS": "Sans solde"}
AUTOROUTES = {"A7": (45.40, 4.80), "A43": (45.55, 5.40), "A41": (45.70, 5.95), "A48": (45.35, 5.55), "A89": (45.85, 4.20)}


def immat():
    L = "ABCDEFGHJKLMNPQRSTVWXYZ"
    return f"{R2.choice(L)}{R2.choice(L)}-{R2.randint(100, 999)}-{R2.choice(L)}{R2.choice(L)}"


def enrichir(tracteurs, conducteurs, clients, relations, voyages, historique, ots, prelev, fms, absent, chrono, as_of, start):
    """Ajoute des colonnes aux objets existants et renvoie les nouvelles tables sources."""
    nom = {c["mat"]: f"{c['nom'].upper()} {c['prenom']}" for c in conducteurs}

    # relations : type, marchandise, sites, date du prix
    for r in relations:
        r["type"] = R2.choice(["Régulière", "Régulière", "Ponctuelle"])
        r["location"] = int(R2.random() < 0.1)
        r["marchandise"] = R2.choice(MARCHANDISES[r["activite"]])
        r["depart_nom"] = f"Site {r['dep']} {R2.randint(1, 3)}"
        r["arrivee_nom"] = f"Site {r['arr']} {R2.randint(1, 3)}"
        r["prix_date"] = date(R2.choice([start.year, start.year + 1, start.year + 2]), R2.randint(1, 12), 1)

    # indexation gazole client (pied de facture)
    indexation = []
    for c in clients:
        t = R2.choice(["Mensuelle", "Mensuelle", "Trimestrielle", "Aucune"])
        indexation.append({"client_cd": c["cd"], "type_indexation": t, "base_pct": round(R2.uniform(95, 105), 2),
                           "indice_reference": round(R2.uniform(150, 185), 2), "part_gasoil": round(R2.uniform(0.22, 0.32), 3),
                           "date_reference": date(2023, R2.randint(1, 12), 1), "date_application": date(as_of.year - 1, R2.randint(1, 11), 1),
                           "sur_facture": R2.choice(["Oui", "Non"]), "a_la_baisse": R2.choice(["Oui", "Non"]),
                           "applique": "Non" if t == "Aucune" else R2.choice(["Oui", "Oui", "Non"]),
                           "commentaire": R2.choice(["", "Clause contractuelle", "Négociation annuelle", "Indice CNR"])})

    # matériel (tracteurs + semi-remorques)
    materiel = []
    for t in tracteurs:
        marque, modele = MARQUES_TRACTEUR[t["num"] % 5]
        materiel.append({"ent_code": str(t["num"]), "immat": immat(), "type_materiel": "TRACTEUR", "marque": marque, "modele": modele,
                         "activite_type": TYPE_ACTIVITE[t["activite"]], "activite_cd": t["activite"],
                         "equipement": "", "date_entree": t["mise_service"], "date_sortie": None, "statut": "En service"})
        typ, marque_r, modele_r = REMORQUES[t["activite"]]
        materiel.append({"ent_code": f"R{t['num'] + 2000}", "immat": immat(), "type_materiel": typ, "marque": marque_r, "modele": modele_r,
                         "activite_type": TYPE_ACTIVITE[t["activite"]], "activite_cd": t["activite"],
                         "equipement": EQUIPEMENTS[t["activite"]], "date_entree": t["mise_service"], "date_sortie": None, "statut": "En service"})
    km_cumul = {}
    for v in voyages:
        if v["date_livre"] <= as_of and v["statut"] == "LIVRE":
            km_cumul[v["tracteur"]] = km_cumul.get(v["tracteur"], 0) + v["km_total"]
    for m in materiel:
        if m["type_materiel"] == "TRACTEUR":
            m["compteur_km"] = 250_000 + R2.randint(0, 400_000) + km_cumul.get(int(m["ent_code"]), 0)
            m["date_compteur"] = as_of
        else:
            m["compteur_km"], m["date_compteur"] = None, None

    # voyages : CMR, double dépotage (tête de lot), quantité facturée, péages, temps de conduite en charge
    extras = {}
    precedent = None
    for v in voyages:
        cmr = f"CMR{v['voyage_id']}"
        e = {"cmr": cmr, "tete_lot_cmr": cmr, "nb_depotages": 1, "qt_facture": round(v["qt_livre"] * R2.uniform(0.98, 1.0), 3),
             "nb_passages_peage": R2.randint(0, 6),
             "tps_cond_charge_h": round(v["km_charge"] / 62 * (R2.uniform(1.8, 2.3) if R2.random() < 0.03 else R2.uniform(0.92, 1.12)), 2),
             "ville_rupture": R2.choice(list(VILLES)) if R2.random() < 0.03 else None}
        if v["double_depotage"] and precedent:
            e["tete_lot_cmr"], e["nb_depotages"] = precedent, 2
        precedent = cmr
        extras[v["voyage_id"]] = e
        v.update(e)
    for h in historique:
        h.update(extras[h["voyage_id"]])

    # atelier : fournisseur, demandeur, motif de sous-traitance, casse imputée, lignes de détail
    conducteur_du_jour = {(v["tracteur"], v["date_charge"]): v["salarie_cd"] for v in voyages}
    titulaire = {c["tracteur"]: c["mat"] for c in conducteurs if c["tracteur"] and c["sortie"] is None}
    lignes, num_ligne = [], 0
    for o in ots:
        externe = o["type_document"] == "Facture externe"
        o["fournisseur"] = R2.choice(GARAGES) if externe else "Atelier TransVal"
        dem = conducteur_du_jour.get((o["tracteur"], o["date_ot"])) or titulaire.get(o["tracteur"])  # sinon le titulaire du tracteur
        o["demandeur"] = nom.get(dem, "Exploitation")
        o["motif_sous_traitance"] = R2.choice(MOTIFS_ST) if externe and o["famille"] in ("PANNE", "SINISTRE", "PREVENTIF") else None
        o["num_facture_interne"] = f"FI{o['ot_id']}"
        o["matricule_responsable"] = dem if o["famille"] == "SINISTRE" and dem and R2.random() < 0.5 else None
        detail = []
        if externe:
            detail.append(("Prestation externe", f"{o['famille'].capitalize()} - {o['fournisseur']}", 1, o["cout_total"], None))
        else:
            reste = o["cout_pieces"]
            noms = PIECES.get(o["famille"], ["Consommables"])
            n = R2.randint(1, min(3, len(noms)))
            for i, p in enumerate(R2.sample(noms, n)):
                montant = reste if i == n - 1 else round(reste * R2.uniform(0.2, 0.6), 2)
                reste = round(reste - montant, 2)
                detail.append(("Pièce", p, R2.randint(1, 4), montant, None))
            if o["heures_mo"]:
                detail.append(("Main d'oeuvre", "Main d'oeuvre atelier", o["heures_mo"], o["cout_mo"], R2.choice(MECANICIENS)[0]))
            ecart = round(o["cout_total"] - sum(x[3] for x in detail), 2)  # arrondis : la dernière ligne absorbe l'écart
            if detail and ecart:
                t, lib, q, m, mec = detail[-1]
                detail[-1] = (t, lib, q, round(m + ecart, 2), mec)
        for t, lib, q, m, mec in detail:
            num_ligne += 1
            lignes.append({"ligne_id": num_ligne, "ot_id": o["ot_id"], "type_ligne": t, "libelle": lib, "quantite": q,
                           "montant": m, "mecanicien": mec})

    # heures mécaniciens : heures payées (paie) et heures produites (GMAO)
    heures_mec, gmao = [], []
    mois = sorted({(o["date_ot"].year, o["date_ot"].month) for o in ots})
    ot_date = {o["ot_id"]: o["date_ot"] for o in ots}
    cout_charge = {m[0]: R2.uniform(41, 55) for m in MECANICIENS}  # coût horaire chargé propre à chaque mécanicien
    for l_ in lignes:
        if l_["mecanicien"]:
            d = ot_date[l_["ot_id"]]
            gmao.append({"date": d, "mecanicien": l_["mecanicien"], "article": "MO", "heures": l_["quantite"],
                         "cout": round(l_["quantite"] * cout_charge[l_["mecanicien"]] * R2.uniform(0.95, 1.06), 2)})
    sur_ot = {}
    for g in gmao:
        k = (g["mecanicien"], g["date"].year, g["date"].month)
        sur_ot[k] = sur_ot.get(k, 0) + g["heures"]
    for mat, n, p in MECANICIENS:
        for y, mo in mois:
            if date(y, mo, 1) >= date(as_of.year, as_of.month, 1):
                continue
            payees = round(151.67 + R2.uniform(0, 12), 2)
            heures_mec.append({"matricule": mat, "nom": n, "prenom": p, "annee": y, "mois": mo, "heures_payees": payees})
            # entretien courant hors OT (graissage, pneus, préparation des semis) : production réaliste de 72 à 88 % des heures payées
            courant = round(max(0.0, payees * R2.uniform(0.72, 0.88) - sur_ot.get((mat, y, mo), 0)), 2)
            gmao.append({"date": date(y, mo, 15), "mecanicien": mat, "article": "ENTRETIEN", "heures": courant,
                         "cout": round(courant * cout_charge[mat] * R2.uniform(0.95, 1.06), 2)})

    # frais et activités annexes des conducteurs (prestations DIV / MOI)
    activcha = []
    jours_travailles = {}
    for c in chrono:
        k = (c["mat"], c["date"].year, c["date"].month)
        jours_travailles[k] = jours_travailles.get(k, 0) + 1
    taux = {c["mat"]: round(R2.uniform(14.2, 17.5), 2) for c in conducteurs}
    for (m, y, mo), nj in sorted(jours_travailles.items()):
        jour = R2.choice(["00", "15", "28"])  # le jour '00' existe en source : à nettoyer
        base = f"{y}{mo:02d}"
        def ligne(lib, prest, h, cout, nacpt="6250"):
            activcha.append({"FR_DATE": base + jour, "FR_MATR": m, "FR_PREST": prest, "FR_COMPTE": nacpt, "FR_LIBELLE": lib, "FR_QTE": round(h, 2),
                             "FR_COUT_1": round(cout * 0.7, 2), "FR_COUT_2": round(cout * 0.2, 2), "FR_COUT_3": round(cout - round(cout * 0.7, 2) - round(cout * 0.2, 2), 2),
                             "FR_VERIF": "N" if date(y, mo, 1) >= date(as_of.year, as_of.month, 1) - timedelta(days=1) and R2.random() < 0.3 else "O"})
        ligne("Frais conv", "DIV", 0, nj * R2.uniform(14, 19))
        ligne("Frais non-conv", "DIV", 0, R2.uniform(0, 90))
        hc = R2.uniform(2, 14)
        ligne("Heures hors carte", "MOI", hc, hc * taux[m] * 1.45)
        if R2.random() < 0.25:
            hf = R2.uniform(3, 7)
            ligne("Formation", "MOI", hf, hf * taux[m] * 1.45)
        if R2.random() < 0.4:
            ht = R2.uniform(1, 5)
            ligne("Trajet", "MOI", ht, ht * taux[m] * 1.45)
        if R2.random() < 0.1:
            ligne("Forfaitmensuel", "MOI", 0, 50)                   # exclu par la requête des heures
        if R2.random() < 0.05:
            ligne("Régularisation", "MOI", 0, R2.uniform(10, 80), nacpt="4000")  # compte 4000 exclu

    # carburant : ville de la pompe / FMS : conducteur, prise de force, CO2
    pompe_ville = {1: "Lyon", 2: "Turin", 3: "Grenoble", 4: "Valence"}
    for f in fms:
        d = date(int(f["DATE_JOUR"][6:]), int(f["DATE_JOUR"][3:5]), int(f["DATE_JOUR"][:2]))
        mat = conducteur_du_jour.get((f["TRACTEUR"], d))
        f["MATRICULE"] = f"C{mat:04d}" if mat else None
        f["LITRES_PTO"] = f"{R2.uniform(0, 6):.1f}"
        f["CO2"] = f"{float(f['LITRES_TOTAL']) * 2.64:.1f}"

    # absences : repos maison / sans solde sur des jours non travaillés
    travaille = {(c["mat"], c["date"]) for c in chrono}
    for c in conducteurs:
        d = max(start, c["entree"])
        while d <= as_of:
            if d.weekday() < 5 and (c["mat"], d) not in absent and (c["mat"], d) not in travaille and R2.random() < 0.02:
                absent[(c["mat"], d)] = R2.choice(["RM", "SS"])
            d += timedelta(1)

    # coûts standard d'un ensemble citerne 44 t (ordres de grandeur publics du secteur, valeurs fictives) :
    # conducteur = salaire conventionnel + charges + frais de route, revalorisé chaque année ;
    # gazole + AdBlue = ~33 L/100 km x prix moyen HT de l'année (repli après le pic de 2022) + ~5 % d'AdBlue ;
    # maintenance = entretien préventif + réparations (pièces et main-d'oeuvre atelier) ; pneus = usure ramenée au km
    gazole = {2023: 0.462, 2024: 0.441, 2025: 0.418, 2026: 0.426}
    couts_standards = [{"annee": y, "cout_chauffeur_heure": round(31.8 * 1.032 ** (y - 2023), 2),
                        "cout_gazole_adblue_km": gazole.get(y, 0.43), "cout_maintenance_parc_km": round(0.105 * 1.04 ** (y - 2023), 3),
                        "cout_pneus_km": round(0.031 * 1.025 ** (y - 2023), 3)}
                       for y in range(start.year, as_of.year + 1)]

    return {"indexation": indexation, "materiel": materiel, "lignes": lignes, "heures_mec": heures_mec, "gmao": gmao,
            "activcha": activcha, "pompe_ville": pompe_ville, "taux": taux, "couts_standards": couts_standards, "nom": nom}
