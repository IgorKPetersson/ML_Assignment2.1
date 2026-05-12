from openai import OpenAI
from dotenv import load_dotenv
import os

from prompts import SYSTEM_PROMPT
from parser import parse_response
from shell_tools import execute_bash

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = os.getenv("MODEL")

def run_agent(user_task):

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": user_task
        }
    ]

    for step in range(5):

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages
        )

        reply = response.choices[0].message.content

        print("\nRAW MODEL RESPONSE:\n")
        print(reply)

        parsed = parse_response(reply)

        print("\nPARSED RESPONSE:\n")
        print(parsed)

        action = parsed["action"]
        tool_input = parsed["input"]

        if action == "NONE":
            print("\nAgent finished.\n")
            break

        if action == "bash":

            result = execute_bash(tool_input)

            print("\nCOMMAND RESULT:\n")
            print(result)

            observation_message = f"""
Observation:
{result}
"""

            messages.append({
                "role": "assistant",
                "content": reply
            })

            messages.append({
                "role": "user",
                "content": observation_message
            })

    return