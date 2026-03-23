import os
import sys
from pprint import pp
import json
import time

import sekrets
from centrala import Centrala
from my_llm import MyLLM
from agent_display import AgentDisplay
from my_functions import get_picture

DEBUG = True

sys.stdout.reconfigure(encoding="utf-8")

if not DEBUG:
    agent_display = AgentDisplay()
    agent_display.set_actions([
        "Agent się łączy",
        "Pętla główna",
        "Wskazanie rozwiązania"
    ])

prompt_analiza = """
## Explanation

Attached you have a picture showing a connections diagram.
The main part of the picture is a 3 by 3 matrix of adjacent squares = 9 squares.
Make sure you see properly where the 3x3 matrix is - it's the central part of the image. We will be analyzing this matrix of squares.
We will label each of the squares in "AxB" format, where A is the row number and B is the column number. Then the 9 squares can be represented like:
1x1 | 1x2 | 1x3
2x1 | 2x2 | 2x3
3x1 | 3x2 | 3x3

So, as some examples, upper-left square is 1x1, upper-right is 1x3, etc.

## Task

Inside each small square there are lines connecting the middle of the square to 4 sides (UP, RIGHT, DOWN, LEFT). Your task is to write how the connections go inside each square.
In the end, write each label in new line (9 lines in total) followed by the list of connected sides.
"""

master_prompt = """
You are an agent, whose task is to work on the picture to transform the connections to match those on the "desired" picture.
The picture consists of 9 fields forming a square (3 by 3), labeled as:
1x1 | 1x2 | 1x3
2x1 | 2x2 | 2x3
3x1 | 3x2 | 3x3
(e.g. 1x1 is the upper left element, 1x3 is the upper right element, etc.)
Each element on the picture has a connector that connects 2 or 3 sides (UP, RIGHT, DOWN, LEFT).
You can check the desired picture or the current picture (one you are working in) using the tool.
Your task is to spot the elements that need to be rotated (only clockwise rotation is allowed, you can rotate one element multiple times) and run the tool to do it.
Rotation of an element rotates it 90 degrees clockwise. So element having "UP, RIGHT" connector, after rotation, would become "RIGHT, DOWN" one.
(the order in which the directions are written - doesn't matter)
What you should do:
1. Check the connections on the "desired" picture
2. Check the current status of your working picture.
3. Run the rotation tool for all elements that are mismatched, so they match the desired picture.
4. Check the current status again (if it matches the desired one). If not matching - go back to point 3 and rotate again.

In the end - inform that the job was done and that all elements on current picture match the desired picture.
"""

def local_picture_analysis(url: str) -> str:
    pp("Pobieram obrazek") if DEBUG else agent_display.log("Pobieram obrazek")
    image = get_picture(url)
    pp("Analizuję obrazek") if DEBUG else agent_display.log("Analizuję obrazek")
    response = llm_local.chat(
        [
            {"role": "user", "content": [
                {"type": "text", "text": prompt_analiza},
                image
            ]}
        ],
        model = "qwen/qwen3-vl-32b",
        label = "task0202-obraz",
    )
    return response

def picture_analysis(url: str) -> str:
    pp("Pobieram obrazek") if DEBUG else agent_display.log("Pobieram obrazek")
    image = get_picture(url)
    pp("Analizuję obrazek") if DEBUG else agent_display.log("Analizuję obrazek")
    response = llm.chat(
        [
            {"role": "user", "content": [
                {"type": "text", "text": prompt_analiza},
                image
            ]}
        ],
        # model = "openai/gpt-5.4",
        # model = "anthropic/claude-sonnet-4.6",
        # model = "anthropic/claude-opus-4.6",
        model = "google/gemini-3-flash-preview",
        label = "task0202-obraz",
    )
    return response

def check_picture(picture: str) -> str:
    url = {}
    url['desired'] = f"{sekrets.centrala_url}i/solved_electricity.png"
    url['current'] = f"{sekrets.centrala_url}data/{sekrets.centrala_key}/electricity.png"
    analiza = picture_analysis(url[picture]) if picture in ['desired','current'] else {"content": "ERROR: bad parameter; picture should be either 'desired' or 'current'."}
    return analiza['content']

def rotate_element(element: str) -> str:
    response = centrala.send_result("electricity", {"rotate": element})
    return str(response.json())

check_picture_tool = {
    "type": "function",
    "function": {
        "name": "check_picture",
        "description": (
            "Analyzes a picture from the electricity connections puzzle and returns "
            "a description of what connections are present in each of the 9 squares "
            "of the 3x3 matrix. Use 'desired' to analyze the target/reference image "
            "showing the correct solution, or 'current' to analyze the working image "
            "that is being modified."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "picture": {
                    "type": "string",
                    "enum": ["desired", "current"],
                    "description": (
                        "'desired' - analyzes the target/reference image (solved_electricity.png), "
                        "'current' - analyzes the current working image (electricity.png)"
                    )
                }
            },
            "required": ["picture"]
        }
    }
}

rotate_element_tool = {
    "type": "function",
    "function": {
        "name": "rotate_element",
        "description": (
            "Rotates a single square element of the 3x3 electricity connections puzzle "
            "90 degrees clockwise. Use this to fix mismatched connections between the "
            "current image and the desired (target) image."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "element": {
                    "type": "string",
                    "enum": [
                        "1x1", "1x2", "1x3",
                        "2x1", "2x2", "2x3",
                        "3x1", "3x2", "3x3"
                    ],
                    "description": "Label of the square to rotate, in 'RowxCol' format (e.g. '2x3')"
                }
            },
            "required": ["element"]
        }
    }
}

tools = [check_picture_tool, rotate_element_tool]
available_functions = {
    "check_picture": check_picture,
    "rotate_element": rotate_element,
}

# Krok 1 - połączenie
if not DEBUG: agent_display.next_action()
llm = MyLLM(api_key=sekrets.openrouter_key, local_llm=False, agent_display=None if DEBUG else agent_display)
llm_local = MyLLM(local_llm_url=sekrets.local_llm, agent_display=None if DEBUG else agent_display)
centrala = Centrala(server_url=sekrets.centrala_url, api_key=sekrets.centrala_key)
centrala.get_file("electricity.png?reset=1", None)  # Reset obrazka
pp("Agent gotowy do pracy.") if DEBUG else agent_display.message("Agent gotowy do pracy.")

# Krok 2 - główna pętla agenta
if not DEBUG: agent_display.next_action()
messages = [{"role": "system", "content": master_prompt}]
for i in range(0,30):
    pp("Zaczynamy kolejny obrót agenta!") if DEBUG else agent_display.message("Zaczynamy kolejny obrót agenta!")
    result = llm.chat(
        messages=messages,
        tools=tools,
        label=f"task0202-agent",
        model="openai/gpt-5.4",
    )
    if isinstance(result, dict) and result.get("tool_calls"):
        messages.append(result)
        for tool_call in result["tool_calls"]:
            time.sleep(1)
            fn_name = tool_call["function"]["name"]
            fn_args = json.loads(tool_call["function"]["arguments"])
            pp(f"  -> Wywołanie: {fn_name} ({fn_args})") if DEBUG else agent_display.message(f"  -> Wywołanie: {fn_name} ({fn_args})")

            fn = available_functions[fn_name]
            fn_result = fn(**fn_args)
            # agent_display.message(f"  <- Wynik: {json.dumps(fn_result, ensure_ascii=False)[0:60]}")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(fn_result, ensure_ascii=False),
            })

            flagi = centrala.get_flags(fn_result)
            if flagi:
                pp("Znaleziono flagę!!") if DEBUG else agent_display.message("Znaleziono flagę!!")
                pp(flagi) if DEBUG else agent_display.message(flagi)
    else:
        final_answer = result if isinstance(result, str) else result.get("content", "")
        break

if not DEBUG: agent_display.next_action()
pp("Agent zakończył pracę!") if DEBUG else agent_display.message("Agent zakończył pracę!")

pp (messages, indent=4, width=200)
