# 5. Power BI — un modèle sémantique unique sur l'entrepôt, 23 rapports de pilotage

## Le modèle sémantique `TransVal`

`powerbi/TransVal.SemanticModel` est au format **PBIP / TMDL** (texte, versionné dans Git, relu en revue de code) et
entièrement **généré** par [`powerbi/build_model.py`](../powerbi/build_model.py) :

1. chaque table utile de l'entrepôt est exportée en Parquet (`powerbi/donnees/`), colonnes renommées en français ;
2. le script écrit les tables, colonnes typées, relations, hiérarchie de dates et les mesures de
   [`powerbi/mesures.py`](../powerbi/mesures.py).

Power Query ne fait **plus aucune transformation** : chaque table est un simple
`Parquet.Document(File.Contents(DossierDonnees & "\<table>.parquet"))`. Tout le nettoyage est dans l'entrepôt.

| | Power BI de départ | Modèle TransVal |
|---|---|---|
| Tables | une copie par rapport et par requête, tables de dates automatiques | 42 tables de données, 19 sélecteurs / paramètres de champs, 1 table de mesures |
| Requêtes Power Query avec logique | SQL natif + étapes M dans chaque requête | 0 (lecture Parquet) |
| Mesures | recopiées d'un rapport à l'autre | 352, une définition chacune, rangées en 15 dossiers |
| Colonnes calculées DAX | nombreuses | 0 (calculées dans l'entrepôt) |
| Relations | nombreuses bidirectionnelles | 60, dont 2 bidirectionnelles assumées (factures ↔ rapprochement) ; aucune clé vide ni orpheline |
| Sécurité | aucune | rôles « Exploitant » (sécurité par ligne dynamique) et « Direction » |
| Date / heure automatique | activée | désactivée ; une table `Date` marquée + « Hiérarchie de dates » |
| `TODAY()` / `NOW()` | dans les mesures | 0 : `[Date de référence]` lue dans la table `Paramètres` |

Les variantes N-1 / évolution de chaque indicateur sont produites par une fonction (`evo()`), pas recopiées.
Exemple d'une mesure avant / après :

```dax
// avant (dans chaque rapport, avec ses propres filtres)
Heures compensées € = CALCULATE( SUMX('Compteur mensuel', ('Compteur mensuel'[Heures réalisées] - 'Compteur mensuel'[Heures base]) * -1),
    IF( DAY(TODAY()) >= 10, 'Compteur mensuel'[Date] < DATE(YEAR(TODAY()), MONTH(TODAY()), 1), ... ) ) * 'Activité totale'[Salaire brut / Heure de prod]

// après (heures compensées calculées dans l'entrepôt ; règle du 10 du mois sur la date de référence)
Heures compensées € = [Heures compensées (base contrat)] * [Salaire brut / heure prod]
```

**Pas de ligne vide dans les rapports.** Une clé vide ou inconnue est rattachée par Power BI à un membre « vide » de la
dimension, qui apparaît sans libellé en tête des tableaux et dans les segments. Les deux cas métier sont traités à l'export :

- les **voyages spot** (ponctuels, sans relation tarifaire) sont rattachés à la relation **« Spot (sans relation) »**, dont
  les attributs sont renseignés (type « Ponctuelle », pas une location, villes « Non renseignée ») pour qu'aucun segment
  n'affiche de valeur vide ; la marge sur coûts variables les exclut par une règle explicite ;
- les **jours d'immobilisation** d'un tracteur à l'atelier (sans conducteur) forment leur propre table `Immobilisation`,
  reliée aux dates, au matériel et à l'activité du tracteur, mais pas aux conducteurs : l'indicateur
  « Jours tracteur en maintenance » la compte, et aucun faux conducteur n'apparaît dans les listes.

Les 60 relations n'ont plus aucune clé vide ni orpheline, et aucun chiffre ne change (parité ci-dessous).

### Parité Power BI ↔ entrepôt

[`tests/parite_powerbi.dax`](../tests/parite_powerbi.dax) recalcule **chaque ligne de `mart_kpi` avec les mesures DAX**
sur sa période : **2 213 valeurs (53 indicateurs × mois, années, total) — 0 écart.**
La chaîne de preuve est donc complète : Power BI de départ → entrepôt (`tests/test_parity.py`) → nouveau modèle Power BI.

## 23 rapports de pilotage, un par sujet

Les rapports sont des rapports légers (format PBIR) connectés au modèle central : un rapport par sujet, on sait où
chercher d'après le nom, sans page d'accueil qui aiguille vers plusieurs thèmes.

| Domaine | Rapports (pages) |
|---|---|
| Commercial | Activité clients (9) · Activité par relation (2) · Coût des trajets (2) · Prix et indexation clients (2) · Productivité hebdomadaire (2) |
| Exploitation | Tableau de bord exploitant (25) · Heures conducteurs (4) · Projection des heures (1) · Missions conducteurs (1) · Absences conducteurs (4) |
| Atelier et parc | Maintenance atelier (18) · Parc matériel (3) · Anomalies matériel (3) |
| Carburant | Consommation carburant (5) · Prix du gazole (5) |
| QHSE | Tableau de bord QHSE (1) · Infractions RSE (3) · Autoroutes interdites (5) |
| Contrôle de gestion | Prestations à facturer (7) · Rapprochement atelier et comptabilité (3) · Rentabilité (2) |
| RH et données | Référentiel conducteurs (2) · Qualité des données (2) |
| **Total** | **23 rapports, 111 pages, 1 698 visuels** |

Principes de conception :

- **Une page par famille d'indicateurs**, pas une page par indicateur : « Indicateurs par client », « Indicateurs par
  relation », « Heures et frais par conducteur » ont un **segment de thème** qui choisit les colonnes du tableau (CA,
  CA par jour ouvré, km et heures, marge, appairage…). Techniquement : un paramètre de champs avec une colonne « Thème »
  (une même mesure peut appartenir à plusieurs thèmes), déclaré dans [`mesures.py`](../powerbi/mesures.py).
- **Vocabulaire uniforme** : pages nommées en clair (« CA par km et par heure », « Heures payées », « Coût des pièces »),
  info-bulles préfixées « Info-bulle – », pages de détail masquées du navigateur et ouvertes par bouton.
- **Liens entre rapports** : les boutons du tableau de bord exploitant qui ouvrent « Heures conducteurs » sont des liens
  web vers le rapport publié. Son adresse n'existe qu'après publication : le lien porte des jetons
  (`transval-espace-de-travail`, `transval-rapport-heures-conducteurs`) que le déploiement remplace par les identifiants
  réels ([`parameter.yml`](../powerbi/parameter.yml)) ; [`verifier_rapports.py`](../powerbi/verifier_rapports.py) échoue si un
  jeton n'y a pas de règle. Dans Power BI Desktop, avant publication, ces liens ne mènent nulle part.
- **Pas de visuel cartographique dépendant d'un compte** (Azure Maps, Flow Map exigent un compte professionnel ou une
  clé) : quantités livrées par ville et principaux flux en barres.
- **Charte graphique commune** (thème `powerbi/theme/`) : bandeau de titre, onglets, bande de filtres, tuiles d'indicateurs,
  pied de page avec la source et la date d'actualisation ; couleurs conditionnelles limitées à trois niveaux
  (bon / moyen / mauvais).
- **Tuiles-sélecteurs** (Anomalies matériel, tableau de bord exploitant) : chaque bouton du segment affiche le nom et la
  valeur de l'indicateur ; on clique sur la tuile comme sur un paramètre de champs, la tuile active est surlignée.
- **Exploitation J+1** : une page globale et une page par activité, même disposition, une couleur par activité :
  missions, CA prévu, tracteurs engagés / libres, conducteurs sans mission pour le prochain jour ouvré ; journée et
  semaine en cours ; tendances 4 et 12 semaines ; équipe du jour.
- **Indicateurs hebdomadaires** : « CA de la semaine » / « Nb voyages de la semaine » suivent la semaine du contexte ;
  une évolution n'est affichée que si la période a des données.
- **Info-bulles « d'où vient ce chiffre »** (Maintenance atelier) : pour chaque indicateur, la mesure DAX, le modèle dbt et
  les sources dont il dépend.
- **Attentes à facturer** : franchise de 3 h sur site pour toutes les activités (1 h 30 au chargement + 1 h 30 à la
  livraison, durée de mise à disposition du contrat type citerne sur plage horaire).
- **Projection des heures** : repères 152 h (35 h légales), 186 h (contrat grand routier) et 208 h (48 h / semaine en
  moyenne, directive 2002/15/CE).

[`verifier_rapports.py`](../powerbi/verifier_rapports.py) contrôle les 23 rapports sans ouvrir Power BI (champs existants,
types des filtres, sélections de segments valides, liens de déploiement) ; il tourne en CI.

## Ce que l'entrepôt permet en plus : 3 rapports et la sécurité par ligne

| Rapport | Pages | Ce qu'il montre | Pourquoi impossible sans entrepôt |
|---|---|---|---|
| **Qualité des données** | Contrôles à l'import · Imports et tests dbt | doublons de recouvrement absorbés, versions CDC, saisies corrigées (« valide », « Decrochage », jour « 00 », Oui/oui/OUI…), écarts de rapprochement ; lignes chargées par lot ; résultat de chaque test dbt | sans couche RAW conservée ni tests, rien à mesurer |
| **Rentabilité** | Par tracteur · Par conducteur | marge directe sur coûts **réels** (CA − péages − carburant prélevé − atelier) par tracteur ; contribution par conducteur (CA − salaire chargé − frais − carburant), par type de contrat | il faut croiser TMS, ERP carburant, atelier et paie au même grain |
| **Référentiel conducteurs** | Conducteurs et contrats · Historique des contrats | type de contrat (186 / 169 / 151,67 / 121,33 h), statut CDI/CDD ; historique des changements (SCD2) | le référentiel source n'expose que son état courant |

**Historique des contrats.** Le référentiel RH n'expose que son état courant ; RAW en conserve une photo à chaque lot.
[`dim_conducteur_historique`](../dbt/models/marts/dim_conducteur_historique.sql) en déduit les versions (SCD2) — même résultat
qu'un `dbt snapshot` pris à chaque import, mais rejouable en `--full-refresh`. Limite assumée et visible dans le rapport :
un changement est daté au **lot qui l'observe** (31/08), pas à sa date d'effet RH (01/05) ; pour la date exacte il faudrait
capter le journal des mouvements à la source (CDC).

**Sécurité par ligne (RLS).** Table `Habilitation` (e-mail → codes activité, seed dbt, identités fictives) et deux rôles :

| Rôle | Règle | Vérifié (impersonation DAX) |
|---|---|---|
| Exploitant | `Conducteur`, `Matériel` et `Activité` filtrés sur les activités de `USERPRINCIPALNAME()` ; les remplaçants (pool partagé) restent visibles d'un exploitant habilité | compte sans habilitation : 0 voyage, 0 conducteur ; exploitant chimie : 6 434 voyages = tous les voyages de l'activité CH |
| Direction | aucun filtre | 32 953 voyages, 62 conducteurs |

Sans la clause « remplaçants », l'exploitant chimie ne voyait que 6 013 de ses 6 434 voyages (ceux conduits par un
remplaçant rattaché à une autre activité disparaissaient) : la règle a été corrigée après ce test.

### Données fictives : des profils très différents

Des données tirées uniformément donnent des rapports plats (tous les clients se ressemblent, tous les conducteurs au
même plancher d'heures payées). Le générateur attribue donc des **profils** (générateur dédié, graine 2122) :

| Axe | Profil | Effet mesuré (2026) |
|---|---|---|
| Clients | poids en loi de puissance, politique tarifaire (−20 % à +22 %), propension aux attentes | CA de 2,9 k€ à 992 k€ ; les 5 premiers = 42 % du CA |
| Activités | distance et prix au km propres (conteneur court et cher, vrac liquide long) | CA/km de 2,03 € (vrac liquide) à 3,49 € (conteneur) |
| Saisonnalité | creux d'août et de décembre, récoltes (alimentaire), chantiers de printemps (pulvérulent) | août ≈ −18 % de voyages |
| Conjoncture | chaque mois et chaque activité tirés entre exceptionnel (×1,28) et catastrophique (×0,55), plus un aléa par semaine | CA mensuel 2025 de 358 k€ à 841 k€ |
| Sites | temps de livraison propre à chaque client (plus long en chimie, en vrac liquide et en hiver), taux de remplissage par flux | 0,6 à 3,0 h par livraison ; 10,5 à 26 t en moyenne par client |
| Conducteurs | amplitude (petit rouleur / standard / grand routier) plafonnée à 12 h de service par jour, style de conduite, absentéisme, infractions | 28 → 43 L/100 km ; 0 → 8 infractions |
| Contrats | base mensuelle du transport routier : 186 h grand routier (43 h/sem. avec équivalence), 169 h courte distance (39 h/sem.), 151,67 h (35 h) ou 121,33 h (temps partiel) pour les remplaçants ; heures sup. majorées 25 % puis 50 % | heures payées 121 → 269 h/mois ; « Heures compensées (base contrat) » révèle le sous-emploi des remplaçants |
| Tracteurs | taux d'utilisation, consommation par marque, pannes croissantes avec l'âge | — |
| Gazole | prix mensuel en marche aléatoire (et non une pente régulière) | — |
| Noms | conducteurs, mécaniciens et clients inventés syllabe par syllabe ; tout tirage qui existe dans les fichiers INSEE des prénoms et des noms de famille (ou à une lettre d'un nom courant) est rejeté | aucun nom réel |

Un second générateur (`R2`) complète par ailleurs les indicateurs qui restaient vides (sinistres en partie sous-traités,
conducteur du jour des ordres de travail, coût chargé par mécanicien, entretien courant pour 72 à 88 % d'heures
produites). Le calendrier s'arrête à la fin de l'année de la date de référence. Les parités restent exactes :
Power BI de départ ↔ entrepôt 93/97 (+ 4 écarts voulus), entrepôt ↔ DAX 2 213 valeurs, 0 écart.

## Aperçu des 23 rapports

Première page de chaque rapport, capturée dans Power BI Desktop une fois les données chargées.

### Commercial

| **Activité clients** | **Activité par relation** |
|---|---|
| ![Activité clients](images/rapports/activite-clients.png) | ![Activité par relation](images/rapports/activite-par-relation.png) |

| **Coût des trajets** | **Prix et indexation clients** |
|---|---|
| ![Coût des trajets](images/rapports/cout-des-trajets.png) | ![Prix et indexation clients](images/rapports/prix-et-indexation-clients.png) |

| **Productivité hebdomadaire** | |
|---|---|
| ![Productivité hebdomadaire](images/rapports/productivite-hebdomadaire.png) | |

### Exploitation

| **Tableau de bord exploitant** | **Heures conducteurs** |
|---|---|
| ![Tableau de bord exploitant](images/rapports/tableau-de-bord-exploitant.png) | ![Heures conducteurs](images/rapports/heures-conducteurs.png) |

| **Projection des heures** | **Missions conducteurs** |
|---|---|
| ![Projection des heures](images/rapports/projection-des-heures.png) | ![Missions conducteurs](images/rapports/missions-conducteurs.png) |

| **Absences conducteurs** | |
|---|---|
| ![Absences conducteurs](images/rapports/absences-conducteurs.png) | |

### Atelier et parc

| **Maintenance atelier** | **Parc matériel** |
|---|---|
| ![Maintenance atelier](images/rapports/maintenance-atelier.png) | ![Parc matériel](images/rapports/parc-materiel.png) |

| **Anomalies matériel** | |
|---|---|
| ![Anomalies matériel](images/rapports/anomalies-materiel.png) | |

### Carburant

| **Consommation carburant** | **Prix du gazole** |
|---|---|
| ![Consommation carburant](images/rapports/consommation-carburant.png) | ![Prix du gazole](images/rapports/prix-du-gazole.png) |

### QHSE

| **Tableau de bord QHSE** | **Infractions RSE** |
|---|---|
| ![Tableau de bord QHSE](images/rapports/tableau-de-bord-qhse.png) | ![Infractions RSE](images/rapports/infractions-rse.png) |

| **Autoroutes interdites** | |
|---|---|
| ![Autoroutes interdites](images/rapports/autoroutes-interdites.png) | |

### Contrôle de gestion

| **Prestations à facturer** | **Rapprochement atelier et comptabilité** |
|---|---|
| ![Prestations à facturer](images/rapports/prestations-a-facturer.png) | ![Rapprochement atelier et comptabilité](images/rapports/rapprochement-atelier-et-comptabilite.png) |

| **Rentabilité** | |
|---|---|
| ![Rentabilité](images/rapports/rentabilite.png) | |

### Ressources humaines et données

| **Référentiel conducteurs** | **Qualité des données** |
|---|---|
| ![Référentiel conducteurs](images/rapports/referentiel-conducteurs.png) | ![Qualité des données](images/rapports/qualite-des-donnees.png) |

## Déploiement

Le dépôt est prêt pour un déploiement « as code » avec [fabric-cicd](https://github.com/microsoft/fabric-cicd) :

| Fichier | Rôle |
|---|---|
| [`powerbi/deployer.py`](../powerbi/deployer.py) | publie le modèle et les rapports dans un espace de travail (principal de service ou `az login`), supprime ceux retirés du dépôt |
| [`powerbi/parameter.yml`](../powerbi/parameter.yml) | remplace le paramètre `DossierDonnees` par le partage de l'environnement (DEV / PROD) et les jetons des liens entre rapports par les identifiants publiés ; les rapports `byPath` sont rebranchés automatiquement |
| [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) | déclenchement manuel, choix DEV / PROD (environnement GitHub, approbation possible), rejoue pipeline + contrôles avant publication |

Après publication, rattacher les utilisateurs aux rôles **Exploitant** et **Direction** (paramètres de sécurité du modèle
dans le service, ou par API) et alimenter la table `Habilitation` avec leurs e-mails : fabric-cicd déploie les rôles,
pas leurs membres.

**Non exécuté** : il faut un tenant Fabric / Power BI, un espace de travail et un principal de service autorisé
(secrets `FABRIC_WORKSPACE_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`). En production, les Parquet
seraient servis par un partage lu par une passerelle de données — ou, plus simplement, le modèle lirait directement
l'entrepôt (SQL Server / Fabric Warehouse) qui remplacerait DuckDB : seule l'expression `DossierDonnees` et la source des
partitions changent, ni les mesures ni les rapports.

## Ouvrir le projet

1. `python run_all.py` puis `python powerbi/build_model.py` (génère les Parquet et le modèle) ;
2. ouvrir `powerbi/TransVal.pbip` (ou l'un des 23 `powerbi/<Rapport>.pbip`) dans Power BI Desktop ;
3. si le dépôt n'est pas au même emplacement : **Transformer les données → Paramètres → DossierDonnees** = chemin de
   `powerbi/donnees`, puis **Actualiser**.

Les visuels personnalisés (Chiclet Slicer, Timeline…) sont des visuels publics AppSource : Power BI Desktop les
télécharge à l'ouverture.

→ Suite : [6. Exploitation](06-exploitation.md)
