"""Constantes partagées par le générateur, l'ingestion, le replica legacy et les tests."""
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "data" / "sources"          # ce que Power BI lit en direct (état des systèmes au jour J)
WAREHOUSE = ROOT / "data" / "warehouse.duckdb"

START = date(2023, 1, 1)
# "Aujourd'hui" figé : remplace les TODAY() dispersés dans les mesures -> résultats reproductibles, rapports
# et tests calés sur la même date de référence.
AS_OF = date(2026, 9, 30)

# Trois imports simulés : chargement initial, puis deux deltas (avec recouvrement et corrections).
CUTOFFS = [date(AS_OF.year, 3, 31), AS_OF.replace(day=1) - timedelta(1), AS_OF]
