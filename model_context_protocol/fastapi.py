"""Lightweight reimplementation of FastAPI helpers for MCP tools.

This module provides a small subset of the functionality exposed by the
``model-context-protocol`` package so the project can run in environments where
that package is not available on PyPI (e.g. Hugging Face Spaces build images).

The implementation focuses on two concerns:

* registering tool handlers that are exposed over HTTP to AgentKit-compatible
  clients; and
* generating a JSON schema for those tools so that clients can understand the
  available parameters.

Only the behaviour required by this project is implemented. The API mirrors the
real helper closely enough that swapping back to the official dependency simply
requires reinstalling the package and removing this module.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi import Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, create_model


ToolCallable = Callable[..., Awaitable[Any] | Any]


@dataclass
class _ToolDefinition:
    """Stores metadata required to expose a tool over HTTP."""

    name: str
    description: str
    endpoint: str
    handler: ToolCallable
    model: type[BaseModel]

    @property
    def schema(self) -> Dict[str, Any]:
        """Return the JSON schema for the tool's request body."""
        schema = self.model.model_json_schema()
        # The schema contains ``title`` and ``definitions`` keys that are not
        # strictly required for clients. Returning only ``properties`` and
        # ``required`` keeps the payload compact while still conveying the
        # necessary structure.
        return {
            "type": "object",
            "properties": schema.get("properties", {}),
            "required": schema.get("required", []),
        }


class FastAPIMCPServer:
    """Registers MCP tools on a FastAPI application.

    Parameters
    ----------
    app:
        The FastAPI application to attach routes to.
    base_path:
        The URL prefix for MCP routes. Defaults to ``"/mcp"``.
    """

    def __init__(self, app: FastAPI, *, base_path: str = "/mcp") -> None:
        self._app = app
        self._base_path = base_path.rstrip("/")
        self._router = APIRouter()
        self._tools: Dict[str, _ToolDefinition] = {}

        # A discovery endpoint so clients can learn the available tools.
        @self._router.get("/tools", response_class=JSONResponse)
        async def list_tools() -> Dict[str, Any]:
            return {
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.schema,
                        "endpoint": f"{self._base_path}{tool.endpoint}",
                    }
                    for tool in self._tools.values()
                ]
            }

        self._app.include_router(self._router, prefix=self._base_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def tool(self, *, name: str, description: str) -> Callable[[ToolCallable], ToolCallable]:
        """Decorator used to register a tool with the MCP server."""

        def decorator(func: ToolCallable) -> ToolCallable:
            if name in self._tools:
                raise ValueError(f"A tool named '{name}' is already registered")

            model = self._build_model_for_callable(name, func)
            endpoint_path = f"/tools/{name}"

            async def call_tool(payload: model = Body(...)) -> Any:  # type: ignore[misc]
                data = payload.model_dump(exclude_unset=True)
                try:
                    result = func(**data)
                    if inspect.isawaitable(result):
                        result = await result  # type: ignore[assignment]
                except TypeError as exc:  # pragma: no cover - defensive programming
                    raise HTTPException(status_code=400, detail=str(exc)) from exc
                return result

            self._router.post(endpoint_path, response_class=JSONResponse)(call_tool)
            self._tools[name] = _ToolDefinition(
                name=name,
                description=description,
                endpoint=endpoint_path,
                handler=func,
                model=model,
            )
            return func

        return decorator

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _build_model_for_callable(name: str, func: ToolCallable) -> type[BaseModel]:
        signature = inspect.signature(func)
        annotations = inspect.get_annotations(func)
        fields: Dict[str, tuple[Any, Any]] = {}

        for parameter_name, parameter in signature.parameters.items():
            if parameter.kind in {parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD}:
                raise TypeError(
                    "Var-args are not supported for MCP tool registration"
                )

            annotation = annotations.get(parameter_name, Any)
            default: Any
            if parameter.default is inspect.Signature.empty:
                default = ...
            else:
                default = parameter.default

            fields[parameter_name] = (annotation, default)

        model_name = f"{name.title().replace('_', '')}ToolInput"
        return create_model(model_name, **fields)  # type: ignore[call-arg]
