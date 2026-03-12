import csv
import json
import os
import sys
from datetime import datetime

import requests

import sekrets
from centrala import Centrala
from my_llm import MyLLM
from agent_display import AgentDisplay

TASK_DIR = os.path.join("taskfiles", "task0102")
CSV_FILENAME = "people.csv"
LOCAL_CSV = os.path.join(TASK_DIR, CSV_FILENAME)
FINDHIM_FILENAME = "findhim_locations.json"
LOCAL_FINDHIM = os.path.join(TASK_DIR, FINDHIM_FILENAME)

sys.stdout.reconfigure(encoding="utf-8")

agent_display = AgentDisplay()
agent_display.set_actions([
    "Połączenie z LLM i z Centralą",
    "Pobranie danych osobowych",
    "Filtrowanie deterministyczne",
    "Kategoryzacja AI",
    "Praca niezależnego agenta",
    "Wysłanie wyniku do Centrali",
    "Wynik końcowy"
])
agent_display.next_action()
agent_display.message("Agent rozpoczyna pracę - łączenie...")
llm = MyLLM(api_key=sekrets.openrouter_key, local_llm=False, agent_display=agent_display)
#llm = MyLLM(local_llm_url=sekrets.local_llm, agent_display=agent_display)
centrala = Centrala(server_url=sekrets.centrala_url, api_key=sekrets.centrala_key)
agent_display.message("Agent połączony i gotowy do pracy.")

# Pobranie danych z Centrali
agent_display.next_action()
os.makedirs(TASK_DIR, exist_ok=True)
centrala.get_file(CSV_FILENAME, LOCAL_CSV)
with open(LOCAL_CSV, encoding="utf-8", newline="") as f:
    people = list(csv.DictReader(f))
centrala.get_file(FINDHIM_FILENAME, LOCAL_FINDHIM)
with open(LOCAL_FINDHIM, encoding="utf-8", newline="") as f:
    findhim_locations = json.load(f)
agent_display.message(f"Dane pobrane i wczytane do pamięci. ({len(people)} osób i {len(findhim_locations)} elektrowni)")

# CSV has following columns: name, surname, gender, birthDate, birthPlace, birthCountry, job

# get yyyy-mm-dd from today
TODAY = datetime.now().strftime("%Y-%m-%d")
MIN_BIRTH = f"1980-{datetime.now().strftime("%m-%d")}"  # 46 years before today
MAX_BIRTH = f"2006-{datetime.now().strftime("%m-%d")}"  # 20 years before today

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
        label=f"task0102 - sprawdzenie kategorii pracy",
        #model="openai/gpt-oss-120b",
        model="openai/gpt-4.1-mini",
        #reasoning_effort="medium"
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

# Funkcja zwracająca lokalizacje danej osoby
def get_location(name: str, surname: str) -> str:
    agent_display.message(f"Pobieranie lokalizacji dla {name} {surname}...")
    endpoint = f"{sekrets.centrala_url}api/location"
    payload = {
        "apikey": sekrets.centrala_key,
        "name": name,
        "surname": surname,
    }
    response = requests.post(endpoint, json=payload)
    response.raise_for_status()
    return response.json()

# Funkcja zwracająca poziom dostępu danej osoby
def access_level(name: str, surname: str, birthYear: int) -> int:
    agent_display.message(f"Pobieranie poziomu dostępu dla {name} {surname} ({birthYear})...")
    endpoint = f"{sekrets.centrala_url}api/accesslevel"
    payload = {
        "apikey": sekrets.centrala_key,
        "name": name,
        "surname": surname,
        "birthYear": birthYear,
    }
    response = requests.post(endpoint, json=payload)
    response.raise_for_status()
    return response.json()

# Tworzymy prompt dla AI i listę narzędzi
prompt = f"""
## Cel zadania

Celem zadania jest znalezienie osoby z listy, która przebywała w pobliżu którejkolwiek z elektrowni z listy.

## Lista osób

Poniżej znajduje się lista osób, które potrzebujemy sprawdzić:
{json.dumps(answer_people, indent=4)}

## Lista elektrowni
Poniżej znajduje się lista elektrowni:
{json.dumps(findhim_locations, indent=4)}

## Współrzędne znanych miast
Poniżej znajduje się lista współrzędnych geograficznych niektórych miast:
- Zabrze — 50.303, 18.778
- Piotrków Trybunalski — 51.411, 19.686
- Grudziądz — 53.484, 18.754
- Tczew — 54.092, 18.778
- Radom — 51.403, 21.147
- Chełmno — 53.349, 18.425
- Żarnowiec — 54.787, 18.088

## Przebieg zadania

Dla każdej osoby z listy sprawdź jej lokalizację korzystając z narzędzia. Musisz wykonać to dla każdej osoby z listy.
Następnie zidentyfiuj jedną osobę, która przebywała najbliżej jednej z elektrowni.
Dla tej osoby stwierdź jej poziom dostępu do elektrowni korzystając z narzędzia.

## Rezultat zadania
Kiedy już znajdziesz osobę, która przebywała najbliżej elektrowni, zwróć jej dane w formacie JSON zawierającym:
- name - imię
- surname - nazwisko
- accessLevel - poziom dostępu
- powerPlant - kod elektrowni

(zwróć tylko JSON, bez dodatkowych informacji)
"""

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_location",
            "description": "Zwraca ostatnią znaną lokalizację danej osoby na podstawie imienia i nazwiska.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Imię osoby",
                    },
                    "surname": {
                        "type": "string",
                        "description": "Nazwisko osoby",
                    },
                },
                "required": ["name", "surname"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "access_level",
            "description": "Zwraca poziom dostępu danej osoby do elektrowni na podstawie imienia, nazwiska i roku urodzenia.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Imię osoby",
                    },
                    "surname": {
                        "type": "string",
                        "description": "Nazwisko osoby",
                    },
                    "birthYear": {
                        "type": "integer",
                        "description": "Rok urodzenia osoby (np. 1990)",
                    },
                },
                "required": ["name", "surname", "birthYear"],
                "additionalProperties": False,
            },
        },
    },
]

available_functions = {
    "get_location": get_location,
    "access_level": access_level,
}

messages = [
    {"role": "system", "content": prompt},
]

# Praca niezależnego agenta
agent_display.next_action()
for i in range(1,20):
    agent_display.message(f"Praca niezależnego agenta - krok {i}...")
    result = llm.chat(
        messages=messages,
        tools=tools,
        label=f"task0102 - praca niezależnego agenta",
        #model="openai/gpt-oss-120b",
        #model="openai/gpt-4.1-mini",
        model="openai/gpt-5",
        #reasoning_effort="medium"
    )

    if isinstance(result, dict) and result.get("tool_calls"):
        messages.append(result)
        for tool_call in result["tool_calls"]:
            fn_name = tool_call["function"]["name"]
            fn_args = json.loads(tool_call["function"]["arguments"])
            agent_display.message(f"  -> Wywołanie: {fn_name}({fn_args})")

            fn = available_functions[fn_name]
            fn_result = fn(**fn_args)
            agent_display.message(f"  <- Wynik: {fn_result}")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(fn_result, ensure_ascii=False),
            })
    else:
        final_answer = result if isinstance(result, str) else result.get("content", "")
        break

# Wysłanie wyniku do Centrali
final_answer = json.loads(final_answer)
agent_display.message(f"Agent zakończył pracę, wysyłanie wyniku do Centrali...")
agent_display.next_action()
response = centrala.send_result("findhim", final_answer)

# Wynik końcowy
agent_display.next_action()
agent_display.message(f"Odpowiedź centrali: {response.status_code}")
agent_display.message(response.text)

agent_display.log(f"Agent zakończył pracę. Wykonano {llm.get_session_stats()['executions']} zapytań., łącznie wyniosło to {llm.get_session_stats()['total_price']} USD. (tokeny: {llm.get_session_stats()['total_input_tokens']} input, {llm.get_session_stats()['total_output_tokens']} output)")