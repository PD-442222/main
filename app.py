"""FastAPI-based MCP server for SAP Purchase Requisition API."""
from __future__ import annotations

import json
import os
import pathlib
import sys
from typing import Optional

CURRENT_DIR = pathlib.Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from model_context_protocol.fastapi import FastAPIMCPServer

load_dotenv()

API_KEY_ENV_VAR = "SAP_API_KEY"
SAP_PURCHASE_REQUISITION_URL = (
    "https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata4/"
    "sap/api_purchaserequisition_2/srvd_a2x/sap/purchaserequisition/0001/"
    "PurchaseReqn"
)

app = FastAPI(title="SAP Purchase Requisition MCP Server", version="0.1.0")
server = FastAPIMCPServer(app)


def _get_api_key() -> str:
    """Load the SAP API key from the environment."""
    api_key = os.getenv(API_KEY_ENV_VAR)
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail=(
                "The SAP API key is not configured. Set the environment variable "
                f"{API_KEY_ENV_VAR} before calling this tool."
            ),
        )
    return api_key


async def _call_sap_api(
    *,
    api_key: str,
    top: int,
    select: Optional[str],
    filter_: Optional[str],
) -> dict:
    """Fetch purchase requisition data from the SAP sandbox API."""
    headers = {
        "APIKey": api_key,
        "Accept": "application/json",
        "Accept-Language": "en",
    }
    params = {"$top": top}
    if select:
        params["$select"] = select
    if filter_:
        params["$filter"] = filter_

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            SAP_PURCHASE_REQUISITION_URL,
            headers=headers,
            params=params,
        )

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"SAP API request failed: {exc.response.text}",
        ) from exc

    try:
        data = response.json()
    except ValueError as exc:  # pragma: no cover - unexpected API response
        raise HTTPException(status_code=502, detail="SAP API returned invalid JSON") from exc

    return data


@server.tool(
    name="list_purchase_requisitions",
    description=(
        "Retrieve purchase requisitions from the SAP sandbox OData endpoint. "
        "Supports optional $select and $filter expressions to trim the payload."
    ),
)
async def list_purchase_requisitions(
    top: int = 50,
    select: Optional[str] = None,
    filter: Optional[str] = None,
):
    """Return purchase requisition data from SAP."""
    if top <= 0 or top > 200:
        raise HTTPException(
            status_code=400,
            detail="Parameter 'top' must be between 1 and 200 for sandbox usage.",
        )

    api_key = _get_api_key()
    data = await _call_sap_api(api_key=api_key, top=top, select=select, filter_=filter)

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(data, indent=2),
            }
        ]
    }


@app.get("/", response_class=JSONResponse)
async def root():
    """Simple health endpoint."""
    return {"status": "ok", "mcp": "available"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
