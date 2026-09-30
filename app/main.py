import argparse
import json
import os
import subprocess
import sys

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")


def read(file_path):
    with open(file_path) as f:
        content = f.read()

    return content


def write(file_path, content):
    with open(file_path, "w") as f:
        f.write(content)

    return f"The content is written to {file_path}"


def run_bash_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

    if result.stderr:
        return f"Error: {result.stderr}"

    return f"Success: {result.stdout}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()

    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    messages = [{"role": "user", "content": args.p}]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "Read",
                "description": "Read and return the contents of a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path to the file to read",
                        }
                    },
                    "required": ["file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "Write",
                "description": "Write content to a file",
                "parameters": {
                    "type": "object",
                    "required": ["file_path", "content"],
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path of the file to write to",
                        },
                        "content": {
                            "type": "string",
                            "description": "The content to write to the file",
                        },
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "Bash",
                "description": "Run bash command",
                "parameters": {
                    "type": "object",
                    "required": ["cmd"],
                    "properties": {
                        "cmd": {
                            "type": "string",
                            "description": "The command that should be run",
                        }
                    },
                },
            },
        },
    ]

    while True:
        chat = client.chat.completions.create(
            model="anthropic/claude-haiku-4.5",
            messages=messages,
            tools=tools,
        )

        if not chat.choices:
            raise RuntimeError("no choices in response")

        # messages.append(
        #     {
        #         "role": chat.choices[0].message.role,
        #         "content": chat.choices[0].message.content,
        #     }
        # )

        messages.append(chat.choices[0].message)

        if not chat.choices[0].message.tool_calls:
            break

        for tool_to_be_called in chat.choices[0].message.tool_calls:
            tool_function = tool_to_be_called.function

            tool_call_id = tool_to_be_called.id

            tool_function_name = tool_function.name

            if tool_function_name == "Read":
                tool_argument = json.loads(tool_function.arguments)
                file_path = tool_argument["file_path"]

                try:
                    content = read(file_path)
                except Exception as e:
                    content = f"Error: {e}"
            elif tool_function_name == "Write":
                tool_argument = json.loads(tool_function.arguments)
                file_path = tool_argument["file_path"]
                input_content = tool_argument["content"]

                try:
                    content = write(file_path, input_content)
                except Exception as e:
                    content = f"Error: {e}"
            elif tool_function_name == "Bash":
                tool_argument = json.loads(tool_function.arguments)
                cmd = tool_argument["cmd"]

                try:
                    content = run_bash_cmd(cmd)
                except Exception as e:
                    content = f"Error: {e}"

            else:
                content = f"Unknown function name: {tool_function_name}"

            messages.append(
                {"role": "tool", "tool_call_id": tool_call_id, "content": content}
            )

    # if chat.choices[0].message.tool_calls:
    #     tool_to_be_called = chat.choices[0].message.tool_calls[0]

    #     tool_function = tool_to_be_called.function

    #     tool_function_name = tool_function.name
    #     tool_argument = json.loads(tool_function.arguments)

    #     file_path = tool_argument["file_path"]

    #     if tool_function_name == "Read":
    #         chat.choices[0].message.content = read(file_path)

    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!", file=sys.stderr)

    # TODO: Uncomment the following line to pass the first stage
    print(chat.choices[0].message.content)


if __name__ == "__main__":
    main()
