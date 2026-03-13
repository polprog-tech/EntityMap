"""Service handlers for EntityMap."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse

from .analysis import analyze_impact
from .const import (
    ATTR_INCLUDE_INFERRED,
    ATTR_NODE_ID,
    DOMAIN,
    SERVICE_ANALYZE_IMPACT,
    SERVICE_GET_DEPENDENCIES,
    SERVICE_SCAN,
    Confidence,
)
from .graph import GraphBuilder

_LOGGER = logging.getLogger(__name__)


async def async_register_services(
    hass: HomeAssistant, builder: GraphBuilder
) -> None:
    """Register EntityMap services."""

    async def handle_scan(call: ServiceCall) -> ServiceResponse:
        """Handle the scan service call."""
        graph = await builder.async_build()
        return {
            "node_count": graph.node_count,
            "edge_count": graph.edge_count,
        }

    async def handle_analyze_impact(call: ServiceCall) -> ServiceResponse:
        """Handle the analyze_impact service call."""
        node_id = call.data[ATTR_NODE_ID]
        report = analyze_impact(builder.graph, node_id)
        return report.as_dict()

    async def handle_get_dependencies(call: ServiceCall) -> ServiceResponse:
        """Handle the get_dependencies service call."""
        node_id = call.data[ATTR_NODE_ID]
        include_inferred = call.data.get(ATTR_INCLUDE_INFERRED, True)
        graph = builder.graph

        if node_id not in graph.nodes:
            return {
                "node_id": node_id,
                "error": "Node not found in graph",
                "inbound": [],
                "outbound": [],
            }

        inbound_edges = graph.get_inbound(node_id)
        outbound_edges = graph.get_outbound(node_id)

        if not include_inferred:
            inbound_edges = [
                e for e in inbound_edges if e.confidence != Confidence.LOW
            ]
            outbound_edges = [
                e for e in outbound_edges if e.confidence != Confidence.LOW
            ]

        return {
            "node_id": node_id,
            "inbound": [e.as_dict() for e in inbound_edges],
            "outbound": [e.as_dict() for e in outbound_edges],
            "inbound_count": len(inbound_edges),
            "outbound_count": len(outbound_edges),
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_SCAN,
        handle_scan,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ANALYZE_IMPACT,
        handle_analyze_impact,
        schema=vol.Schema({vol.Required(ATTR_NODE_ID): str}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_DEPENDENCIES,
        handle_get_dependencies,
        schema=vol.Schema(
            {
                vol.Required(ATTR_NODE_ID): str,
                vol.Optional(ATTR_INCLUDE_INFERRED, default=True): bool,
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )


async def async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister EntityMap services."""
    hass.services.async_remove(DOMAIN, SERVICE_SCAN)
    hass.services.async_remove(DOMAIN, SERVICE_ANALYZE_IMPACT)
    hass.services.async_remove(DOMAIN, SERVICE_GET_DEPENDENCIES)
