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
    "Sprawdzenie lokalizacji",
    "Sprawdzenie poziomu dostępu"
])

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

agent_display.next_action()
#result = get_location("Martin","Handford")
#agent_display.message(f"Location: {result}")

agent_display.next_action()
result = access_level("Martin","Handford",1987)
agent_display.message(f"Access level: {result}")

agent_display.next_action()
agent_display.log("Skrypt zakończył pracę.")