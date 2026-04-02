import os
import re
import sys
import csv
from pprint import pp

import sekrets
from centrala import Centrala
from my_llm import MyLLM
from agent_display import AgentDisplay

TASK_DIR = os.path.join("taskfiles", "task0203")
LOG_FILENAME = "failure.log"
LOCAL_LOG = os.path.join(TASK_DIR, LOG_FILENAME)
# model = "openai/gpt-oss-120b"
model = "openai/gpt-5.4-mini"

sys.stdout.reconfigure(encoding="utf-8")

agent_display = AgentDisplay()
agent_display.set_actions([
    "Pobierz plik z logami",
    "Wyczyść logi",
    "Agent pracuje",
    "Pokaż odpowiedź"
])

# Krok 1 - pobranie pliku z logami
agent_display.next_action()
llm = MyLLM(api_key=sekrets.openrouter_key, local_llm=False, agent_display=agent_display)
# llm_local = MyLLM(local_llm_url=sekrets.local_llm, agent_display=agent_display)
centrala = Centrala(server_url=sekrets.centrala_url, api_key=sekrets.centrala_key)

os.makedirs(TASK_DIR, exist_ok=True)
centrala.get_file(LOG_FILENAME, LOCAL_LOG)
with open(LOCAL_LOG, encoding="utf-8", newline="") as f:
    # log = the contents of the file, full text
    log_lines = f.readlines()
agent_display.message(f"Logi pobrane. Liczba linii: {len(log_lines)}")
agent_display.message("Rozpoczynamy pracę - agent pracuje...")

# Krok 2 - wyczyszczenie logów
agent_display.next_action()

seen_texts = set()
deduplicated = []
for line in log_lines:
    text_outside_brackets = re.sub(r'\[.*?\]', '', line).strip()
    if text_outside_brackets not in seen_texts:
        seen_texts.add(text_outside_brackets)
        deduplicated.append(line)

agent_display.message(f"Usunięto {len(log_lines) - len(deduplicated)} duplikatów. Pozostało {len(deduplicated)} linii.")
# log_lines = deduplicated

# Krok 3 - pętla pracy agenta
agent_display.next_action()

prompt = f"""
Below you see a log file contents from a power plant. The log file is very large.
Your task is to create an extract from the log file, that contains only the lines that are most relevant to debugging the power plant problem.
Your output should be a list of lines, each line being a string from the log file. Don't add any other lines to the output.
The output can contain **maximum 30 lines** from the logs, no more!

## Where to start

When preparing first extract, analyze the log file contents and rank them based on severity.
If the same log is repeated multiple times (with different timestamps), consider it only once, when it first happened.
Check if the logs in the lines you prepared don't repeat themselves (with different timestamps). If they do - remove the duplicate lines.

## Output format

The output should be just a log text (with extracted logs), one log in one line. All lines separated by '\n'.
There is no JSON or other formatting - just a plain text.

## Evaluation

After you send the output, the engineers evaluating the logs will respond with the information if any other lines are necessary. In such case - prepare new extract, concentrating on the feedback from all the messages you received.
The engineers will also provide a list of the most important elements or parts, which should be included in the logs. Use this list (from all feedback received) to prepare the new extract.
The element names or part IDs can be recognized by being written with CAPITAL LETTERS.
If the feedback relates to lacking logs about a specific element or part ID - add more logs related to that part or ID.
For example - if system says that more logs are needed for ELEMENT_X - add more logs related to ELEMENT_X.
If system needs to know what happened to FIRMWARE - add more logs related to FIRMWARE.
If still more logs are needed for a specific module - also look for the logs related to that module with lower priorities, and include them.

## No repetitions!

When you're adding a log line to a text extract, ensure that it's not a repetition of a previous line. If a similar line is already in the extract (same log with different timestamp) - don't add it again.

## What to do

If you already have some feedback:
- think about the list of items that need to be included (looking at the full feedback history from the conversation)
- prepate the extract, containing most relevant (to you) and UNIQUE (not repeated) logs related to the items in the list.
- use your judgement to add more logs that may be related.
- the total length of the extract should be maximum 30 lines.

## Log file contents:

{log_lines}
"""

messages = [
    {"role": "system", "content": prompt}
]

feedback = "Feedback history:\n\n"

for i in range(1, 10):
    agent_display.message(f"Praca agenta - krok {i}...")
    # result = llm.chat(
    #     messages=messages,
    #     label=f"task0203-agent",
    #     model=model,
    #     #reasoning={"enabled": True},
    #     #reasoning_effort="medium"
    # )
    # answer = result.get("content", "") if isinstance(result, dict) else str(result)
    if i == 1:
        answer = "x\n"*34 + "x y"
    elif i == 2:
        answer = "x\n"*37 + "x y"
    elif i == 3:
        answer = "x\n"*32 + "x"
    elif i == 4:
        answer = "x\n"*35 + "x"
    agent_display.log(f"Odpowiedź agenta: {answer}")
    if answer.count('\n') > 100:
        agent_display.message("Odpowiedź jest za długa, wychodzę...")
        sys.exit(1)
    messages.append({"role": "assistant", "content": answer})
    response = centrala.send_result("failure", {"logs": answer})
    agent_display.message(f"Odpowiedź centrali: {response.status_code}")
    agent_display.message(response.text)
    response_json = response.json()
    message = response_json['message']
    flagi = centrala.get_flags(response_json)
    if flagi:
        agent_display.message("Znaleziono flagę!!")
        agent_display.message(flagi)
        break
    feedback += f"{message}\n"
    messages.append({"role": "user", "content": feedback})

# Krok 4 - kończenie pracy agenta
agent_display.next_action()
llm.final_stats()
pp(messages, indent=4, width=200)
