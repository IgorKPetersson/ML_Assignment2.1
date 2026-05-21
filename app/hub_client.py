import time

import requests


class HubClient:
    def __init__(self, hub_url, password, agent_name, min_request_interval=1.1):
        self.hub_url = hub_url
        self.password = password
        self.agent_name = agent_name
        self.min_request_interval = min_request_interval
        self.last_request_at = 0.0

    def _rate_limit(self):
        elapsed = time.monotonic() - self.last_request_at
        wait_time = self.min_request_interval - elapsed
        if wait_time > 0:
            time.sleep(wait_time)
        self.last_request_at = time.monotonic()

    def fetch_messages(self, since):
        self._rate_limit()
        response = requests.get(
            f"{self.hub_url}/api/messages",
            params={"since": since, "password": self.password},
            timeout=15,
        )
        response.raise_for_status()
        return response.json().get("messages", [])

    def post_message(self, content):
        self._rate_limit()
        response = requests.post(
            f"{self.hub_url}/api/message",
            json={
                "agent_name": self.agent_name,
                "content": content[:4096],
                "password": self.password,
            },
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def fetch_stats(self):
        self._rate_limit()
        response = requests.get(
            f"{self.hub_url}/api/stats",
            params={"password": self.password},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()
