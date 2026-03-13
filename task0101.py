import csv
import json
import os
import sys
from datetime import datetime

import sekrets
from centrala import Centrala
from my_llm import MyLLM
from agent_display import AgentDisplay

TASK_DIR = os.path.join("taskfiles", "task0101")
CSV_FILENAME = "people.csv"
LOCAL_CSV = os.path.join(TASK_DIR, CSV_FILENAME)

sys.stdout.reconfigure(encoding="utf-8")

agent_display = AgentDisplay()
agent_display.set_actions([
    "Połączenie z LLM i z Centralą",
    "Pobranie danych osobowych",
    "Filtrowanie deterministyczne",
    "Kategoryzacja AI",
    "Wysyłka danych do Centrali",
    "Wynik końcowy"
])
agent_display.next_action()
agent_display.message("Agent rozpoczyna pracę - łączenie...")
#llm = MyLLM(api_key=sekrets.openrouter_key, local_llm=False, agent_display=agent_display)
llm = MyLLM(local_llm_url=sekrets.local_llm, agent_display=agent_display)
centrala = Centrala(server_url=sekrets.centrala_url, api_key=sekrets.centrala_key)
agent_display.message("Agent połączony i gotowy do pracy.")

# Pobranie danych z Centrali
agent_display.next_action()
os.makedirs(TASK_DIR, exist_ok=True)
centrala.get_file(CSV_FILENAME, LOCAL_CSV)
with open(LOCAL_CSV, encoding="utf-8", newline="") as f:
    people = list(csv.DictReader(f))
agent_display.message(f"Dane pobrane i wczytane do pamięci. ({len(people)} osób)")

# CSV has following columns: name, surname, gender, birthDate, birthPlace, birthCountry, job

# get yyyy-mm-dd from today
TODAY = datetime.now().strftime("%Y-%m-%d")
MIN_BIRTH = f"1980-{datetime.now().strftime('%m-%d')}"  # 46 years before today
MAX_BIRTH = f"2006-{datetime.now().strftime('%m-%d')}"  # 20 years before today

# Filtrowanie deterministyczne
agent_display.next_action()
filtered = [
    p for p in people
    if p["birthPlace"] == "Grudziądz"
    and p["birthCountry"] == "Polska"
    and p["gender"] == "M"
    and MIN_BIRTH <= p["birthDate"] <= MAX_BIRTH
]

agent_display.message(f"Znaleziono {len(filtered)} pasujących osób.")

# Filtrowanie AI
agent_display.next_action()
prompt = """
Poniżej znajduje się opis jednej osoby.
Na podstawie tego opisu powinieneś stwierdzić, w której z kategorii pracy pracuje dana osoba.
Jest możliwe, że osoba pracuje w kilku kategoriach. W takim przypadku powinieneś wybrać wszystkie kategorie, do których pasuje praca danej osoby.
Jeżeli osoba pracuje w danej kategorii, ustaw dla niej wartość true, w przeciwnym wypadku ustaw wartość false.
W odpowiedzi powinieneś zwrócić JSON zawierający klucze o nazwach kategorii z wartościami true lub false.
"""

CATEGORY_KEYS = ["IT", "transport", "edukacja", "medycyna",
                 "praca z ludźmi", "praca z pojazdami", "praca fizyczna"]

response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "kategorie",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "IT":                  {"type": "boolean"},
                "transport":           {"type": "boolean"},
                "edukacja":            {"type": "boolean"},
                "medycyna":            {"type": "boolean"},
                "praca z ludźmi":      {"type": "boolean"},
                "praca z pojazdami":   {"type": "boolean"},
                "praca fizyczna":      {"type": "boolean"},
            },
            "required": CATEGORY_KEYS,
            "additionalProperties": False,
        },
    },
}

answer_people = []

print (f"Przetwarzanie osób...")

for i, person in enumerate(filtered, 1):

    result = llm.chat(
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": person["job"]},
        ],
        response_format=response_format,
        label=f"task0101 - sprawdzenie kategorii pracy",
        model="openai/gpt-oss-120b",
        #model="openai/gpt-4.1-mini",
        reasoning_effort="medium"
    )

    categories = json.loads(result['content'])
    tags = [key for key in CATEGORY_KEYS if categories.get(key)]

    if "transport" in tags:
        answer_people.append({
            "name": person["name"],
            "surname": person["surname"],
            "gender": person["gender"],
            "born": person["birthDate"][:4],
            "city": person["birthPlace"],
            "tags": tags,
        })

    agent_display.message(f"[{i}/{len(filtered)}] {person['name']} {person['surname']}: {tags}")

agent_display.message(f"\n--- Wyniki ({len(answer_people)} osób) ---")
for entry in answer_people:
    agent_display.message(f"  {entry['name']} {entry['surname']} ({entry['gender']}, {entry['born']}, {entry['city']}): {entry['tags']}")

# Wysyłka danych do centrali
agent_display.next_action()
agent_display.message("Wysyłanie wyników...")
response = centrala.send_result("people", answer_people)

# Wynik końcowy
agent_display.next_action()
agent_display.message(f"Odpowiedź centrali: {response.status_code}")
agent_display.message(response.text)
agent_display.message("Agent zakończył pracę.")

agent_display.log(response.text)
llm.final_stats()