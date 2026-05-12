import re


def parse_response(response_text):
    thought_match = re.search(r"Thought:\s*(.*)", response_text)
    action_match = re.search(r"Action:\s*(.*)", response_text)
    input_match = re.search(r"Input:\s*(.*)", response_text)

    result = {
        "thought": thought_match.group(1).strip() if thought_match else None,
        "action": action_match.group(1).strip() if action_match else None,
        "input": input_match.group(1).strip() if input_match else None,
    }

    return result