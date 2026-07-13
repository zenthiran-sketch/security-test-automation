"""Curated tool catalog for the web console UI — backed by tool_registry."""

from typing import Any, Dict, List

from server.tool_registry import TOOL_REGISTRY, catalog_entries, tools_for_profile


def get_catalog(include_availability: bool = True) -> List[Dict[str, Any]]:
    return catalog_entries(include_availability=include_availability)


def get_catalog_tool_names() -> List[str]:
    return list(TOOL_REGISTRY.keys())


def get_all_web_tools(available_only: bool = True) -> List[Dict[str, Any]]:
    return tools_for_profile("web_url", available_only=available_only)
