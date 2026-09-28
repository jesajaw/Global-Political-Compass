import json
import requests
import date

OLLAMA_URL = "http://localhost:11434/api/generate"


def evaluate_country(country_name, year):
    prompt = f"""
    Analyze the political situation in {country_name} for the full year {year}.

    Rate the country on two axes ranging from -100 to +100:
    - left_right: -100 (Left/Planned economy) to +100 (Right/Free market)
    - lib_auth: -100 (liberal/libertarian) to +100 (authoritarian/state control)

    Respond EXCLUSIVELY as valid JSON in the following format:
    {{
        "left_right": 0,
        "lib_auth": 0,
        "summary": "just a title or up to 4-5 words",
        "justification": {{
            "left_right": "a simple and short justification",
            "lib_auth": "a simple and short justification"
        }},
        "sources": ["at least one link / source where you got this information"]
    }}
    """

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "gemma4:31b",  # Oder llama3.3 / deepseek-r1
                "prompt": prompt,
                "format": "json",
                "stream": False,
            },
        )
        response.raise_for_status()

        raw_text = response.json().get("response", "{}")
        return json.loads(raw_text)

    except Exception as e:
        print(f"Fehler bei der Bewertung von {country_name}: {e}")
        return None


def save_evaluation(country_id, year, result_data):
    if not result_data:
        return

    country_id = str(country_id)
    year = str(year)
    n=1 # dynamic index reading -> if there is already a entry in eva for this country + date, n+1
    rubric_id = f"{date.today}{country_id}-{n}"
    try:
        with open("data/country_scores.json", "r") as f:
            scores = json.load(f)
    except FileNotFoundError:
        scores = {}

    if country_id not in scores:
        scores[country_id] = {}

    scores[country_id][year] = {
        "left_right": result_data.get("left_right", 0),
        "lib_auth": result_data.get("lib_auth", 0),
        "rubric_id": rubric_id,
    }

    with open("data/country_scores.json", "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2, ensure_ascii=False)

    try:
        with open("data/evaluations.json", "r") as f:
            evaluations = json.load(f)
    except FileNotFoundError:
        evaluations = {"evaluations": {}}

    evaluations["evaluations"][rubric_id] = {
        "country_id": country_id,
        "year": year,
        "summary": result_data.get("summary", ""),
        "justification": result_data.get("justification", {}),
        "sources": result_data.get("sources", []),
    }

    with open("data/evaluations.json", "w", encoding="utf-8") as f:
        json.dump(evaluations, f, indent=2, ensure_ascii=False)