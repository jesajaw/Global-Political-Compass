import json
import os
import sys
from datetime import date
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from openai import OpenAI

# Lade Umgebungsvariablen aus .env
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ Fehler: OPENAI_API_KEY ist nicht gesetzt. Bitte erstelle eine .env Datei.")
    sys.exit(1)

client = OpenAI(api_key=api_key)

# Pydantic Schemas für Structured Outputs
class Scores(BaseModel):
    economic_left_right: float = Field(
        description="Wert von -10.0 (Sozialismus/Planwirtschaft) bis +10.0 (Freier Markt/Kapitalismus)"
    )
    social_libertarian_authoritarian: float = Field(
        description="Wert von -10.0 (Maximal Libertär/Bürgerrechte) bis +10.0 (Maximal Autoritär/Überwachung/Zensur)"
    )

class CountryProfile(BaseModel):
    country: str
    last_updated: str = Field(description="Datum der Analyse (YYYY-MM-DD)")
    scores: Scores
    economic_justification: str = Field(description="Begründung der Wirtschafts-Punktzahl.")
    social_justification: str = Field(description="Begründung der Gesellschafts-Punktzahl.")
    key_factors: List[str] = Field(description="3-5 prägende Merkmale oder aktuelle Entwicklungen.")

SYSTEM_PROMPT = f"""
Du bist ein wissenschaftlicher, neutraler Politikanalyst.
Deine Aufgabe ist es, das politische und wirtschaftliche System eines Landes anhand des 2D-Kompass-Modells zu bewerten.
Aktuelles Datum für zeitliche Einordnung: {date.today().isoformat()}

BEWERTUNGSMASSSTÄBE:
1. Wirtschaft (economic_left_right):
   - -10.0: Reine Planwirtschaft, Verstaatlichung, hohe Regulierungen.
   -   0.0: Ausgewogene Soziale Marktwirtschaft.
   - +10.0: Deregulierter freier Markt, minimale Staatsquote, Anarcho-Kapitalismus.

2. Gesellschaft (social_libertarian_authoritarian):
   - -10.0: Maximal libertär, starke Bürgerrechte, freie Presse, minimale staatliche Einmischung.
   -   0.0: Moderate Rechtsstaatlichkeit / Standard-Demokratie.
   - +10.0: Totalitär, Massenüberwachung, Zensur, Autokratie.

Nutze für die Bewertung dein aktuelles Wissen über Gesetzgebung, Wirtschaftsindikatoren und Berichte internationaler Organisationen.
"""

def analyze_country(country_name: str, output_file: str = "countries_data.json"):
    print(f"🔍 Analysiere {country_name}...")

    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Erstelle eine politische Profil-Analyse für: {country_name}"}
            ],
            response_format=CountryProfile,
        )

        data = completion.choices[0].message.parsed.model_dump()

        database = {}
        if os.path.exists(output_file):
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    database = json.load(f)
            except json.JSONDecodeError:
                database = {}

        database[country_name] = data

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(database, f, ensure_ascii=False, indent=2)

        print(f"✅ Analyse für '{country_name}' gespeichert!")

    except Exception as e:
        print(f"❌ Fehler bei der Verarbeitung: {e}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "Argentinien"
    analyze_country(target)