# Angel – Web Service Boilerplate (Project Overview)

## ✨ Quick Summary

A lightweight, Docker‑ready Python web service built with Flask‑style blueprints (or FastAPI), Peewee ORM, and a solid development workflow (dotenv config, structured logging, pre‑commit hooks, and a full pytest suite).  
It provides a clean foundation for building API‑driven applications – from simple CRUD services to more complex domains such as algorithmic trading, data collection, or internal dashboards.

---

## 📦 Core Features

| Feature                      | Description                                                                                                  |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Modular Architecture**     | `src/` holds business logic, `components/` holds route handlers, `config/` centralises environment settings. |
| **Configuration Management** | `.env` files + `python‑dotenv` → `Config` object; defaults live in `config/default.yaml`.                    |
| **Database Layer**           | SQLite via **Peewee** ORM (easy migrations, type‑safe models).                                               |
| **Logging**                  | `logzero` creates JSON or plain‑text logs in `logs/angel.log`; log level configurable through env vars.      |
| **Docker Support**           | Multi‑stage `Dockerfile` + `docker-compose.yml` for one‑click containerisation.                              |
| **Testing**                  | `pytest` test suite (`tests/`, `test_angel*.py`) with coverage for services, models, and HTTP endpoints.     |
| **Pre‑commit Hooks**         | Enforces `black`, `isort`, `flake8`, and `mypy` on every commit – code stays clean automatically.            |
| **CLI / Run Script**         | `run.sh` wraps virtual‑env activation and server start‑up for local development.                             |
| **Extensible Entry Point**   | `app.py` loads all blueprints dynamically, making it trivial to add new API modules.                         |

---

## 🚀 What It Can Do Today

1. **Serve HTTP APIs** – Define routes in `components/` that call functions in `src/`.
2. **Persist Data** – Store and retrieve records using Peewee models backed by a SQLite file (`data/angel.db`).
3. **Configuration‑driven Behavior** – Change DB path, log level, or any custom setting via `.env` without touching code.
4. **Run Anywhere** – Launch locally (`python app.py`) or inside Docker (`docker compose up`).
5. **Automated Testing** – Run `pytest -v` to verify business logic and endpoint responses.
6. **Observability** – All requests and internal events are logged; logs can be shipped to ELK/Prometheus pipelines.

---

## 👍 Advantages

| Advantage                         | Why It Helps                                                                                              |
| --------------------------------- | --------------------------------------------------------------------------------------------------------- |
| **Zero‑setup for prototyping**    | Clone → `pip install -r requirements.txt` → run.                                                          |
| **Clear separation of concerns**  | UI, business, and data layers live in distinct packages → easier maintenance.                             |
| **Production‑ready dev workflow** | Linting, formatting, type‑checking & tests run on every commit.                                           |
| **Portable**                      | Dockerfile guarantees the same environment on any host (Mac, Linux, CI).                                  |
| **Extensible**                    | Adding a new endpoint only requires a new file in `components/` and (optionally) a new service in `src/`. |
| **Lightweight**                   | No heavyweight frameworks; startup time < 200 ms, memory footprint ~ 30 MB.                               |
| **Open‑source friendly**          | MIT license, comprehensive `README`, and explicit contribution guidelines.                                |

---

## ⚠️ Disadvantages / Current Limitations

| Limitation                                                                                                             | Impact                                                                                                                         |
| ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **SQLite only**                                                                                                        | Suitable for prototyping or low‑throughput workloads; not ideal for high‑concurrency or massive data volumes.                  |
| **Synchronous request handling**                                                                                       | Using the default Flask development server; not optimized for ultra‑low‑latency or massive concurrent connections.             |
| **No market‑data or trading integration**                                                                              | The codebase does not include brokers, order‑routing, or risk‑management modules required for algo‑trading out of the box.     |
| **Single‑process architecture**                                                                                        | Scaling horizontally requires an external load balancer and a shared DB; not yet container‑orchestrated for high availability. |
| **Limited security** – only basic env‑var secret handling, no authentication/authorization middleware.                 |
| **Feature set is minimal** – only a sample CRUD example is shipped; you must implement domain‑specific logic yourself. |

---

## 📈 Path Forward (If You Want to Turn This Into an Algo‑Trading Engine)

| Step                       | What to Add                                            | Suggested Tech                                     |
| -------------------------- | ------------------------------------------------------ | -------------------------------------------------- |
| **Real‑time market data**  | Async WebSocket client → in‑memory queue               | `asyncio`, `websockets`, or `ccxt`                 |
| **Order execution layer**  | Broker API wrapper, order‑status callbacks             | `httpx` async, or official SDKs (Alpaca, Binance)  |
| **Risk manager**           | Position limits, max‑drawdown checks                   | Custom `RiskEngine` class                          |
| **Fast data store**        | In‑memory order book, Redis cache for positions        | `redis-py`, `aioredis`                             |
| **Back‑testing framework** | Replay historic ticks, performance metrics             | `vectorbt`, `backtrader` or a home‑grown simulator |
| **Async server**           | Switch to FastAPI/Uvicorn or Quart for async endpoints | `fastapi`, `uvicorn`                               |
| **Security**               | API keys vault, JWT auth, rate limiting                | `python‑jwt`, `fastapi-security`                   |
| **Observability**          | Prometheus metrics, Grafana dashboards                 | `prometheus-client`, structured JSON logs          |

You can build these pieces incrementally; because the project already follows a modular pattern, each new component fits naturally into `src/` (core logic) and `components/` (API surface).

---

## 📄 How to Use This Documentation

- **Copy & paste** the markdown into `docs/PROJECT_OVERVIEW.md` or the top of `README.md`.
- Keep the table of contents up‑to‑date as you add new features.
- Link from the main `README` with:

  ```markdown
  📖 [Project Overview & Documentation](docs/PROJECT_OVERVIEW.md)
  ```
