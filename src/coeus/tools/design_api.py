# Copyright (c) 2026 Reza Malik. Licensed under the Apache License, Version 2.0.
"""MCP tool: design_api

Takes a domain model and communication requirements. Returns an API blueprint
with recommended style, contract structure, versioning strategy, error handling,
and authentication approach.
"""

from __future__ import annotations

from typing import Any

from coeus.tools._shared import coerce, emit_event, get_knowledge

# ---------------------------------------------------------------------------
# API style selection heuristics
# ---------------------------------------------------------------------------

_API_STYLE_SIGNALS: dict[str, list[str]] = {
    "rest": [
        "crud", "resource", "public api", "third-party", "mobile",
        "cacheable", "browser", "openapi", "swagger", "simple",
    ],
    "graphql": [
        "flexible queries", "nested data", "multiple clients",
        "frontend-driven", "schema-first", "graph", "relay",
        "underfetching", "overfetching",
    ],
    "grpc": [
        "internal service", "low latency", "binary protocol",
        "streaming", "protobuf", "service mesh", "high throughput",
        "microservice communication",
    ],
    "websocket": [
        "real-time", "bidirectional", "chat", "live updates",
        "push notifications", "collaborative", "multiplayer",
    ],
    "event-driven": [
        "async", "event", "pub/sub", "message queue", "webhook",
        "notification", "eventual consistency", "decoupled",
    ],
}

_VERSIONING_STRATEGIES: dict[str, dict[str, str]] = {
    "url": {
        "approach": "URL path versioning (e.g., /v1/users, /v2/users)",
        "pros": "Explicit, cacheable, easy to route and test",
        "cons": "URL pollution, harder to sunset incrementally",
        "best_for": "Public APIs, REST services, simple versioning needs",
    },
    "header": {
        "approach": "Header-based versioning (e.g., Accept: application/vnd.api+json;version=2)",
        "pros": "Clean URLs, fine-grained control, content negotiation",
        "cons": "Harder to test in browser, less discoverable",
        "best_for": "Enterprise APIs, APIs with many versions, content negotiation",
    },
    "query": {
        "approach": "Query parameter versioning (e.g., /users?version=2)",
        "pros": "Easy to implement, optional parameter",
        "cons": "Breaks caching, not RESTful, easy to forget",
        "best_for": "Internal APIs, quick prototyping",
    },
}

_ERROR_HANDLING: dict[str, Any] = {
    "structure": {
        "error": {
            "code": "RESOURCE_NOT_FOUND",
            "message": "Human-readable description",
            "details": [],
            "request_id": "for tracing",
        }
    },
    "principles": [
        "Use standard HTTP status codes (4xx for client errors, 5xx for server errors)",
        "Include machine-readable error codes alongside human-readable messages",
        "Attach a request_id for distributed tracing and support debugging",
        "Provide actionable details when possible (which field failed, what's expected)",
        "Never expose internal stack traces or implementation details",
        "Use problem+json (RFC 7807) for structured error responses",
    ],
}

_AUTH_APPROACHES: dict[str, dict[str, str]] = {
    "api_key": {
        "approach": "API key authentication",
        "best_for": "Simple integrations, server-to-server, internal services",
        "considerations": "Rotate regularly, scope per-service, never embed in client code",
    },
    "oauth2": {
        "approach": "OAuth 2.0 with JWT tokens",
        "best_for": "User-facing APIs, third-party integrations, SSO",
        "considerations": "Use PKCE for public clients, short-lived access tokens, refresh token rotation",
    },
    "mutual_tls": {
        "approach": "Mutual TLS (mTLS) certificate authentication",
        "best_for": "Service mesh, zero-trust networks, high-security environments",
        "considerations": "Certificate management overhead, requires PKI infrastructure",
    },
}


# ---------------------------------------------------------------------------
# Main tool
# ---------------------------------------------------------------------------

def design_api(
    domain_model: str,
    communication_requirements: dict | None = None,
    style_preference: str | None = None,
    conn: object = None,
) -> dict:
    """Design an API blueprint for a given domain model.

    Args:
        domain_model: Description of the domain entities and their
            relationships (e.g. "Users have Orders, Orders contain Items").
        communication_requirements: Optional dict describing communication
            needs, e.g. ``{"clients": ["web", "mobile"], "latency": "low",
            "real_time": false}``.
        style_preference: Optional preferred API style ("rest", "graphql",
            "grpc", "websocket", "event-driven"). If None, auto-detected.
        conn: Kuzu/LadybugDB connection for graph mode, or None for JSON.

    Returns:
        Dict with keys: recommended_style, rationale, contract_structure,
        versioning_strategy, error_handling, authentication_approach.
    """
    communication_requirements = coerce(communication_requirements, dict) or {}

    kb = get_knowledge(conn)

    # 1. Auto-detect API style from domain model + requirements
    model_lower = domain_model.lower()
    req_text = " ".join(str(v) for v in communication_requirements.values()).lower()
    combined_text = f"{model_lower} {req_text}"

    if style_preference and style_preference.lower() in _API_STYLE_SIGNALS:
        recommended_style = style_preference.lower()
    else:
        # Score each style by signal matches
        style_scores: dict[str, int] = {}
        for style, signals in _API_STYLE_SIGNALS.items():
            score = sum(1 for s in signals if s in combined_text)
            style_scores[style] = score

        # Default to REST if no strong signals
        best_style = max(style_scores, key=style_scores.get)  # type: ignore[arg-type]
        recommended_style = best_style if style_scores[best_style] > 0 else "rest"

    # 2. Build rationale from knowledge base
    style_to_pattern_prefix = {
        "rest": "rest_",
        "graphql": "graphql_",
        "grpc": "grpc_",
        "websocket": "websocket_",
        "event-driven": "pub_sub_",
    }

    # Find relevant patterns from API/data knowledge
    prefix = style_to_pattern_prefix.get(recommended_style, "rest_")
    relevant_patterns = [
        p for p in kb._api_data_patterns
        if p["id"].startswith(prefix)
    ]

    rationale_parts: list[str] = []
    if relevant_patterns:
        primary = relevant_patterns[0]
        rationale_parts.append(primary.get("description", "")[:200])
        rationale_parts.append(
            f"Matched {len(relevant_patterns)} {recommended_style.upper()} patterns "
            f"from the knowledge base."
        )
    if communication_requirements:
        rationale_parts.append(
            f"Communication requirements considered: {', '.join(communication_requirements.keys())}."
        )

    # 3. Contract structure
    contract_structure: dict[str, Any] = {
        "style": recommended_style,
        "domain_entities": domain_model[:200],
        "relevant_patterns": [
            {"id": p["id"], "name": p["name"]}
            for p in relevant_patterns[:5]
        ],
    }

    if recommended_style == "rest":
        contract_structure["conventions"] = {
            "naming": "Plural nouns for collections (/users, /orders)",
            "methods": "GET (read), POST (create), PUT (replace), PATCH (update), DELETE (remove)",
            "pagination": "Cursor-based for large collections, offset for small",
            "filtering": "Query parameters for simple filters, POST body for complex queries",
        }
    elif recommended_style == "graphql":
        contract_structure["conventions"] = {
            "schema": "Schema-first design with SDL",
            "queries": "Use DataLoader for N+1 prevention",
            "mutations": "Input types for all mutations, return affected objects",
            "subscriptions": "WebSocket transport for real-time updates",
        }
    elif recommended_style == "grpc":
        contract_structure["conventions"] = {
            "schema": "Protocol Buffers v3 for service definitions",
            "streaming": "Use server streaming for large result sets",
            "errors": "Use standard gRPC status codes with details",
            "evolution": "Add fields (never remove), use field numbers for backward compatibility",
        }

    # 4. Versioning strategy
    if recommended_style == "rest":
        versioning = _VERSIONING_STRATEGIES["url"]
    elif recommended_style == "graphql":
        versioning = {
            "approach": "Schema evolution (no versioning — deprecate fields, add new ones)",
            "pros": "Single endpoint, no version management, gradual migration",
            "cons": "Requires discipline in deprecation, monitoring field usage",
            "best_for": "GraphQL APIs with controlled client base",
        }
    elif recommended_style == "grpc":
        versioning = {
            "approach": "Protobuf schema evolution with field numbers",
            "pros": "Backward compatible by design, binary efficiency",
            "cons": "Cannot remove fields, field number management",
            "best_for": "Internal service communication with strict contracts",
        }
    else:
        versioning = _VERSIONING_STRATEGIES["header"]

    # 5. Authentication approach
    clients = communication_requirements.get("clients", [])
    if isinstance(clients, str):
        clients = [clients]
    clients_lower = [c.lower() for c in clients]

    if any(c in clients_lower for c in ["web", "mobile", "browser"]):
        auth = _AUTH_APPROACHES["oauth2"]
    elif any(c in clients_lower for c in ["service", "internal", "backend"]):
        auth = _AUTH_APPROACHES["mutual_tls"]
    else:
        auth = _AUTH_APPROACHES["api_key"]

    # 6. Build result
    result: dict[str, Any] = {
        "recommended_style": recommended_style,
        "rationale": " ".join(rationale_parts),
        "contract_structure": contract_structure,
        "versioning_strategy": versioning,
        "error_handling": _ERROR_HANDLING,
        "authentication_approach": auth,
    }

    emit_event("design_api", {
        "domain_model": domain_model[:120],
        "recommended_style": recommended_style,
        "patterns_matched": len(relevant_patterns),
    })

    return result
