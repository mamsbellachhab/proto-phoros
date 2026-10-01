import json
import os

from openai import OpenAI

from tools import TOOL_SCHEMAS, call_tool

BASE_URL = os.environ.get("ECHO_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("ECHO_API_KEY")
MODEL = os.environ.get("ECHO_MODEL", "gemini-2.5-flash")
MAX_TOOL_ROUNDS = 6

SYSTEM_PROMPT = """You are Echo, a logistics copilot for PROTO-PHOROS, a military supply and inventory system. You answer questions about stock levels, vehicles, weapons, pending supply requests, demand forecasts and flagged anomalies, and you can approve, edit or reject pending requirement lines and raise new ones -- but only by calling the tools you are given. Never invent numbers, IDs or statuses; if you need data, call a tool for it. You only ever see and act on data within the acting user's own unit scope -- the backend enforces this, not you, so if a tool call comes back with an error, say so plainly rather than guessing why.

Keep answers short and concrete: numbers, names, statuses. When you take an action, confirm exactly what happened, including any ID returned."""


def _client():
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set.")
    return OpenAI(api_key=API_KEY, base_url=BASE_URL)


class EchoSession:
    def __init__(self, username):
        self.username = username
        self.client = _client()
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def ask(self, user_message):
        self.messages.append({"role": "user", "content": user_message})

        for _ in range(MAX_TOOL_ROUNDS):
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=self.messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
            )
            choice = response.choices[0].message
            self.messages.append(choice.model_dump(exclude_none=True))

            if not choice.tool_calls:
                return choice.content

            for tool_call in choice.tool_calls:
                name = tool_call.function.name
                try:
                    arguments = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    arguments = {}
                result = call_tool(name, arguments, self.username)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, default=str),
                })

        return "(stopped after too many tool calls in a row)"