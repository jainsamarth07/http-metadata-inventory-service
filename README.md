# HTTP Metadata Inventory Service

A FastAPI-based microservice that collects and retrieves HTTP metadata (headers, cookies, and page source) for any given URL. Built with **Python 3.11+**, **MongoDB**, and **Docker Compose**.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                    │
│                                                             │
│  POST /api/v1/metadata ──► Collector ──► MongoDB (upsert)   │
│                                                             │
│  GET  /api/v1/metadata ──► DB Lookup                        │
│           │                    │                            │
│           │ cache hit ◄────────┘                            │
│           │ cache miss ──► 202 + Background Task ──► Store  │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

- **Async-first**: Uses `httpx.AsyncClient` and Motor (async MongoDB driver) for non-blocking I/O.
- **Background collection**: On a GET cache miss, `asyncio.create_task()` schedules an internal background task — no self-HTTP calls or polling loops.
- **Deduplication**: A `set` of in-flight URLs prevents duplicate background tasks for the same URL.
- **Upsert strategy**: POST always upserts, so re-fetching a URL refreshes its metadata.
- **Indexed lookups**: A unique index on `url` ensures O(log n) lookups as the dataset grows.

---

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)

### Run the service

```bash
docker-compose up --build
```

The API will be available at **http://localhost:8000**.

### Stop the service

```bash
docker-compose down
```

To also remove stored data:

```bash
docker-compose down -v
```

---

## API Documentation

Once running, interactive docs are available at:

| UI | URL |
|----|-----|
| **Swagger UI** | http://localhost:8000/docs |
| **ReDoc** | http://localhost:8000/redoc |

### Endpoints

#### `POST /api/v1/metadata`

Collect metadata for a URL and store it.

**Request body:**
```json
{
  "url": "https://example.com"
}
```

**Response (201):**
```json
{
  "message": "Metadata collected and stored successfully.",
  "url": "https://example.com"
}
```

#### `GET /api/v1/metadata?url=<URL>`

Retrieve stored metadata for a URL.

**Cache hit — Response (200):**
```json
{
  "url": "https://example.com",
  "headers": { "content-type": "text/html", "..." : "..." },
  "cookies": {},
  "page_source": "<!doctype html>...",
  "created_at": "2026-02-06T12:00:00Z",
  "updated_at": "2026-02-06T12:00:00Z"
}
```

**Cache miss — Response (202):**
```json
{
  "message": "Request accepted. Metadata is being collected in the background.",
  "url": "https://example.com"
}
```

> After receiving a 202 response, simply retry the GET request after a few seconds — the data will be available once the background collection completes.

#### `GET /health`

Simple health check endpoint.

---

## Running Tests

### With Docker (recommended)

```bash
# Build and run tests inside the container
docker-compose run --rm api pytest -v
```

### Locally (requires Python 3.11+)

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest -v
```

> Tests use `mongomock-motor` — no running MongoDB instance is needed.

---

## Project Structure

```
.
├── app/
│   ├── main.py                 # FastAPI app, lifespan, health check
│   ├── config.py               # Settings from environment variables
│   ├── database/
│   │   ├── mongodb.py          # Motor client, connect/disconnect, indexes
│   │   └── repository.py       # Data-access layer (DB queries abstracted)
│   ├── models/
│   │   └── metadata.py         # Pydantic request/response/document models
│   ├── routes/
│   │   └── metadata.py         # POST & GET endpoint definitions
│   └── services/
│       ├── collector.py        # Shared httpx client with connection pooling
│       └── metadata_service.py # Business logic & background task orchestration
├── tests/
│   ├── conftest.py             # Shared fixtures (mock DB, async client)
│   ├── test_post_endpoint.py   # POST endpoint tests
│   ├── test_get_endpoint.py    # GET endpoint tests
│   └── test_collector.py       # Collector unit tests
├── docker-compose.yml          # API + MongoDB orchestration
├── Dockerfile                  # Python 3.11-slim container
├── requirements.txt            # Python dependencies
├── pyproject.toml              # Pytest configuration
└── README.md
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MONGODB_URL` | `mongodb://mongodb:27017` | MongoDB connection string |
| `MONGODB_DB_NAME` | `metadata_inventory` | Database name |
| `APP_HOST` | `0.0.0.0` | API host |
| `APP_PORT` | `8000` | API port |
| `REQUEST_TIMEOUT` | `15` | HTTP request timeout (seconds) |

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| Web Framework | FastAPI |
| Database | MongoDB 7 |
| Async DB Driver | Motor |
| HTTP Client | httpx |
| Validation | Pydantic v2 |
| Orchestration | Docker Compose |
| Testing | pytest + mongomock-motor |
