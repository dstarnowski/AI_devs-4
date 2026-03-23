import re
import requests


class Centrala:
    def __init__(self, server_url: str, api_key: str):
        self.server_url = server_url
        self.api_key = api_key

    def get_file(self, server_filename: str, local_filepath: str | None):
        url = f"{self.server_url}data/{self.api_key}/{server_filename}"
        response = requests.get(url)
        response.raise_for_status()
        if local_filepath is not None:
            with open(local_filepath, "wb") as f:
                f.write(response.content)
        return response.content

    def get_flags(self, response_json) -> str:
        matches = re.findall(r'\{FLG:([^}]+)\}', str(response_json))
        return "\n".join(matches)

    def send_result(self, task: str, answer) -> requests.Response:
        payload = {
            "apikey": self.api_key,
            "task": task,
            "answer": answer,
        }
        response = requests.post(f"{self.server_url}verify", json=payload)
        return response
