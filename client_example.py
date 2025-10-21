"""Helper script to verify the SAP MCP server is reachable and working.

Usage examples::

    python client_example.py
    python client_example.py --base-url https://your-space.hf.space --top 5

You can also set the environment variable ``MCP_SERVER_URL`` instead of
passing ``--base-url``.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any

import httpx


def _normalise_base_url(url: str) -> str:
    """Ensure the base URL does not end with a slash."""
    return url[:-1] if url.endswith("/") else url


async def _get_json(client: httpx.AsyncClient, url: str) -> Any:
    response = await client.get(url)
    response.raise_for_status()
    return response.json()


async def _post_json(client: httpx.AsyncClient, url: str, payload: dict[str, Any]) -> Any:
    response = await client.post(url, json=payload)
    response.raise_for_status()
    return response.json()


async def main(base_url: str, top: int) -> None:
    base_url = _normalise_base_url(base_url)
    print(f"Checking MCP server at {base_url} ...\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Health check
        health = await _get_json(client, f"{base_url}/")
        print("Health endpoint (/):")
        print(json.dumps(health, indent=2), "\n")

        # 2. Discover tools
        tools_payload = await _get_json(client, f"{base_url}/mcp/tools")
        print("Discovered tools:")
        print(json.dumps(tools_payload, indent=2), "\n")

        if not tools_payload.get("tools"):
            print("No tools were returned. Check the server logs and ensure the deployment includes app.py.")
            return

        # 3. Call the purchase requisition tool
        tool_endpoint = f"{base_url}/mcp/tools/list_purchase_requisitions"
        print(f"Calling list_purchase_requisitions (top={top}) ...")
        result = await _post_json(client, tool_endpoint, {"top": top})

        print("\nTool response:")
        print(json.dumps(result, indent=2))
        print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quick MCP tool smoke test")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("MCP_SERVER_URL", "http://localhost:8000"),
        help="Root URL of the MCP server (default: http://localhost:8000 or MCP_SERVER_URL env)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Number of purchase requisitions to request (default: 5)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(main(args.base_url, args.top))
    except httpx.HTTPError as exc:  # pragma: no cover - best effort CLI feedback
        raise SystemExit(f"Request failed: {exc}") from exc
