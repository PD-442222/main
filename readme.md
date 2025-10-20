# SAP Purchase Requisition MCP Server

This repository contains a minimal [Model Context Protocol (MCP)](https://spec.modelcontextprotocol.io/) server that exposes tools for querying the SAP Purchase Requisition sandbox API. The server is implemented with FastAPI and packaged for easy deployment to Hugging Face Spaces or any other platform that can run a Python web service.

## Features

- MCP-compliant server that can be connected to OpenAI AgentKit.
- Single tool `list_purchase_requisitions` that wraps the SAP OData endpoint.
- Environment-based configuration for the SAP API key.
- Ready for cloud deployment via `uvicorn` (works on Hugging Face Spaces, Render, etc.).

## Requirements

- Python 3.9+
- SAP sandbox API key (obtainable from the SAP API Hub)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Create an `.env` file or set the `SAP_API_KEY` environment variable directly:

```bash
SAP_API_KEY="your-sap-api-key"
```

If you prefer using a `.env` file locally, place it next to `app.py`.

## Running locally

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

The root endpoint (`/`) provides a simple health response. The MCP server is exposed over the same FastAPI app and can be consumed by AgentKit using the standard MCP client configuration.

## Connecting from OpenAI AgentKit

1. Expose the running server to the public internet (for example using [ngrok](https://ngrok.com/) with `ngrok http 8000`).
2. Create an AgentKit tool configuration pointing to your MCP server. For example:

```json
{
  "url": "wss://<your-ngrok-subdomain>.ngrok.io/mcp",
  "capabilities": ["tools"],
  "name": "sap_purchase_requisitions"
}
```

AgentKit will discover the `list_purchase_requisitions` tool, allowing agents to query the SAP sandbox data.

## Deployment to Hugging Face Spaces

1. Create a new **FastAPI** space and upload `app.py` and `requirements.txt`.
2. Add the `SAP_API_KEY` secret in the **Variables** section of the space settings.
3. Spaces automatically launches `uvicorn` with `app:app`.

## Development notes

- The SAP sandbox enforces rate limits; keep the `top` parameter modest.
- You can use the `$select` and `$filter` parameters to minimize payload size.
- Error messages from SAP are surfaced directly in the MCP tool response for easier debugging.

## Testing

This project has no automated tests yet, but you can validate syntax with:

```bash
python -m compileall app.py
```
