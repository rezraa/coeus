<p align="center">
  <img src="graphics/Coeus.png" alt="Coeus: Architecture Titan" width="100%">
</p>

<h1 align="center">Coeus</h1>

<p align="center">
  <strong>Architecture Titan for System Design, Scalability, and Resilience</strong><br>
  65 architecture patterns, 55 scalability patterns, 57 API and data patterns, and 71 decision rules. He thinks in tradeoffs, respects constraints, and never recommends microservices to a team of three.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white" alt="Python"></a>
  <a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP-Compatible-8A2BE2.svg" alt="MCP"></a>
  <a href="https://ko-fi.com/rezraa"><img src="https://img.shields.io/badge/Ko--fi-Support-ff5e5b.svg?logo=ko-fi&logoColor=white" alt="Ko-fi"></a>
</p>

---

## Why

Architecture tools give you diagrams. Coeus gives you decisions.

He carries 248 entries of structured architectural knowledge. You describe your system, your team size, your constraints. He matches structural signals against decision rules, recommends patterns with full tradeoff analysis, evaluates how your system holds up at 10x and 100x scale, designs your API contract, and finds every single point of failure in your architecture.

Every recommendation is constraint aware. A team of three building an MVP gets a modular monolith, not microservices. That is a cardinal rule, tested and enforced. A fifty person org running twelve services on Kubernetes gets a different answer entirely. Coeus does not chase trends. He reasons from first principles and structural forces.

He thinks across time horizons. What works now, what breaks at 10x, what you migrate to at 100x. All vendor neutral, all cloud agnostic.

Named after the Titan of intellect and rational intelligence. He sees how systems hold together and where they will fall apart.

## Knowledge Base

Structured architectural knowledge, not vibes.

| Category | Count | What |
|----------|-------|------|
| Architecture patterns | 65 | Structural (15): monolith, modular monolith, microservices, hexagonal, clean architecture, DDD. Behavioral (16): event driven, saga, CQRS, circuit breaker, rate limiting. Deployment (13): blue green, canary, GitOps, service mesh. Data flow (12): pipes and filters, stream processing, CDC. Hybrid (9): BFF, sidecar, ambassador. |
| Scalability patterns | 55 | Scaling (11): horizontal, vertical, sharding, replication. Caching (11): cache aside, write through, distributed cache, stampede prevention. Consensus (11): Raft, Paxos, eventual consistency, vector clocks. Resilience (11): circuit breaker, bulkhead, graceful degradation. Load management (11): rate limiting, backpressure, traffic shaping. |
| API and data patterns | 57 | REST (9): resource oriented, HATEOAS, pagination, versioning. GraphQL (6): schema first, DataLoader, federation. gRPC (6): streaming, bidirectional. Async (9): pub/sub, webhooks, SSE. Storage (9): relational, document, graph, time series. Processing (9): batch, stream, MapReduce. Streaming (9): Kafka, Kinesis, NATS, Pulsar. |
| Decision rules | 71 | Team scale (12), performance (8), data (11), API design (8), resilience (9), evolution (9), compliance (8), cost (6). Each rule maps structural signals to recommended patterns with priority and rationale. |

5 architecture categories. 5 scalability categories. 7 API and data categories. 8 rule categories. 248 total entries.

## Tools

| Tool | What it does |
|------|-------------|
| `analyze_architecture` | Analyzes existing architecture for issues, anti patterns, and risks. Detects 12 built in anti patterns including god service, distributed monolith, shared database, chatty services, synchronous chains, and missing circuit breakers. Returns matched rules, issues with severity, and recommendations. |
| `evaluate_scalability` | Evaluates how your architecture holds up across three tiers: 10x, 100x, and 1000x scale. Each tier identifies bottlenecks, recommends scaling patterns, and maps to specific patterns from the knowledge base. Takes growth projections like users, requests per second, and data volume. |
| `recommend_pattern` | The decision engine. Takes structural signals and constraints, matches against decision rules, scores patterns for fit, and returns ranked recommendations with full tradeoff analysis. Cardinal rule: small team plus MVP never gets microservices as number one. |
| `design_api` | Designs an API blueprint from a domain model. Auto detects the best style (REST, GraphQL, gRPC, WebSocket, event driven) based on communication requirements. Returns contract structure, versioning strategy, error handling conventions, and authentication approach. |
| `assess_resilience` | Finds every weak point in your architecture. Identifies single points of failure (6 detectors), missing resilience patterns (10 checks), blast radius indicators (6 checks), and generates hardening recommendations with priority. Returns a resilience score from 0 to 1. |

## Anti Pattern Detection

Coeus detects 12 architectural anti patterns out of the box:

| Signal | What it catches |
|--------|----------------|
| god-service | Monolithic service handling too many responsibilities |
| distributed-monolith | Microservices with tight coupling that deploy together |
| shared-database | Multiple services sharing one database |
| chatty-services | Excessive inter service calls creating latency chains |
| no-circuit-breaker | Missing fault tolerance on external calls |
| synchronous-chain | Long synchronous call chains causing cascading failures |
| no-caching | Missing cache layer on read heavy paths |
| single-point-of-failure | Critical component without redundancy |
| no-health-checks | Missing observability infrastructure |
| hardcoded-config | Configuration baked into code instead of environment |
| no-versioning | APIs without a version strategy |
| tight-coupling | High coupling making independent changes impossible |

## Resilience Assessment

Three layers of resilience analysis:

| Layer | Checks | What it finds |
|-------|--------|--------------|
| Single points of failure | 6 | Single database, single node, single region, no load balancer, single queue, single cache |
| Missing patterns | 10 | No circuit breaker, no retry, no timeout, no bulkhead, no fallback, no health checks, no dead letter queue, no idempotency, no rate limiting, no observability |
| Blast radius | 6 | Shared database, synchronous chain, shared library, monolith, shared cache, global load balancer |

Returns a resilience score from 0 to 1 with prioritized hardening recommendations.

## Quick Start

### Install

```bash
git clone https://github.com/rezraa/coeus.git
cd coeus
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
# 68 tests, all passing
```

### Configure with Claude Code

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "coeus": {
      "command": "/path/to/coeus/.venv/bin/python3",
      "args": ["-m", "coeus.server"],
      "cwd": "/path/to/coeus",
      "env": {
        "PYTHONPATH": "src"
      }
    }
  }
}
```

Then in Claude Code:

```
/architect I have a team of 3 building a CRUD web app. What architecture should we use?
```

## Architecture

```
Claude Code (top level LLM) -> invokes /architect agent
  +-- Coeus Agent (reasoning via persona + skill instructions)
       +-- Coeus MCP Tools (analyze, evaluate, recommend, design, assess)
            +-- Knowledge Base (JSON)
                 |-- architecture_patterns.json (65 patterns)
                 |-- scalability_patterns.json (55 patterns)
                 |-- api_and_data.json (57 patterns)
                 +-- decision_rules.json (71 rules)
```

Dual mode: all tools accept an optional `conn` parameter. Without it, Coeus runs standalone on local JSON. With it (inside Othrys), he reads from and writes to the shared Kuzu graph. Same logic, richer data.

## Project Structure

```
coeus/
+-- src/coeus/
|   |-- server.py                  # MCP server
|   |-- tools/
|   |   |-- analyze_architecture.py     # Architecture analysis
|   |   |-- evaluate_scalability.py     # Scalability evaluation
|   |   |-- recommend_pattern.py        # Pattern recommendation
|   |   |-- design_api.py              # API design
|   |   +-- assess_resilience.py        # Resilience assessment
|   +-- knowledge/
|       |-- architecture_patterns.json
|       |-- scalability_patterns.json
|       |-- api_and_data.json
|       |-- decision_rules.json
|       +-- loader.py              # Knowledge retrieval
+-- .claude/
|   |-- agents/coeus.md            # Agent persona
|   +-- skills/architect/          # Skill workflow
+-- tests/                         # 68 tests
+-- pyproject.toml
```

## Part of Othrys

Coeus is one of the Titans in the [Othrys](https://github.com/rezraa/othrys) summoning engine. Standalone, he analyzes architectures and recommends patterns for any project. Inside Othrys, his recommendations feed into the shared graph and his architecture decisions connect to test strategies (Themis), security reviews (Hyperion), and design systems (Theia).

## Support

If Coeus is useful to your work, consider [buying me a coffee](https://ko-fi.com/rezraa).

## Author

**Reza Malik** | [GitHub](https://github.com/rezraa) | [Ko-fi](https://ko-fi.com/rezraa)

## License

Copyright (c) 2026 Reza Malik. [Apache 2.0](LICENSE)
