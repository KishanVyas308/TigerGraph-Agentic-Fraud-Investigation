"""TigerGraph MCP Adapter — Model Context Protocol tool interface for LangGraph agents."""

from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel

from backend.app.graph.models import (
    CaseTimelineParams,
    CaseUpdateParams,
    DeviceIdentityParams,
    EntityNeighborhoodParams,
    FraudNeighborsParams,
    MoneyFlowPatternParams,
    SharedDeviceParams,
    SharedIPParams,
    ShortestPathParams,
    SimilarGraphCasesParams,
    ToolPermission,
    TransactionBehaviorParams,
    TransactionContextParams,
    VectorSearchParams,
)
from backend.app.graph.tigergraph_client import TigerGraphClient, get_tigergraph_client
from backend.app.utils.logging import get_logger

logger = get_logger("graph.mcp")


class MCPToolDefinition(BaseModel):
    """Schema definition for an MCP tool."""
    name: str
    description: str
    permission: ToolPermission
    input_schema: Dict[str, Any]


class TigerGraphMCPAdapter:
    """Adapter exposing restricted, safe TigerGraph queries as MCP tools."""

    def __init__(self, client: Optional[TigerGraphClient] = None):
        self.client = client or get_tigergraph_client()
        self._tools: Dict[str, MCPToolDefinition] = {}
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self._register_tools()

    def _register_tool(
        self,
        name: str,
        description: str,
        permission: ToolPermission,
        param_model: type[BaseModel],
        handler: Callable[[Dict[str, Any]], Any],
    ) -> None:
        schema = param_model.model_json_schema()
        self._tools[name] = MCPToolDefinition(
            name=name,
            description=description,
            permission=permission,
            input_schema=schema,
        )
        self._handlers[name] = handler

    def _register_tools(self) -> None:
        """Register all allowed read and safe append tools."""
        self._register_tool(
            name="get_transaction_context",
            description="Retrieve 1-hop context of a transaction (customer, account, merchant, device, IP).",
            permission=ToolPermission.READ_ONLY,
            param_model=TransactionContextParams,
            handler=lambda args: self.client.get_transaction_context(args["transaction_id"]).model_dump(),
        )

        self._register_tool(
            name="get_transaction_behavior",
            description="Calculate historical behavioral baseline, velocity, and merchant novelty.",
            permission=ToolPermission.READ_ONLY,
            param_model=TransactionBehaviorParams,
            handler=lambda args: self.client.get_transaction_behavior(
                args["transaction_id"], args.get("lookback_hours", 24)
            ).model_dump(),
        )

        self._register_tool(
            name="get_entity_neighborhood",
            description="Retrieve bounded k-hop subgraph around an entity for visualization.",
            permission=ToolPermission.READ_ONLY,
            param_model=EntityNeighborhoodParams,
            handler=lambda args: self.client.get_entity_neighborhood(
                args["vertex_id"], args.get("max_depth", 2), args.get("max_vertices", 50)
            ).model_dump(),
        )

        self._register_tool(
            name="find_shared_devices",
            description="Find accounts and customers sharing a hardware device with prior fraud flags.",
            permission=ToolPermission.READ_ONLY,
            param_model=SharedDeviceParams,
            handler=lambda args: self.client.find_shared_devices(args["device_id"]).model_dump(),
        )

        self._register_tool(
            name="find_shared_ips",
            description="Find accounts and transactions aggregating on an IP address.",
            permission=ToolPermission.READ_ONLY,
            param_model=SharedIPParams,
            handler=lambda args: self.client.find_shared_ips(args["ip_address"]).model_dump(),
        )

        self._register_tool(
            name="find_fraud_neighbors",
            description="Identify neighbors linked to confirmed historical fraud cases.",
            permission=ToolPermission.READ_ONLY,
            param_model=FraudNeighborsParams,
            handler=lambda args: self.client.find_fraud_neighbors(
                args["vertex_id"], args.get("max_hops", 2)
            ).model_dump(),
        )

        self._register_tool(
            name="get_shortest_path_to_fraud",
            description="Compute bounded shortest distance to any confirmed fraud entity.",
            permission=ToolPermission.READ_ONLY,
            param_model=ShortestPathParams,
            handler=lambda args: self.client.get_shortest_path_to_fraud(
                args["vertex_id"], args.get("max_depth", 4)
            ).model_dump(),
        )

        self._register_tool(
            name="detect_money_flow_patterns",
            description="Calculate fan-in, fan-out, and circular money loops for an account.",
            permission=ToolPermission.READ_ONLY,
            param_model=MoneyFlowPatternParams,
            handler=lambda args: self.client.detect_money_flow_patterns(args["account_id"]).model_dump(),
        )

        self._register_tool(
            name="get_device_identity_context",
            description="Retrieve device hardware type, age, and linked account count.",
            permission=ToolPermission.READ_ONLY,
            param_model=DeviceIdentityParams,
            handler=lambda args: self.client.get_device_identity_context(args["device_id"]).model_dump(),
        )

        self._register_tool(
            name="find_similar_graph_cases",
            description="Retrieve top graph-similar cases sharing identical entities or typologies.",
            permission=ToolPermission.READ_ONLY,
            param_model=SimilarGraphCasesParams,
            handler=lambda args: self.client.find_similar_graph_cases(
                args["case_id"], args.get("limit", 5)
            ),
        )

        self._register_tool(
            name="get_case_timeline",
            description="Retrieve complete chronological audit trail of a case.",
            permission=ToolPermission.READ_ONLY,
            param_model=CaseTimelineParams,
            handler=lambda args: self.client.get_case_timeline(args["case_id"]),
        )

        self._register_tool(
            name="write_case_update",
            description="Safely append or update case state without overwriting history.",
            permission=ToolPermission.APPEND_ONLY,
            param_model=CaseUpdateParams,
            handler=lambda args: self.client.write_case_update(
                case_id=args["case_id"],
                status=args["status"],
                risk_level=args["risk_level"],
                confidence=args["confidence"],
                evidence_completeness=args["evidence_completeness"],
                summary=args["summary"],
                stop_reason=args.get("stop_reason"),
            ),
        )

        self._register_tool(
            name="vector_search",
            description="Retrieve semantically similar historical cases or fraud policies.",
            permission=ToolPermission.READ_ONLY,
            param_model=VectorSearchParams,
            handler=lambda args: self.client.vector_search(
                query_text=args["query_text"],
                collection=args.get("collection", "cases"),
                top_k=args.get("top_k", 3),
            ),
        )

    def list_tools(self) -> List[MCPToolDefinition]:
        """Return list of all registered MCP tool definitions."""
        return list(self._tools.values())

    def get_tool_definition(self, name: str) -> Optional[MCPToolDefinition]:
        """Retrieve schema for a specific tool."""
        return self._tools.get(name)

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an approved MCP tool call."""
        if name not in self._tools:
            logger.error("Forbidden or unknown MCP tool call: %s", name)
            return {"error": f"Tool '{name}' is not allowed or does not exist."}

        tool = self._tools[name]
        logger.info("Executing MCP tool '%s' (Permission: %s)", name, tool.permission.value)

        try:
            handler = self._handlers[name]
            result = handler(arguments)
            return {"status": "success", "tool": name, "data": result}
        except Exception as exc:
            logger.error("Error executing tool '%s': %s", name, exc)
            return {"status": "error", "tool": name, "error": str(exc)}
