"""Contrôles statiques des rapports PBIP (sans ouvrir Power BI Desktop), rejoués en CI :
1. aucune mesure dans un rôle qui exige une colonne (axe, lignes, légende, segment...) ;
2. chaque valeur littérale de filtre a le type de la colonne filtrée ;
3. aucune référence à un champ absent du modèle ;
4. chaque sélection enregistrée d'un paramètre de champs désigne un champ du modèle ;
5. aucun état de dépliage de matrice figé dans le rapport, groupes de segments synchronisés aux noms lisibles ;
6. chaque valeur sélectionnée sur une table calculée DATATABLE (sélecteur) existe dans cette table ;
7. chaque lien vers un autre rapport a sa règle de remplacement au déploiement (parameter.yml).
"""
import json
import re
import sys
from pathlib import Path

PBI = Path(__file__).resolve().parent
MODELE = PBI / "TransVal.SemanticModel" / "definition"


def lire_modele():
    """Noms des tables, colonnes, mesures et hiérarchies du modèle TMDL."""
    unq = lambda s: s.strip().strip("'").replace("''", "'")  # noqa: E731
    cols, mesures, hier = set(), set(), set()
    for f in (MODELE / "tables").glob("*.tmdl"):
        txt = f.read_text(encoding="utf-8")
        table = unq(re.match(r"table (.+)", txt).group(1))
        cols |= {(table, unq(c)) for c in re.findall(r"\n\tcolumn (.+)", txt)}
        mesures |= {unq(re.split(r" =", m_)[0]) for m_ in re.findall(r"\n\tmeasure (.+)", txt)}
        hier |= {(table, unq(h)) for h in re.findall(r"\n\thierarchy (.+)", txt)}
    return cols, mesures, hier


def types_colonnes():
    """(table, colonne) -> dataType TMDL."""
    t = {}
    for f in (MODELE / "tables").glob("*.tmdl"):
        txt = f.read_text(encoding="utf-8")
        table = re.match(r"table (.+)", txt).group(1).strip("'").replace("''", "'")
        for nom, typ in re.findall(r"\n\tcolumn (.+)\n\t\tdataType: (\w+)", txt):
            t[(table, nom.strip("'").replace("''", "'"))] = typ
    return t


ROLES_COLONNE = {"Category", "Rows", "Columns", "Legend", "Series", "Axis", "Group", "Details", "Location", "Latitude", "Longitude"}
SEGMENTS = ("slicer", "Chiclet", "textFilter", "textSearch", "advancedSlicer", "Timeline")


def type_litteral(v):
    if v in ("true", "false"):
        return "boolean"
    if v.startswith("datetime'"):
        return "dateTime"
    if v.startswith("'"):
        return "string"
    if re.fullmatch(r"-?\d+L", v):
        return "int64"
    if re.fullmatch(r"-?[\d.]+D|-?[\d.]+M", v):
        return "double"
    return None


def valeurs_datatable():
    """Tables calculées DATATABLE (sélecteurs, paramètres) : valeurs texte autorisées par table."""
    res = {}
    for f in PBI.glob("*.SemanticModel/definition/tables/*.tmdl"):
        t = f.read_text(encoding="utf-8")
        m = re.search(r"DATATABLE\((.*?)\}\s*\)", t, re.S)
        if m:
            nom = re.match(r"table '?([^'\n]+?)'?\s*$", t.splitlines()[0]).group(1)
            res[nom] = set(re.findall(r'"([^"]*)"', m.group(1).split("{", 1)[1]))
    return res


def main():
    cols, mesures, hier = lire_modele()
    types = types_colonnes()
    datatables = valeurs_datatable()
    problemes = []
    for f in PBI.glob("*.Report/definition/**/*.json"):
        data = json.loads(f.read_text(encoding="utf-8"))
        v = data.get("visual", {})
        vt = v.get("visualType", "")
        noms = [p.get("nativeQueryRef") for r in v.get("query", {}).get("queryState", {}).values()
                 for p in r.get("projections", []) if p.get("nativeQueryRef")]
        refs = [p.get("queryRef") for r in v.get("query", {}).get("queryState", {}).values() for p in r.get("projections", [])]
        doublons = {n for n in noms if noms.count(n) > 1 and len({q for q, nn in zip(refs, noms) if nn == n}) > 1}
        if doublons:
            problemes.append(f"{f.parent.name} [{vt}] nom interne en double : {sorted(doublons)}")
        for role, r in v.get("query", {}).get("queryState", {}).items():
            for p in r.get("projections", []):
                fl = p.get("field", {})
                k = next(iter(fl), None)
                x = fl.get(k, {})
                if k == "Aggregation":
                    k, x = next(iter(x["Expression"])), x["Expression"][next(iter(x["Expression"]))]
                if k in ("Column", "Measure") and "Entity" in x.get("Expression", {}).get("SourceRef", {}):
                    t, n = x["Expression"]["SourceRef"]["Entity"], x["Property"]
                    if (k == "Measure" and n not in mesures) or (k == "Column" and (t, n) not in cols):
                        problemes.append(f"{f.parent.name} [{vt}/{role}] champ absent du modèle : {t}[{n}]")
                # exception : l'étiquette (Label) d'un segment-boutons est une mesure affichée dans chaque bouton
                if "Measure" in p.get("field", {}) and (role in ROLES_COLONNE or any(s in vt for s in SEGMENTS))                         and not (vt == "advancedSlicerVisual" and role == "Label"):
                    problemes.append(f"{f.parent.name} [{vt}/{role}] mesure en rôle colonne : {p['queryRef']}")
                agg = p.get("field", {}).get("Aggregation")
                if agg and agg.get("Function") in (0, 1, 6, 7, 8):
                    col = agg["Expression"].get("Column", {})
                    cle = (col.get("Expression", {}).get("SourceRef", {}).get("Entity"), col.get("Property"))
                    if types.get(cle) in ("string", "dateTime"):
                        problemes.append(f"{f.parent.name} [{vt}/{role}] somme/moyenne sur une colonne {types[cle]} : {p['queryRef']}")

        def filtres(o, alias):
            if isinstance(o, list):
                for x in o:
                    filtres(x, alias)
            elif isinstance(o, dict):
                if isinstance(o.get("From"), list):
                    alias = {**alias, **{x["Name"]: x.get("Entity") for x in o["From"]}}
                cond = o.get("In") or o.get("Comparison")
                if isinstance(cond, dict):
                    exprs = cond.get("Expressions") or [cond.get("Left")]
                    vals = [x for row in cond.get("Values", []) for x in row] + ([cond["Right"]] if "Right" in cond else [])
                    for e in exprs:
                        c = (e or {}).get("Column")
                        if not c:
                            continue
                        sr = c["Expression"]["SourceRef"]
                        table = sr.get("Entity") or alias.get(sr.get("Source"))
                        attendu = types.get((table, c["Property"]))
                        for val in vals:
                            lit = val.get("Literal", {}).get("Value") if isinstance(val, dict) else None
                            tl = type_litteral(lit) if lit else None
                            if attendu and tl and tl != attendu and not (attendu == "double" and tl == "int64"):
                                problemes.append(f"{f.parent.name} filtre {table}[{c['Property']}] ({attendu}) = {lit}")
                            if tl == "string" and table in datatables and lit[1:-1].replace("''", "'") not in datatables[table]:
                                problemes.append(f"{f.parent.name} sélection inexistante dans {table} : {lit}")
                for x in o.values():
                    filtres(x, alias)

        if "expansionStates" in v:  # lignes dépliées figées dans le fichier
            problemes.append(f"{f.parent.name} état de dépliage enregistré")
        nom_sync = v.get("syncGroup", {}).get("groupName", "").partition(".")[0]
        if "_" in nom_sync or nom_sync.isupper():
            problemes.append(f"{f.parent.name} groupe de segments au nom technique : {nom_sync}")
        filtres(data, {})
        for t, c in re.findall(r"'''([^'\]]+)''\[([^\]]+)\]'", f.read_text(encoding="utf-8")):  # sélection de paramètre de champs
            if (t, c) not in cols and not (t == "Mesures" and c in mesures):
                problemes.append(f"{f.parent.name} sélection de paramètre de champs inconnue : '{t}'[{c}]")
    parametres = (PBI / "parameter.yml").read_text(encoding="utf-8")
    for f in PBI.glob("*.Report/definition/pages/*/visuals/*/visual.json"):  # liens vers un autre rapport
        for j in set(re.findall(r"transval-(?:espace-de-travail|rapport-[a-z0-9-]+)", f.read_text(encoding="utf-8"))):
            if f'"{j}"' not in parametres:
                problemes.append(f"{f.parents[4].name} lien inter-rapports sans remplacement au déploiement : {j}")
    for p in sorted(set(problemes)):
        print(" ", p)
    print(f"{len(set(problemes))} problème(s) détecté(s)")
    return problemes


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
