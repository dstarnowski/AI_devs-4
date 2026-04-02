import json
import os
import re
import sys
import csv
from pprint import pp
from datetime import datetime

import sekrets
from centrala import Centrala
from my_llm import MyLLM
from agent_display import AgentDisplay
from my_functions import get_picture

# model = "openai/gpt-oss-120b"
model = "openai/gpt-5.4-mini"

sys.stdout.reconfigure(encoding="utf-8")

agent_display = AgentDisplay()
agent_display.set_actions([
    "Agent pracuje",
    "Pokaż odpowiedź"
])

# Inicjalizacja
llm = MyLLM(api_key=sekrets.openrouter_key, local_llm=False, agent_display=agent_display)
# llm_local = MyLLM(local_llm_url=sekrets.local_llm, agent_display=agent_display)
centrala = Centrala(server_url=sekrets.centrala_url, api_key=sekrets.centrala_key)

# Narzędzie dla agenta - pobierz plik
get_file_tool = {
    "type": "function",
    "function": {
        "name": "get_file",
        "description": "Get a file from the server",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "The name of the file to get"},
            },
            "required": ["filename"],
            "additionalProperties": False
        }
    }
}

prompt_picture = """
Otrzymujesz plik graficzny. Twoim zadaniem jest zawrzeć jak najwięcej informacji o tym, co widzisz na obrazku.
Jeżeli widzisz tekst, to przepisz go. Staraj się zachować oryginalny kształt tekstu i strukturę (np. tabele, umiejscowienie, itp.)
Jeżeli widzisz obiekty (symbole, kształty, itp.), to opisz je.
Jeżeli obrazek pokazuje jakiś schemat, to opisz go, starając się zawrzeć jak najwięcej informacji o tym, co widzisz.
Generalnie - opisz wszystko tak szczegółowo i dokładnie, aby przekazać jak najwięcej treści z obrazka osobie niewidomej.
"""

def get_file(filename: str) -> str:
    agent_display.message(f"... pobieranie pliku: {filename}")
    if filename.endswith(".md") or filename.endswith(".txt"):
        content = centrala.get_file_any(f"dane/doc/{filename}", None)
        return {
            "filename": filename,
            "file_contents": content.decode("utf-8")
        }
    if filename.endswith(".png") or filename.endswith(".jpg") or filename.endswith(".jpeg"):
        image = get_picture(f"{sekrets.centrala_url}dane/doc/{filename}")
        response = llm.chat(
            [
                {"role": "user", "content": [
                    {"type": "text", "text": prompt_picture},
                    image
                ]}
            ],
            model = 'google/gemini-3-flash-preview',
            label = "task0104-obraz",
        )
        return {
            "filename": filename,
            "image_file_description": response['content']
        }
    return {"error": f"Unsupported file type: {filename}"}

tools = [get_file_tool]
available_functions = {
    "get_file": get_file
}

# Pętla pracy agenta
agent_display.next_action()

prompt = f"""
# Zadanie

Musisz wygenerować poprawnie wypełnioną deklarację transportu w Systemie Przesyłek Konduktorskich. W takim dokumencie niestety nie można wpisać, czego się tylko chce, ponieważ jest on weryfikowany zarówno przez ludzi, jak i przez automaty.

Jako że dysponujemy zerowym budżetem, musisz tak przygotować dane, aby była to przesyłka darmowa lub opłacana przez sam "System". Transport będziemy realizować z Gdańska do Żarnowca.

Udało nam się zdobyć numer nadawcy (450202122). Sama paczka waży mniej więcej 2,8 tony. Nie dodawaj proszę żadnych uwag specjalnych.

Co do opisu zawartości, możesz wprost napisać, co to jest ("zabawki pluszowe"). Nie przejmuj się, że trasa, którą chcemy jechać jest zamknięta. Zajmiemy się tym później.

Dokumentacja przesyłek znajduje się w pliku "index.md". Plik ten odwołuje się również do innych plików. Zastanów się, które z nich są potrzebne i pobierz je.

Nie udzielaj odpowiedzi, dopóki nie będziesz miał wszystkich potrzebnych plików (wszystkie polecenia "include" zawarte w dokumentach).

Odpowiedzią powinna być gotowa deklaracja - cały tekst, sformatowany dokładnie jak wzór z pobranej dokumentacji (upewnij się, że pobrałeś całą, z załącznikami!).

Dane niezbędne do wyepełnienia deklaracji:

Nadawca (identyfikator): 450202122
Punkt nadawczy: Gdańsk
Punkt docelowy: Żarnowiec
Waga: 2,8 tony (2800 kg)
Budżet: 0 PP (przesyłka ma być darmowa lub finansowana przez System)
Zawartość: zabawki pluszowe
Uwagi specjalne: brak - nie dodawaj żadnych uwag

Do dyspozycji masz narzędzie "get_file", które pozwala na pobranie pliku z dokumentacji. Możesz go użyć dla każdego z brakujących plików, aby pobrać jego zawartość. Kiedy będziesz miał już wszystkie potrzebne pliki, to generujesz w odpowiedzi gotową deklarację.

Jeżeli plik, który pobrałeś, odwołuje się do innych plików (np. ma "include"), to pobierz również te pliki, KONIECZNIE!. Użyj narzędzia "get_file" dla każdego z nich.

Powodzenia!

(Aktualna data i godzina: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
"""

messages = [
    {"role": "system", "content": prompt}
]

for i in range(1, 20):
    agent_display.message(f"Praca agenta - krok {i}...")
    result = llm.chat(
        messages=messages,
        label=f"task0104-agent",
        model=model,
        tools=tools,
        #reasoning={"enabled": True},
        #reasoning_effort="medium"
    )
    messages.append(result)
    if "tool_calls" in result:
        for tool_call in result["tool_calls"]:
            fn_name = tool_call["function"]["name"]
            fn_args = json.loads(tool_call["function"]["arguments"])
            fn = available_functions[fn_name]
            fn_result = fn(**fn_args)
            messages.append({"role": "tool", "tool_call_id": tool_call["id"], "content": json.dumps(fn_result, ensure_ascii=False)})
    else:
        break

# Krok 4 - kończenie pracy agenta
agent_display.next_action()
llm.final_stats()
answer = result['content']
answer = answer.replace("zabawki pluszowe", "kasety z paliwem do reaktora")
agent_display.message(f"Odpowiedź: {answer}")

pp (messages, indent=4, width=200)

response = centrala.send_result(task="sendit", answer=json.dumps({"declaration": answer}, ensure_ascii=False))

response_json = response.json()
pp (response_json, indent=4, width=200)
flagi = centrala.get_flags(response_json)
if flagi:
    agent_display.message("Znaleziono flagę!!")
    agent_display.message(flagi)
