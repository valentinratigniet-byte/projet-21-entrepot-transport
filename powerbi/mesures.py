"""Mesures DAX du modèle TransVal — une seule définition par indicateur, rangées par dossier.

Le nettoyage, les filtres métier (pointages valides, voyages annulés, matricules...) et le « aujourd'hui » figé sont
déjà dans l'entrepôt : les mesures se limitent à agréger et à rapporter. Les variantes N-1 / évolution sont
générées par evo() au lieu d'être recopiées à la main (copies de mesures = définitions qui divergent).
"""

MESURES = []


def m(dossier, nom, expr, fmt=None):
    MESURES.append((dossier, nom, expr, fmt))


def evo(dossier, nom, fmt=None, mois=False):
    """Ajoute <nom> N-1 (ou M-1) et <nom> évolution pour une mesure existante."""
    suffixe, decal = ("M-1", "DATEADD('Date'[Date], -1, MONTH)") if mois else ("N-1", "SAMEPERIODLASTYEAR('Date'[Date])")
    m(dossier, f"{nom} {suffixe}", f"CALCULATE([{nom}], {decal})", fmt)
    # période sans donnée (mois à venir...) : pas d'évolution, plutôt qu'un -100 % trompeur
    m(dossier, f"{nom} évolution", f"IF(NOT ISBLANK([{nom}]) && NOT ISBLANK([{nom} {suffixe}]), DIVIDE([{nom}], [{nom} {suffixe}]) - 1)",
      "0.0%;-0.0%;0.0%")


EUR, EUR2, PCT, N0, N1, N2 = "#,0 €", "#,0.00 €", "0.0%", "#,0", "#,0.0", "#,0.00"
REF = "VAR ref = [Date de référence]\n"

# ---------------------------------------------------------------- calendrier
C = "Calendrier"
m(C, "Date de référence", "MAX('Paramètres'[Date référence])", "dd/mm/yyyy")
m(C, "Actualisé le", "MAX('Paramètres'[Date actualisation])", "dd/mm/yyyy hh:nn")
m(C, "Jours ouvrés", "CALCULATE(COUNTROWS('Date'), 'Date'[Est jour ouvré])", "0")
m(C, "Semaine en cours", "\"S \" & FORMAT(WEEKNUM([Date de référence], 21), \"00\")")
m(C, "Semaine texte", "\"Du \" & FORMAT(MIN('Date'[Date]), \"dd/MM/yyyy\") & \" au \" & FORMAT(MAX('Date'[Date]), \"dd/MM/yyyy\")")
m(C, "Date min", "MIN('Date'[Date])", "dd/mm/yyyy")
m(C, "Date max", "MAX('Date'[Date])", "dd/mm/yyyy")

# ---------------------------------------------------------------- activité
A = "Activité"
m(A, "Nb voyages", "COUNTROWS('Voyage')", N0); evo(A, "Nb voyages", N0)
m(A, "Nb voyages / jour ouvré", "DIVIDE([Nb voyages], [Jours ouvrés])", N1); evo(A, "Nb voyages / jour ouvré", N1, mois=True)
m(A, "CA facturé", "CALCULATE(SUM('Voyage'[CA facturé]), 'Voyage'[Est réalisé])", EUR); evo(A, "CA facturé", EUR)
m(A, "CA réparti", "CALCULATE(SUM('Voyage'[CA réparti]), 'Voyage'[Est réalisé])", EUR); evo(A, "CA réparti", EUR)
m(A, "CA moyen / jour ouvré", "DIVIDE([CA facturé], [Jours ouvrés])", EUR); evo(A, "CA moyen / jour ouvré", EUR)
m(A, "CA moyen / jour ouvré (k€)", "IF(ISBLANK([CA moyen / jour ouvré]), BLANK(), FORMAT([CA moyen / jour ouvré] / 1000, \"#,0.00\") & \" k€\")")
m(A, "CA moyen / jour ouvré réparti", "DIVIDE([CA réparti], [Jours ouvrés])", EUR); evo(A, "CA moyen / jour ouvré réparti", EUR)
m(A, "Km total", "SUM('Voyage'[Km total])", N0); evo(A, "Km total", N0)
m(A, "Km chargé moyen", "AVERAGE('Voyage'[Km chargé])", N0)
m(A, "Temps chargement moyen", "AVERAGE('Voyage'[Temps chargement h])", N2)
m(A, "Temps livraison moyen", "AVERAGE('Voyage'[Temps livraison h])", N2)
m(A, "Heures prod", "SUM('Voyage'[Temps total h])", N0)
m(A, "CA / km", "DIVIDE([CA facturé], [Km total])", EUR2); evo(A, "CA / km", EUR2)
m(A, "CA / km réparti", "DIVIDE([CA réparti], [Km total])", EUR2); evo(A, "CA / km réparti", EUR2)
m(A, "CA / heure", "DIVIDE([CA facturé], [Heures prod])", EUR2); evo(A, "CA / heure", EUR2)
m(A, "CA / heure réparti", "DIVIDE([CA réparti], [Heures prod])", EUR2); evo(A, "CA / heure réparti", EUR2)
m(A, "CA / voyage", "DIVIDE([CA facturé], [Nb voyages], 0)", EUR); evo(A, "CA / voyage", EUR)
m(A, "Appairage", "DIVIDE(SUM('Voyage'[Km chargé]), SUM('Voyage'[Km total]))", PCT); evo(A, "Appairage", PCT)
m(A, "MCV €", "SUM('Voyage'[MCV marge retenue])", EUR); evo(A, "MCV €", EUR)
m(A, "MCV %", "CALCULATE(DIVIDE(SUM('Voyage'[MCV marge retenue]), SUM('Voyage'[CA réparti])), 'Voyage'[Code relation] <> \"SPOT\")", PCT)
evo(A, "MCV %", PCT)
m(A, "Autoroute € / 100 km", "DIVIDE(SUM('Voyage'[Autoroute €]), SUM('Voyage'[Km total])) * 100", EUR2); evo(A, "Autoroute € / 100 km", EUR2)
m(A, "Péages €", "SUM('Voyage'[Autoroute €])", EUR)
m(A, "Péages € / km", "DIVIDE([Péages €], [Km total])", EUR2)
m(A, "Km à vide €", "SUM('Voyage'[Km vide €])", EUR)
m(A, "Qté livrée", "SUM('Voyage'[Qté livrée])", N1)
m(A, "Qté livrée moyenne", "AVERAGE('Voyage'[Qté livrée])", N2)
m(A, "Qté facturée / voyage", "DIVIDE(SUM('Voyage'[Qté facturée]), [Nb voyages])", N2); evo(A, "Qté facturée / voyage", N2)
m(A, "Dernier prix", "MAX('Relation'[Prix tarif])", EUR2)
m(A, "Coût total chargé", "SUM('Voyage'[Coût total chargé])", EUR)
# semaine : celle du contexte (colonne, point de courbe) ; sans semaine précise -> dernière semaine écoulée de la période
SEMAINE = ("VAR sem = IF(HASONEVALUE('Date'[Année semaine n°]), VALUES('Date'[Année semaine n°]), "
           "CALCULATE(MAX('Date'[Année semaine n°]), 'Date'[Est passé]))\n")
m(A, "Nb voyages de la semaine", SEMAINE + "RETURN CALCULATE([Nb voyages], 'Date'[Année semaine n°] = sem)", N0)
m(A, "CA de la semaine", SEMAINE + "RETURN CALCULATE([CA facturé], 'Date'[Année semaine n°] = sem)", EUR)
# même semaine ISO un an plus tôt (numéro année*100 + semaine)
m(A, "Nb voyages même semaine N-1", SEMAINE + "RETURN CALCULATE([Nb voyages], REMOVEFILTERS('Date'), 'Date'[Année semaine n°] = sem - 100)", N0)
m(A, "CA même semaine N-1", SEMAINE + "RETURN CALCULATE([CA facturé], REMOVEFILTERS('Date'), 'Date'[Année semaine n°] = sem - 100)", EUR)
m(A, "Nb voyages semaine évolution", "IF(NOT ISBLANK([Nb voyages de la semaine]) && NOT ISBLANK([Nb voyages même semaine N-1]), DIVIDE([Nb voyages de la semaine], [Nb voyages même semaine N-1]) - 1)", PCT)
m(A, "CA semaine évolution", "IF(NOT ISBLANK([CA de la semaine]) && NOT ISBLANK([CA même semaine N-1]), DIVIDE([CA de la semaine], [CA même semaine N-1]) - 1)", PCT)
# année en cours / précédente : on remplace le filtre d'année mais on garde l'axe (semaine, jour...) du visuel
m(A, "CA / jour ouvré année en cours",
  REF + "RETURN CALCULATE(DIVIDE([CA facturé], [Jours ouvrés]), 'Date'[Année] = YEAR(ref), 'Date'[Est passé])", EUR)
m(A, "CA / jour ouvré année précédente",
  REF + "RETURN CALCULATE(DIVIDE([CA facturé], [Jours ouvrés]), 'Date'[Année] = YEAR(ref) - 1)", EUR)
m(A, "Nb missions du jour", REF + "RETURN CALCULATE([Nb voyages], REMOVEFILTERS('Date'), 'Date'[Date] = ref)", N0)

# ---------------------------------------------------------------- exploitation J+1 (préparation du prochain jour ouvré)
J = "Exploitation J+1"
J1 = REF + "VAR j1 = CALCULATE(MIN('Date'[Date]), REMOVEFILTERS('Date'), 'Date'[Date] > ref, 'Date'[Est jour ouvré])\n"
m(J, "Jour J+1", J1 + "RETURN j1", "dd/mm/yyyy")
m(J, "Libellé J+1", J1 + "RETURN \"Préparation du \" & FORMAT(j1, \"dddd d mmmm yyyy\") & \"  ·  situation arrêtée au \" & FORMAT(ref, \"dd/mm/yyyy\")")
m(J, "Missions planifiées J+1", J1 + "RETURN CALCULATE([Nb voyages], REMOVEFILTERS('Date'), 'Date'[Date] = j1) + 0", N0)
m(J, "CA prévu J+1", J1 + "RETURN CALCULATE(SUM('Voyage'[CA facturé]), REMOVEFILTERS('Date'), 'Date'[Date] = j1) + 0", EUR)
m(J, "Tracteurs engagés J+1", J1 + "RETURN CALCULATE(DISTINCTCOUNT('Voyage'[N° tracteur]), REMOVEFILTERS('Date'), 'Date'[Date] = j1) + 0", N0)
# les journées d'atelier portent l'activité « MAIN » et aucun conducteur : on ignore ces filtres (le parc est filtré par le matériel)
m(J, "Tracteurs en maintenance J", REF + "RETURN CALCULATE([Jours tracteur en maintenance], REMOVEFILTERS('Date'), REMOVEFILTERS('Activité'), REMOVEFILTERS('Conducteur'), 'Date'[Date] = ref) + 0", N0)
m(J, "Tracteurs libres J+1", "MAX(0, [Parc tracteurs] - [Tracteurs en maintenance J] - [Tracteurs engagés J+1])", N0)
m(J, "Taux d'engagement flotte J+1", "DIVIDE([Tracteurs engagés J+1], [Parc tracteurs] - [Tracteurs en maintenance J])", PCT)
m(J, "Conducteurs sans mission J+1", "MAX(0, [Nb chauffeurs] - [Nb absents du jour] - [Tracteurs engagés J+1])", N0)
m(J, "CA du jour", REF + "RETURN CALCULATE([CA facturé], REMOVEFILTERS('Date'), 'Date'[Date] = ref)", EUR)
m(J, "Appairage du jour", REF + "RETURN CALCULATE([Appairage], REMOVEFILTERS('Date'), 'Date'[Date] = ref)", PCT)
m(A, "Passages autoroute interdite / voyage", "DIVIDE(DISTINCTCOUNT('Autoroute interdite'[Événement ID]), [Nb voyages])", "0.000")

# ---------------------------------------------------------------- contrôle de facturation
F = "Contrôle facturation"
evt = lambda t: f"CALCULATE(SUM('Événement facturé'[Montant facturé]), 'Événement facturé'[Type événement] = \"{t}\")"  # noqa: E731
m(F, "Attente à facturer €", "CALCULATE(SUM('Voyage'[Attente à facturer €]), 'Voyage'[Est réalisé])", EUR)
m(F, "Attentes facturées €", evt("ATT"), EUR)
m(F, "% attentes facturées", "DIVIDE([Attentes facturées €], [Attente à facturer €])", PCT)
m(F, "Nb attentes", "CALCULATE([Nb voyages], 'Voyage'[Est attente])", N0)
m(F, "Nb attentes facturées", "CALCULATE([Nb voyages], 'Voyage'[Est attente facturée])", N0)
m(F, "Nb attentes justifiées", "CALCULATE([Nb voyages], 'Voyage'[Est attente justifiée])", N0)
m(F, "Lavage à facturer €", "SUM('Voyage'[MCV lavage int])", EUR)
m(F, "Lavages facturés €", evt("LAV"), EUR)
m(F, "% lavages facturés", "DIVIDE([Lavages facturés €], [Lavage à facturer €])", PCT)
m(F, "Nb lavages facturés", "CALCULATE([Nb voyages], 'Voyage'[Est lavage facturé])", N0)
m(F, "Nb lavages justifiés", "CALCULATE([Nb voyages], 'Voyage'[Est lavage justifié])", N0)
m(F, "Samedi à facturer €", "SUM('Voyage'[Samedi à facturer €])", EUR)
m(F, "Samedis facturés €", evt("SAM"), EUR)
m(F, "Nb samedis facturés", "CALCULATE([Nb voyages], 'Voyage'[Est samedi facturé])", N0)
m(F, "Double dépotage facturé €", evt("DD"), EUR)
m(F, "Nb doubles dépotages", "CALCULATE([Nb voyages], 'Voyage'[Est double dépotage])", N0)
m(F, "Nb doubles dépotages facturés", "CALCULATE([Nb voyages], 'Voyage'[Est DD facturé])", N0)

# ---------------------------------------------------------------- heures conducteurs
H = "Heures conducteurs"
pt = lambda cond: (f"CALCULATE(SUM('Pointage'[Heures]), 'Pointage'[Est valide], 'Pointage'[Est saisie exploitation], {cond})")  # noqa: E731
m(H, "Nb voyages réalisés",
  "CALCULATE(COUNTROWS('Voyage'), USERELATIONSHIP('Voyage'[Date chargement], 'Date'[Date]), 'Voyage'[Statut] = \"LIVRE\")", N0)
for nom, cond in (("Heures à justifier", "'Pointage'[Catégorie HCHC] = \"a_justifier\""),
                  ("Heures chargement", "'Pointage'[Libellé brut] IN {\"Chargement\", \"Chargement hors mission\"}"),
                  ("Heures déchargement", "'Pointage'[Libellé brut] IN {\"Déchargement\", \"Livraison hors mission\"}"),
                  ("Heures chargement + déchargement", "'Pointage'[Catégorie HCHC] = \"chargement_dechargement\""),
                  ("Heures lavage interne", "'Pointage'[Catégorie HCHC] = \"lavage_interne\""),
                  ("Heures lavage externe", "'Pointage'[Catégorie HCHC] = \"lavage_externe\""),
                  ("Heures gasoil", "'Pointage'[Catégorie HCHC] = \"gasoil\""),
                  ("Heures décroche / raccroche", "'Pointage'[Catégorie HCHC] = \"decroche_raccroche\""),
                  ("Heures VT / VO", "'Pointage'[Catégorie HCHC] = \"vt_vo\"")):
    m(H, nom, pt(cond), N1)
    m(H, f"{nom} / voyage", f"DIVIDE([{nom}], [Nb voyages réalisés])", N2)
m(H, "Heures carte hors conduite",
  "CALCULATE(SUM('Pointage'[Heures]) + SUM('Pointage'[Heures forfait]), 'Pointage'[Est valide], 'Pointage'[Catégorie HCHC] <> \"a_justifier\")", N1)
m(H, "Heures carte hors conduite / voyage", "DIVIDE([Heures carte hors conduite], [Nb voyages réalisés])", N2)
m(H, "HCHC heures", "SUM('Chrono'[Heures hors conduite])", N1)
m(H, "HCHC / voyage", "DIVIDE([HCHC heures], [Nb voyages réalisés])", N2)
for nom, col in (("Heures conduite", "Heures conduite"), ("Heures travail", "Heures travail"), ("Heures dispo", "Heures dispo"),
                 ("Heures repos payé", "Heures repos payé"), ("Heures service", "Heures service")):
    m(H, nom, f"SUM('Chrono'[{col}])", N1)
m(H, "Productivité TC / TS", "DIVIDE([Heures conduite], [Heures service])", PCT)
m(H, "Salaire brut / heure prod", "DIVIDE(SUM('Compteur paie'[Salaire brut]), [Heures prod])", EUR2)
m(H, "Heures compensées (base contrat)",
  REF + "VAR debut = DATE(YEAR(ref), MONTH(ref), 1)\nVAR limite = IF(DAY(ref) >= 10, debut, EDATE(debut, -1))  -- mois clos à partir du 10\n"
  "RETURN CALCULATE(SUM('Compteur paie'[Heures compensées]), 'Compteur paie'[Mois] < limite)", N1)
m(H, "Heures compensées €", "[Heures compensées (base contrat)] * [Salaire brut / heure prod]", EUR)
m(H, "Heures compensées € / HP", "DIVIDE([Heures compensées €], [Heures prod])", EUR2)
m(H, "Heures à justifier payées",
  "CALCULATE(SUM('Pointage'[Heures]), 'Pointage'[Est valide], 'Pointage'[Catégorie HCHC] = \"a_justifier\")", N1)
m(H, "Heures à justifier payées €", "[Heures à justifier payées] * [Salaire brut / heure prod]", EUR)
m(H, "Heures à justifier payées € / HP", "DIVIDE([Heures à justifier payées €], [Heures prod])", EUR2)
m(H, "% heures à justifier / heures prod", "DIVIDE([Heures à justifier payées], [Heures prod])", PCT)
ac = lambda cond, col="Coût": f"CALCULATE(SUM('Activité chauffeur'[{col}]), {cond})"  # noqa: E731
m(H, "Heures hors carte", ac("'Activité chauffeur'[Catégorie] = \"Hors carte\"", "Heures"), N1)
m(H, "Heures hors carte €", ac("'Activité chauffeur'[Catégorie] = \"Hors carte\""), EUR)
m(H, "Coût heure hors carte / HP", "DIVIDE([Heures hors carte €], [Heures prod])", EUR2)
m(H, "% heures hors carte / heures prod", "DIVIDE([Heures hors carte], [Heures prod])", PCT)
m(H, "Frais conv €", ac("'Activité chauffeur'[Libellé] = \"Frais conv\""), EUR)
m(H, "Frais non-conv €", ac("'Activité chauffeur'[Libellé] = \"Frais non-conv\""), EUR)
m(H, "Frais conv / HP", "DIVIDE([Frais conv €], [Heures prod])", EUR2)
m(H, "Frais non-conv / HP", "DIVIDE([Frais non-conv €], [Heures prod])", EUR2)
m(H, "Frais & primes / HP", "[Frais conv / HP] + [Frais non-conv / HP]", EUR2)
m(H, "Heures formation", ac("'Activité chauffeur'[Catégorie] = \"Formation\"", "Heures"), N1)
m(H, "Coût formation €", ac("'Activité chauffeur'[Catégorie] = \"Formation\""), EUR)
m(H, "Heures trajets", ac("'Activité chauffeur'[Catégorie] = \"Trajet\"", "Heures"), N1)
m(H, "Coût trajets €", ac("'Activité chauffeur'[Catégorie] = \"Trajet\""), EUR)
m(H, "Lignes en attente de vérification", "CALCULATE(COUNTROWS('Activité chauffeur'), 'Activité chauffeur'[Est en attente vérification])", N0)
m(H, "Heures payées", "SUM('Compteur paie'[Heures payées])", N1)
m(H, "Heures réalisées (paie)", "SUM('Compteur paie'[Heures réalisées])", N1)
m(H, "Heures payées / mois",
  "AVERAGEX(VALUES('Conducteur'[Matricule]), DIVIDE(CALCULATE(SUM('Compteur paie'[Heures payées])), CALCULATE(DISTINCTCOUNT('Compteur paie'[Mois]))))", N1)
m(H, "Écart moyen heures payées",
  "VAR moyenne = CALCULATE([Heures payées / mois], ALLSELECTED('Conducteur'))\n"
  "RETURN AVERAGEX(FILTER(VALUES('Conducteur'[Matricule]), NOT ISBLANK([Heures payées / mois])), ABS([Heures payées / mois] - moyenne))", N1)
m(H, "Heures réalisées moyennes / conducteur",
  "CALCULATE(DIVIDE([Heures réalisées (paie)], DISTINCTCOUNT('Compteur paie'[Matricule])), ALLSELECTED('Conducteur'))", N1)
m(H, "Écart moyen heures réalisées",
  "AVERAGEX(FILTER(VALUES('Conducteur'[Matricule]), NOT ISBLANK(CALCULATE([Heures réalisées (paie)]))),"
  " ABS(CALCULATE([Heures réalisées (paie)]) - [Heures réalisées moyennes / conducteur]))", N1)
mtd = ("CALCULATE({x}, REMOVEFILTERS('Date'), 'Date'[Date] >= DATE(YEAR(ref), MONTH(ref), 1), 'Date'[Date] <= ref - 1)")
m(H, "Heures réalisées mois en cours", REF + "RETURN " + mtd.format(x="SUM('Chrono'[Heures service])"), N1)
m(H, "Moyenne heures / jour", REF + "RETURN DIVIDE([Heures réalisées mois en cours], " + mtd.format(x="DISTINCTCOUNT('Chrono'[Date])") + ")", N1)
m(H, "Jours restants", REF + "RETURN NETWORKDAYS(ref, EOMONTH(ref, 0))", "0")
m(H, "Jours ouvrés restants", REF + "RETURN CALCULATE(COUNTROWS('Date'), REMOVEFILTERS('Date'), 'Date'[Date] >= ref, 'Date'[Date] <= EOMONTH(ref, 0), 'Date'[Est jour ouvré])", "0")
m(H, "Projection fin de mois", "[Heures réalisées mois en cours] + [Moyenne heures / jour] * [Jours restants]", N0)
m(H, "Projection fin de mois hors fériés", "[Heures réalisées mois en cours] + [Moyenne heures / jour] * [Jours ouvrés restants]", N0)
m(H, "Reste à faire", "[Projection fin de mois] - [Heures réalisées mois en cours]", N0)

# ---------------------------------------------------------------- parc
P = "Parc"
m(P, "Nb jours-tracteur", "CALCULATE(COUNTROWS('Affectation'), NOT 'Affectation'[Est maintenance])", N0)
m(P, "Nb tracteurs / jour ouvré", "DIVIDE([Nb jours-tracteur], [Jours ouvrés])", N1); evo(P, "Nb tracteurs / jour ouvré", N1)
m(P, "Nb tracteurs / jour ouvré année en cours",
  REF + "RETURN CALCULATE([Nb tracteurs / jour ouvré], 'Date'[Année] = YEAR(ref), 'Date'[Est passé])", N1)
m(P, "Nb tracteurs / jour ouvré année précédente",
  REF + "RETURN CALCULATE([Nb tracteurs / jour ouvré], 'Date'[Année] = YEAR(ref) - 1)", N1)
m(P, "Matériels hors exploitation", "CALCULATE(COUNTROWS('Matériel'), 'Matériel'[Statut] <> \"En service\") + 0", N0)
m(P, "Jours tracteur en maintenance", "COUNTROWS('Immobilisation') + 0", N0)
m(P, "Pic tracteurs", "MAXX(VALUES('Date'[Date]), CALCULATE([Nb jours-tracteur]))", N0)
m(P, "Étiquette tracteurs", "FORMAT([Nb tracteurs / jour ouvré], \"0.0\") & \" (\" & FORMAT([Pic tracteurs], \"0\") & \")\"")
m(P, "Parc tracteurs", "CALCULATE(COUNTROWS('Matériel'), 'Matériel'[Est tracteur])", N0)
m(P, "Parc semi-remorques", "CALCULATE(COUNTROWS('Matériel'), NOT 'Matériel'[Est tracteur])", N0)
m(P, "Nb matériels", "COUNTROWS('Matériel')", N0)
m(P, "Tracteurs disponibles", "[Parc tracteurs] - [Nb tracteurs / jour ouvré]", N1)
for code in ("VL", "PU", "AL", "CH", "CT"):
    m(P, f"Tracteurs disponibles {code}",
      f"CALCULATE([Parc tracteurs], 'Matériel'[Code activité] = \"{code}\") - CALCULATE([Nb tracteurs / jour ouvré], 'Affectation'[Code activité] = \"{code}\")", N1)
    m(P, f"Parc tracteurs {code}", f"CALCULATE([Parc tracteurs], 'Matériel'[Code activité] = \"{code}\")", N0)
for typ in ("TAD", "LOG"):
    m(P, f"Charge {typ}", f"CALCULATE([Nb tracteurs / jour ouvré], 'Activité'[Type activité] = \"{typ}\")", N1)
m(P, "Part de l'activité", "DIVIDE([Nb tracteurs / jour ouvré], CALCULATE([Nb tracteurs / jour ouvré], REMOVEFILTERS('Activité')))", PCT)
m(P, "Nb conducteurs actifs", "CALCULATE(DISTINCTCOUNT('Affectation'[Matricule]), NOT 'Affectation'[Est maintenance])", N0)
m(P, "Nb chauffeurs", "CALCULATE(COUNTROWS('Conducteur'), 'Conducteur'[Est actif])", N0)
m(P, "Nb absents du jour", REF + "RETURN CALCULATE(DISTINCTCOUNT('Absence'[Matricule]), REMOVEFILTERS('Date'), 'Date'[Date] = ref) + 0", N0)
m(P, "Nb chauffeurs disponibles", "[Nb chauffeurs] - [Nb absents du jour] - [Nb missions du jour]", N0)
m(P, "Km par tracteur", "DIVIDE([Km total], DISTINCTCOUNT('Voyage'[Code tracteur]))", N0)
m(P, "Heures par tracteur", "DIVIDE([Heures prod], DISTINCTCOUNT('Voyage'[Code tracteur]))", N1)
m(P, "Heures d'utilisation / jour ouvré par matériel", "DIVIDE([Heures par tracteur], [Jours ouvrés])", N2)

# ---------------------------------------------------------------- atelier
W = "Atelier"
m(W, "Km atelier", "CALCULATE(SUM('Voyage'[Km total]), 'Voyage'[Statut] = \"LIVRE\")", N0)
m(W, "Coût atelier", "SUM('Atelier'[Montant])", EUR)
m(W, "Coût pièces", "CALCULATE([Coût atelier], 'Atelier'[Type ligne] = \"Pièce\")", EUR)
m(W, "Coût main d'oeuvre", "CALCULATE([Coût atelier], 'Atelier'[Type ligne] = \"Main d'oeuvre\")", EUR)
m(W, "Coût sous-traitance", "CALCULATE([Coût atelier], 'Atelier'[Est externe])", EUR)
m(W, "Heures main d'oeuvre", "CALCULATE(SUM('Atelier'[Quantité]), 'Atelier'[Type ligne] = \"Main d'oeuvre\")", N1)
m(W, "Nb OT", "DISTINCTCOUNT('Atelier'[OT ID])", N0)
m(W, "Nb mécaniciens", "DISTINCTCOUNTNOBLANK('Atelier'[Matricule mécanicien])", N0)  # les lignes de pièces n'ont pas de mécanicien
part = {"pièces": "[Coût pièces]", "MO": "[Coût main d'oeuvre]", "sous-traitance": "[Coût sous-traitance]", "total": "[Coût atelier]"}
raisons = {"Coût maintenance": None, "Préventif": "{\"ENT\"}", "Panne": "{\"COR\", \"DEP\"}", "Sinistre": "{\"SIN\"}"}
for rnom, rset in raisons.items():
    for pnom, pexpr in part.items():
        num = pexpr if rset is None else f"CALCULATE({pexpr}, 'Atelier'[Raison] IN {rset})"
        m(W, f"{rnom} / 100 km {pnom}", f"DIVIDE({num}, [Km atelier]) * 100", EUR2)
m(W, "Taux sous-traitance",
  "DIVIDE(CALCULATE([Coût atelier], 'Atelier'[Est externe], 'Atelier'[Compte dans sous traitance]), [Coût atelier])", PCT)
m(W, "Taux préventif", "DIVIDE(CALCULATE([Heures main d'oeuvre], 'Atelier'[Raison] = \"ENT\"), [Heures main d'oeuvre])", PCT)
m(W, "Pannes / 10 000 km",
  "DIVIDE(CALCULATE(DISTINCTCOUNT('Atelier'[OT ID]), 'Atelier'[Raison] IN {\"COR\", \"DEP\"}), [Km atelier]) * 10000", N2)
m(W, "Nb visites", "COUNTROWS('Visite technique')", N0)
m(W, "Nb VT", "CALCULATE([Nb visites], 'Visite technique'[Type visite] = \"VT\")", N0)
m(W, "Nb VO", "CALCULATE([Nb visites], 'Visite technique'[Type visite] = \"VO\")", N0)
m(W, "Taux réussite visites", "DIVIDE(CALCULATE([Nb visites], 'Visite technique'[Est valide]), [Nb visites])", PCT)
m(W, "Taux réussite VT", "DIVIDE(CALCULATE([Nb VT], 'Visite technique'[Est valide]), [Nb VT])", PCT)
m(W, "Taux réussite VO", "DIVIDE(CALCULATE([Nb VO], 'Visite technique'[Est valide]), [Nb VO])", PCT)
m(W, "Coût heure prod direct", "DIVIDE(SUM('Heures mécanicien'[Coût produit]), SUM('Heures mécanicien'[Heures produites]))", EUR2)
m(W, "Heures prod / heures payées", "DIVIDE(SUM('Heures mécanicien'[Heures produites]), SUM('Heures mécanicien'[Heures payées]))", PCT)
m(W, "Coût casse responsable / 100 km", "DIVIDE(CALCULATE([Coût atelier], 'Atelier'[Est casse interne]), [Km total]) * 100", EUR2)

O = "Objectifs"
OBJ = ["Appairage", "MCV %", "HCHC par voyage", "Km à vide €", "CA/KM", "Heures à justifier / HP", "Heures compensées / HP",
       "Frais & primes / HP", "Coût total heure hors carte", "Salaire brut / HP", "Coût maintenance / 100 km",
       "Coût maintenance / 100 km MOD", "Coût maintenance / 100 km pièces", "Coût maintenance / 100 km sous-traitance",
       "Coût heure prod direct", "Taux préventif", "Taux réussite VT", "Taux sous-traitance", "Pannes / 10000 km", "H qual"]
for ind in OBJ:
    m(O, f"Objectif {ind}",
      "VAR annee = MIN(YEAR(MAX('Date'[Date])), YEAR([Date de référence]))\n"
      f"RETURN CALCULATE(AVERAGE('Objectif'[Objectif]), 'Objectif'[Indicateur] = \"{ind}\", 'Objectif'[Année] = annee)", N2)

OBJ_ANNEE = "VAR annee = MIN(YEAR(MAX('Date'[Date])), YEAR([Date de référence]))\n"
for code in ("VL", "PU", "AL", "CH", "CT"):
    m(O, f"Objectif {code}", OBJ_ANNEE + f"RETURN CALCULATE(AVERAGE('Objectif'[Objectif]), 'Objectif'[Code activité] = \"{code}\", 'Objectif'[Année] = annee)", N2)
m(O, "Objectif global", OBJ_ANNEE + "RETURN CALCULATE(AVERAGE('Objectif'[Objectif]), 'Objectif'[Année] = annee)", N2)
m(C, "Pictogramme info", "UNICHAR(9432)")  # « ⓘ » : zone de survol qui ouvre une info-bulle
m(C, "Variation des données", "\"Variation des données\"")

# ---------------------------------------------------------------- rapprochement
R = "Rapprochement"
m(R, "HT atelier", "SUM('Rapprochement'[HT atelier]) + 0", EUR2)
m(R, "HT comptable", "SUM('Rapprochement'[HT compta]) + 0", EUR2)
m(R, "Écart rapprochement", "VAR d = [HT comptable] - [HT atelier] RETURN IF(ABS(d) < 0.01, BLANK(), d)", EUR2)
m(R, "Nb factures", "COUNTROWS('Rapprochement')", N0)
for statut in ("Ok", "Absent Atelier", "Absent Comptable", "Ecart montant"):
    m(R, f"Nb {statut.lower()}", f"CALCULATE([Nb factures], 'Rapprochement'[Statut] = \"{statut}\") + 0", N0)
m(R, "Nb anomalies rapprochement", "[Nb factures] - [Nb ok]", N0)
m(R, "Statut rapprochement", "SELECTEDVALUE('Rapprochement'[Statut])")
m(R, "Montant écritures", "SUM('Écriture comptable'[Montant HT])", EUR2)
m(R, "Montant factures atelier", "SUM('Facture atelier'[Montant HT])", EUR2)

# ---------------------------------------------------------------- carburant
K = "Carburant"
m(K, "Volume litres", "CALCULATE(SUM('Carburant'[Quantité litres]), 'Carburant'[Est prélèvement réel])", N0)
m(K, "Montant carburant €", "CALCULATE(SUM('Carburant'[Montant €]), 'Carburant'[Est prélèvement réel])", EUR)
m(K, "Prix moyen / litre", "DIVIDE([Montant carburant €], [Volume litres])", "#,0.000 €")
m(K, "Conso moyenne L/100 km", "AVERAGEX('Conso FMS', 'Conso FMS'[Conso totale l] * 100 / 'Conso FMS'[Distance km])", N1)
m(K, "Conso moyenne conduite L/100 km", "AVERAGEX('Conso FMS', 'Conso FMS'[Conso conduite l] * 100 / 'Conso FMS'[Distance km])", N1)
m(K, "Conso pondérée L/100 km", "DIVIDE(SUM('Conso FMS'[Conso totale l]) * 100, SUM('Conso FMS'[Distance km]))", N1)
m(K, "CO2 (t)", "SUM('Conso FMS'[CO2 kg]) / 1000", N1)
m(K, "Conso PTO (L)", "SUM('Conso FMS'[Conso PTO l])", N0)
m(K, "Distance FMS", "SUM('Conso FMS'[Distance km])", N0)

# ---------------------------------------------------------------- QHSE
Q = "QHSE"
m(Q, "Nb infractions", "COUNTROWS('Infraction') + 0", N0)
m(Q, "Nb infractions classe 5", "CALCULATE(COUNTROWS('Infraction'), 'Infraction'[Classe] = 5) + 0", N0)
m(Q, "Nb AT", "COUNTROWS('Accident travail') + 0", N0)
m(Q, "Jours perdus", "SUM('Accident travail'[Jours arrêt retenus]) + 0", N0)
m(Q, "Nb anomalies QHSE", "COUNTROWS('Anomalie QHSE') + 0", N0)
m(Q, "Nb événements autoroute interdite", "COUNTROWS('Autoroute interdite') + 0", N0)
m(Q, "Passages autoroutes interdites", "SUM('Autoroute interdite'[Nb passages]) + 0", N0)
m(Q, "Événements autoroute non justifiés", "CALCULATE(COUNTROWS('Autoroute interdite'), NOT 'Autoroute interdite'[Est justifié]) + 0", N0)
m(Q, "Événements autoroute justifiés", "CALCULATE(COUNTROWS('Autoroute interdite'), 'Autoroute interdite'[Est justifié]) + 0", N0)
m(Q, "Nb anomalies matériel", "COUNTROWS('Anomalie matériel') + 0", N0)
m(Q, "Anomalies à traiter", "CALCULATE(COUNTROWS('Anomalie matériel'), 'Anomalie matériel'[Statut] = \"A traiter\") + 0", N0)
m(Q, "Anomalies en cours", "CALCULATE(COUNTROWS('Anomalie matériel'), 'Anomalie matériel'[Statut] = \"En cours\") + 0", N0)
m(Q, "Anomalies traitées 7 derniers jours",
  REF + "RETURN CALCULATE(COUNTROWS('Anomalie matériel'), REMOVEFILTERS('Date'), 'Anomalie matériel'[Statut] = \"Traitée\",\n"
  "    'Anomalie matériel'[Date traitement] >= ref - 7, 'Anomalie matériel'[Date traitement] <= ref) + 0", N0)

# ---------------------------------------------------------------- absences
B = "Absences"
m(B, "Absents uniques", "DISTINCTCOUNT('Absence'[Matricule]) + 0", N0)
m(B, "Jours d'absence", "COUNTROWS('Absence') + 0", N0)
m(B, "Jours d'absence / jour ouvré", "DIVIDE([Jours d'absence], [Jours ouvrés])", N1)
for nom, motifs in (("maladie", "{\"AM\"}"), ("congés", "{\"CP\"}"), ("absence (maladie + injustifiée)", "{\"AM\", \"ABS\"}"),
                    ("repos maison", "{\"RM\"}"), ("sans solde", "{\"SS\"}")):
    m(B, f"Jours {nom}", f"CALCULATE(COUNTROWS('Absence'), 'Absence'[Motif] IN {motifs}) + 0", N0)
    m(B, f"Absents {nom}", f"CALCULATE(DISTINCTCOUNT('Absence'[Matricule]), 'Absence'[Motif] IN {motifs}) + 0", N0)

# ---------------------------------------------------------------- sélecteurs (tables de choix + SWITCH)
TABLES_SELECTEURS = {
    "Sélecteur activité": ("Indicateur", [("CA", 1), ("CA / jour ouvré", 2), ("MCV %", 3), ("Appairage", 4)]),
    "Sélecteur coût": ("Indicateur", [("Salaire brut / HP", 1), ("Frais & primes / HP", 2),
                                       ("Passages autoroute interdite / voyage", 3), ("HCHC / voyage", 4)]),
    "Sélecteur anomalies": ("Indicateur", [("Anomalies à traiter", 1), ("Anomalies en cours", 2), ("Anomalies traitées 7 derniers jours", 3)]),
    "Sélecteur atelier qualité": ("Indicateur", [("Taux préventif", 1), ("Pannes / 10 000 km", 2), ("Taux réussite VO", 3), ("Taux réussite VT", 4)]),
    "Sélecteur atelier productivité": ("Indicateur", [("Taux sous-traitance", 1), ("Heures prod / heures payées", 2), ("Coût heure prod direct", 3)]),
    "Vue heures": ("Vue", [("€/HP", 1), ("Heures", 2), ("€", 3)]),
    "Filtre période": ("Période", [("N-1", 1), ("Semaine en cours", 2)]),
}
for p in ("pièces", "MO", "sous-traitance", "total"):
    TABLES_SELECTEURS[f"Sélecteur atelier {p}"] = ("Indicateur", [("Coût maintenance", 1), ("Préventif", 2), ("Panne", 3), ("Sinistre", 4)])
    m("Sélecteurs", f"Indicateur atelier {p}",
      f"SWITCH(SELECTEDVALUE('Sélecteur atelier {p}'[Indicateur], \"Coût maintenance\"),\n"
      + ",\n".join(f"    \"{r}\", [{r} / 100 km {p}]" for r in raisons) + ")", EUR2)
S = "Sélecteurs"
m(S, "Indicateur activité", "SWITCH(SELECTEDVALUE('Sélecteur activité'[Indicateur], \"CA\"), \"CA\", [CA facturé], "
  "\"CA / jour ouvré\", [CA moyen / jour ouvré], \"MCV %\", [MCV %], \"Appairage\", [Appairage])")
m(S, "Indicateur coût", "SWITCH(SELECTEDVALUE('Sélecteur coût'[Indicateur], \"Salaire brut / HP\"), \"Salaire brut / HP\", [Salaire brut / heure prod], "
  "\"Frais & primes / HP\", [Frais & primes / HP], \"Passages autoroute interdite / voyage\", [Passages autoroute interdite / voyage], "
  "\"HCHC / voyage\", [HCHC / voyage])")
m(S, "Indicateur anomalies", "SWITCH(SELECTEDVALUE('Sélecteur anomalies'[Indicateur]), \"Anomalies à traiter\", [Anomalies à traiter], "
  "\"Anomalies en cours\", [Anomalies en cours], \"Anomalies traitées 7 derniers jours\", [Anomalies traitées 7 derniers jours], [Nb anomalies matériel])", N0)
m(S, "Indicateur atelier qualité", "SWITCH(SELECTEDVALUE('Sélecteur atelier qualité'[Indicateur], \"Pannes / 10 000 km\"), "
  "\"Taux préventif\", [Taux préventif], \"Pannes / 10 000 km\", [Pannes / 10 000 km], \"Taux réussite VO\", [Taux réussite VO], "
  "\"Taux réussite VT\", [Taux réussite VT])")
m(S, "Indicateur atelier productivité", "SWITCH(SELECTEDVALUE('Sélecteur atelier productivité'[Indicateur], \"Coût heure prod direct\"), "
  "\"Taux sous-traitance\", [Taux sous-traitance], \"Heures prod / heures payées\", [Heures prod / heures payées], "
  "\"Coût heure prod direct\", [Coût heure prod direct])")
# étiquettes des segments-boutons (valeur affichée dans chaque bouton, au format de l'indicateur) : le bouton = la tuile
def etiquette(nom, table, cas):
    corps = ", ".join(f"\"{v}\", {expr}" for v, expr in cas)
    m(S, nom, f"SWITCH(SELECTEDVALUE('{table}'[Indicateur]), {corps})")


etiquette("Étiquette indicateur activité", "Sélecteur activité", [
    ("CA", "FORMAT([CA facturé] / 1000000, \"0.00\") & \" M€\""), ("CA / jour ouvré", "FORMAT([CA moyen / jour ouvré] / 1000, \"0.0\") & \" k€\""),
    ("MCV %", "FORMAT([MCV %], \"0.0 %\")"), ("Appairage", "FORMAT([Appairage], \"0.0 %\")")])
etiquette("Étiquette indicateur coût", "Sélecteur coût", [
    ("Salaire brut / HP", "FORMAT([Salaire brut / heure prod], \"0.00\") & \" €\""), ("Frais & primes / HP", "FORMAT([Frais & primes / HP], \"0.00\") & \" €\""),
    ("Passages autoroute interdite / voyage", "FORMAT([Passages autoroute interdite / voyage], \"0.000\")"),
    ("HCHC / voyage", "FORMAT([HCHC / voyage], \"0.00\") & \" h\"")])
etiquette("Étiquette indicateur anomalies", "Sélecteur anomalies", [
    ("Anomalies à traiter", "FORMAT([Anomalies à traiter] + 0, \"0\")"), ("Anomalies en cours", "FORMAT([Anomalies en cours] + 0, \"0\")"),
    ("Anomalies traitées 7 derniers jours", "FORMAT([Anomalies traitées 7 derniers jours] + 0, \"0\")")])
for nom, eur_hp, h, eur in (("hors carte", "[Coût heure hors carte / HP]", "[Heures hors carte]", "[Heures hors carte €]"),
                            ("à justifier", "[Heures à justifier payées € / HP]", "[Heures à justifier payées]", "[Heures à justifier payées €]"),
                            ("compensées", "[Heures compensées € / HP]", "[Heures compensées (base contrat)]", "[Heures compensées €]")):
    m(S, f"Sélection heures {nom}",
      f"SWITCH(SELECTEDVALUE('Vue heures'[Vue], \"€/HP\"), \"€/HP\", {eur_hp}, \"Heures\", {h}, \"€\", {eur})", N2)

# ---------------------------------------------------------------- rentabilité (coûts réels)
N = "Rentabilité"
for nom, col in (("CA (tracteurs)", "CA"), ("Péages réels", "Péages"), ("Carburant réel", "Carburant"),
                 ("Coût atelier réel", "Atelier"), ("Marge directe", "Marge directe")):
    m(N, nom, f"SUM('Rentabilité tracteur'[{col}])", EUR)
m(N, "Marge directe %", "DIVIDE([Marge directe], [CA (tracteurs)])", PCT)
m(N, "Marge directe / km", "DIVIDE([Marge directe], SUM('Rentabilité tracteur'[Km]))", EUR2)
for nom, col in (("CA (conducteurs)", "CA"), ("Salaire chargé", "Salaire chargé"), ("Frais conducteur", "Frais"),
                 ("Carburant conducteur", "Carburant"), ("Contribution conducteur", "Contribution")):
    m(N, nom, f"SUM('Rentabilité conducteur'[{col}])", EUR)
m(N, "Contribution %", "DIVIDE([Contribution conducteur], [CA (conducteurs)])", PCT)
m(N, "Contribution / heure payée", "DIVIDE([Contribution conducteur], SUM('Rentabilité conducteur'[Heures payées]))", EUR2)

# ---------------------------------------------------------------- qualité des données et référentiel
D = "Qualité des données"
m(D, "Lignes importées", "SUM('Import'[Lignes])", N0)
m(D, "Lignes corrigées ou écartées", "SUM('Contrôle qualité'[Lignes concernées])", N0)
m(D, "Nb tests dbt", "CALCULATE(COUNTROWS('Résultat dbt'), 'Résultat dbt'[Type nœud] = \"test\")", N0)
m(D, "Nb tests réussis", "CALCULATE([Nb tests dbt], 'Résultat dbt'[Statut] = \"pass\")", N0)
m(D, "Taux de tests réussis", "DIVIDE([Nb tests réussis], [Nb tests dbt])", PCT)
m(D, "Nb changements de contrat", "CALCULATE(COUNTROWS('Historique conducteur'), NOT 'Historique conducteur'[Version courante])", N0)

# paramètres de champs (NAMEOF) : libellé, référence, ordre
PARAMETRES_CHAMPS = {
    "Choix période": [("Année", "'Date'[Année]"), ("Trimestre", "'Date'[Trimestre année]"), ("Mois", "'Date'[Mois année]"),
                      ("Semaine", "'Date'[Semaine affichage]")],
    "Pic ou moyenne tracteurs": [("Moyenne", "'Mesures'[Nb tracteurs / jour ouvré]"), ("Pic", "'Mesures'[Pic tracteurs]")],
    "Pic ou moyenne absences": [("Pic", "'Mesures'[Absents uniques]"), ("Moyenne", "'Mesures'[Jours d'absence / jour ouvré]")],
    "Sélecteur indicateur QHSE": [("Nb anomalies", "'Mesures'[Nb anomalies QHSE]"), ("Nb AT", "'Mesures'[Nb AT]"),
                                  ("Nb infractions", "'Mesures'[Nb infractions]")],
    "Axe QHSE": [("Type d'anomalies", "'Anomalie QHSE'[Type anomalie]"), ("Type accident", "'Accident travail'[Type accident]"),
                 ("Infraction RSE", "'Infraction'[Type infraction]")],
}

# Une page par sujet plutôt qu'une page par indicateur : le tableau affiche le thème choisi dans un segment.
# Thème -> mesures, dans l'ordre d'affichage.
THEMES_INDICATEURS = {
    "Indicateurs client": {
        "CA": ["CA facturé", "CA facturé évolution"],
        "Voyages": ["CA facturé", "Nb voyages", "CA / voyage", "CA / voyage évolution", "Nb voyages / jour ouvré",
                    "Nb voyages évolution"],
        "CA / jour ouvré": ["CA facturé", "CA moyen / jour ouvré (k€)"],
        "CA / km et heure": ["CA facturé", "CA / heure", "CA / km", "CA / km évolution"],
        "Km et heures": ["CA facturé", "Heures prod", "Km total", "Km total évolution"],
        "Marge (MCV)": ["CA facturé", "Dernier prix", "MCV €", "MCV %", "MCV € évolution"],
        "Appairage": ["CA facturé", "Km à vide €", "Appairage", "Appairage évolution"],
        "Autoroute": ["CA facturé", "Autoroute € / 100 km", "Autoroute € / 100 km évolution"],
        "Qté / voyage": ["CA facturé", "Qté livrée", "Qté facturée / voyage", "Qté facturée / voyage évolution"],
    },
    "Indicateurs relation": {
        "CA": ["CA réparti", "CA réparti évolution"],
        "Voyages": ["CA réparti", "Nb voyages", "Nb voyages / jour ouvré", "Nb voyages évolution"],
        "CA / jour ouvré": ["CA réparti", "CA moyen / jour ouvré réparti"],
        "CA / km": ["CA réparti", "Km total", "CA / km réparti", "CA / km réparti évolution"],
        "CA / heure": ["CA réparti", "Heures prod", "CA / heure réparti", "CA / heure réparti évolution"],
        "MCV €": ["CA réparti", "MCV €", "MCV € évolution"],
        "MCV %": ["CA réparti", "MCV €", "MCV %", "MCV % évolution"],
        "Appairage": ["CA réparti", "Appairage", "Appairage évolution"],
        "Autoroute": ["CA réparti", "Autoroute € / 100 km", "Autoroute € / 100 km évolution"],
    },
    "Indicateurs heures conducteur": {
        "Heures payées": ["Heures payées", "Heures payées / mois", "Écart moyen heures payées"],
        "Heures compensées": ["Heures compensées (base contrat)", "Heures compensées €", "Heures compensées € / HP", "Heures prod"],
        "Heures à justifier": ["Heures à justifier payées", "% heures à justifier / heures prod", "Heures à justifier payées €",
                               "Heures à justifier payées € / HP", "Heures prod"],
        "Frais et primes": ["Frais conv €", "Frais conv / HP", "Frais non-conv €", "Frais non-conv / HP", "Heures prod"],
    },
}
for _t, _themes in THEMES_INDICATEURS.items():  # (libellé, référence, thème) : une ligne par mesure et par thème
    PARAMETRES_CHAMPS[_t] = [(m, f"'Mesures'[{m}]", th) for th, ms in _themes.items() for m in ms]
