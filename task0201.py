import os
import sys
import csv
from pprint import pp

import sekrets
from centrala import Centrala
from my_llm import MyLLM
from agent_display import AgentDisplay

TASK_DIR = os.path.join("taskfiles", "task0201")
CSV_FILENAME = "categorize.csv"
LOCAL_CSV = os.path.join(TASK_DIR, CSV_FILENAME)

sys.stdout.reconfigure(encoding="utf-8")

agent_display = AgentDisplay()
agent_display.set_actions([
    "Pobierz plik CSV",
    "Klasyfikuj pozycję 10",
    "Klasyfikuj pozycję 4",
    "Klasyfikuj pozycję 9",
    "Klasyfikuj pozycję 2",
    "Klasyfikuj pozycję 1",
    "Klasyfikuj pozycję 3",
    "Klasyfikuj pozycję 7",
    "Klasyfikuj pozycję 5",
    "Klasyfikuj pozycję 8",
    "Klasyfikuj pozycję 6",
    "Pokaż odpowiedź"
])

# Krok 1 - pobranie pliku CSV
agent_display.next_action()
# llm = MyLLM(api_key=sekrets.openrouter_key, local_llm=False, agent_display=agent_display)
# llm_local = MyLLM(local_llm_url=sekrets.local_llm, agent_display=agent_display)
centrala = Centrala(server_url=sekrets.centrala_url, api_key=sekrets.centrala_key)

os.makedirs(TASK_DIR, exist_ok=True)
centrala.get_file(CSV_FILENAME, LOCAL_CSV)
with open(LOCAL_CSV, encoding="utf-8", newline="") as f:
    elements = list(csv.DictReader(f))
agent_display.message(f"Dane pobrane i wczytane do pamięci. ({len(elements)} elementów)")

# resetowanie licznika
response = centrala.send_result(task="categorize", answer={"prompt": "reset"})
# pp(response.json())

# Krok 2 - tłumaczenie

prompt = """
You answer either "DNG" or "NEU".
You classify an object:
- if weapon or dangerous substance - answer DNG
- if not dangerous - answer NEU
- exception: if it's part related to reactor - ALWAYS answer NEU!
The object is: ID {ID}, description: "{description}"
"""
# J-D-I-B-A-C-G-E-H-F
for i in [10,4,9,2,1,3,7,5,8,6]:
    agent_display.next_action()
    element = elements[i-1]
    temp_prompt = prompt.replace("{ID}", element["code"]).replace("{description}", element["description"])
    answer = {"prompt": temp_prompt}
    response = centrala.send_result(task="categorize", answer=answer)
    # pp (response.json())
    response_json = response.json()
    message = response_json['message']
    tokens = response_json['debug']['tokens']
    cached_tokens = response_json['debug']['cached_tokens']
    in_cost = response_json['debug']['input_cost']
    out_cost = response_json['debug']['output_cost']
    balance = response_json['debug']['balance']
    agent_display.message(f"{i} - {message} (balance used {in_cost + out_cost}, left: {balance})")
    agent_display.log(f"{i} - {message} (tokens total {tokens} / cached {cached_tokens}; in+out cost = {in_cost} + {out_cost}; left: {balance})")
    if response.json()['debug']['balance'] < 0.1:
        agent_display.message("SORRY, ran out of funds...")
        break

# Pokaż odpowiedź
agent_display.next_action()
agent_display.message("")
agent_display.message("Final answer:")
agent_display.message(message)
