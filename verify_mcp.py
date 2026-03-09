#!/usr/bin/env python3
"""Run the Facebook MCP server and verify it responds to initialize + tools/list."""
import json
import subprocess
import sys

def main():
    env = {"PYTHONPATH": "src", "FACEBOOK_PAGE_ID": "1078511068671402"}
    # Optional: set a dummy token so debug_token can run (or leave unset to test env check)
    # env["FACEBOOK_PAGE_ACCESS_TOKEN"] = "test"

    proc = subprocess.Popen(
        [sys.executable, "-c", "from facebook_mcp_server import main; main()"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd="/Users/sarangali/Workspace/facebookmcp/facebook-mcp-server",
        env={**__import__("os").environ, **env},
    )

    def send(req: dict):
        line = json.dumps(req) + "\n"
        proc.stdin.write(line)
        proc.stdin.flush()

    def recv() -> dict:
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("Server closed stdout")
        return json.loads(line)

    try:
        # Initialize
        send({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "verify_mcp", "version": "0.1.0"},
            },
        })
        init_resp = recv()
        if "error" in init_resp:
            print("initialize ERROR:", json.dumps(init_resp, indent=2))
            return 1
        print("initialize OK:", init_resp.get("result", {}).get("serverInfo"))

        # Notify initialized (required by MCP)
        send({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        })

        # List tools
        send({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
        })
        tools_resp = recv()
        if "error" in tools_resp:
            print("tools/list ERROR:", json.dumps(tools_resp, indent=2))
            return 1
        tools = tools_resp.get("result", {}).get("tools", [])
        names = [t.get("name") for t in tools]
        print("tools/list OK:", names)
        assert "get_page_posts" in names
        assert "debug_token" in names

        # Call debug_token (no token set -> env check only)
        send({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "debug_token", "arguments": {}},
        })
        call_resp = recv()
        if "error" in call_resp:
            print("tools/call debug_token ERROR:", call_resp.get("error"))
        else:
            text = call_resp.get("result", {}).get("content", [{}])[0].get("text", "{}")
            print("debug_token result:", text[:500] + "..." if len(text) > 500 else text)

        print("\nVerification passed: MCP server works.")
        return 0
    finally:
        proc.terminate()
        proc.wait(timeout=2)
        stderr = proc.stderr.read()
        if stderr:
            print("Server stderr:", stderr, file=sys.stderr)

if __name__ == "__main__":
    sys.exit(main())
