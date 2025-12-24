# agent_fun.py
import asyncio, json, sys
from typing import Dict, Any, List
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from ollama import chat  # pip install ollama

SYSTEM = (
    "You are a cheerful weekend helper. You can call MCP tools.\n"
    "Decide step-by-step (ReAct). If you need a tool, output ONLY JSON:\n"
    '{"action":"<tool_name>","args":{...}}\n'
    "If you can answer, output ONLY JSON:\n"
    '{"action":"final","answer":"..."}'
)

def llm_json(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    resp = chat(model="mistral:7b", messages=messages, options={"temperature": 0.2})
    txt = resp["message"]["content"]
    try:
        return json.loads(txt)
    except Exception:
        # force JSON if model drifted
        fix = chat(model="mistral:7b",
                   messages=[{"role": "system", "content": "Return ONLY valid JSON."},
                             {"role": "user", "content": txt}],
                   options={"temperature": 0})
        return json.loads(fix["message"]["content"])

async def main():
    server_path = sys.argv[1] if len(sys.argv) > 1 else "server_fun.py"
    exit_stack = AsyncExitStack()
    stdio = await exit_stack.enter_async_context(
        stdio_client(StdioServerParameters(command="python", args=[server_path]))
    )
    r_in, w_out = stdio
    session = await exit_stack.enter_async_context(ClientSession(r_in, w_out))
    await session.initialize()

    tools = (await session.list_tools()).tools
    tool_index = {t.name: t for t in tools}
    print("Connected tools:", list(tool_index.keys()))

    history = [{"role": "system", "content": SYSTEM}]
    try:
        while True:
            user = input("\nYou: ").strip()
            if not user or user.lower() in {"exit","quit"}: break
            history.append({"role": "user", "content": user})

            for _ in range(4):  # small safety loop
                decision = llm_json(history)
                if decision.get("action") == "final":
                    answer = decision.get("answer","")
                    # one-shot reflection
                    reflect = chat(model="mistral:7b",
                                   messages=[{"role":"system","content":"Check for mistakes or missing tool calls. If fine, reply 'looks good'; else give corrected answer."},
                                             {"role":"user","content": answer}],
                                   options={"temperature": 0})
                    if reflect["message"]["content"].strip().lower() != "looks good":
                        answer = reflect["message"]["content"]
                    print("\nAgent:", answer)
                    history.append({"role":"assistant","content": answer})
                    break

                tname = decision.get("action")
                args = decision.get("args", {})
                if tname not in tool_index:
                    history.append({"role":"assistant","content": f"(unknown tool {tname})"})
                    continue

                result = await session.call_tool(tname, args)
                payload = result.content[0].text if result.content else result.model_dump_json()
                history.append({"role":"assistant","content": f"[tool:{tname}] {payload}"})
    finally:
        await exit_stack.aclose()

if __name__ == "__main__":
    asyncio.run(main())
