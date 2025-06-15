# FloudsVectors.Py

FloudsVectors.Py is a FastAPI-based service for managing multi-tenant vector stores using Milvus as the backend. It provides APIs for creating tenants, managing users, and storing and searching vector embeddings with metadata.

**This is a new project and we are looking for collaborators!**  
If you are interested in vector databases, FastAPI, or scalable backend systems, your contributions are welcome.

---

## Features

- Multi-tenant vector store management
- User and role management for each tenant
- Insert and search vector embeddings with metadata
- RESTful API endpoints (FastAPI)
- Milvus vector database backend
- Configurable via JSON and environment variables
- Thread-safe and production-ready

---

## Project Structure

```
app/
  config/           # Configuration and settings
  milvus/           # Milvus integration and vector store logic
  models/           # Pydantic models for requests and responses
  modules/          # Utility modules (e.g., thread-safe dict)
  routers/          # FastAPI routers for API endpoints
  services/         # Service layer for business logic
  utils/            # Utility functions
  main.py           # FastAPI app entry point
  logger.py         # Logging setup
  app_init.py       # App settings loader
  requirements.txt  # Python dependencies
tests/              # Pytest-based unit tests
```

---

## Configuration

### appsettings.json

All main configuration is handled via `app/config/appsettings.json`.  
You can set server type, host, port, logging, and Milvus options.

**Example:**
```json
{
  "app": {
    "name": "FloudsVectors.Py"
  },
  "server": {
    "type": "hypercorn",
    "host": "0.0.0.0",
    "port": 19680,
    "reload": true,
    "workers": 4
  },
  "vectordb": {
    "protocol": "http",
    "endpoint": "http://localhost",
    "port": 19530,
    "username": "root",
    "password": "Milvus",
    "default_dimension": 256,
    "admin_role_name": "flouds_admin_role"
  },
  "logging": {
    "folder": "logs",
    "app_log_file": "flouds.log"
  }
}
```

You can override any setting using environment variables (see below).

---

## Requirements

- Python 3.9+
- Milvus (standalone or cluster)
- See [app/requirements.txt](app/requirements.txt) for Python dependencies
- [Uvicorn](https://www.uvicorn.org/) or [Hypercorn](https://pgjones.gitlab.io/hypercorn/) for running the server

---

## Setup

1. **Clone the repository:**
   ```sh
   git clone https://github.com/your-org/FloudsVector.Py.git
   cd FloudsVector.Py
   ```

2. **Install dependencies:**
   ```sh
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r app/requirements.txt
   ```

3. **Configure settings:**
   - Edit [app/config/appsettings.json](app/config/appsettings.json) for your Milvus and server settings.
   - Optionally, create environment-specific overrides such as [app/config/appsettings.development.json](app/config/appsettings.development.json).
   - You can override any setting using environment variables.

4. **Run the server:**
   ```sh
   python -m app.main
   ```
   Or with Uvicorn:
   ```sh
   uvicorn app.main:app --host 0.0.0.0 --port 19680 --reload
   ```

---

## Environment Variables

- `FLOUDS_API_ENV` — Set to `Development`, `Production`, etc. to load environment-specific config.
- `VECTORDB_USERNAME` — Milvus admin username (overrides config).
- `VECTORDB_PASSWORD` — Milvus admin password (overrides config).
- `FLOUDS_PORT`, `FLOUDS_HOST`, `FLOUDS_SERVER_TYPE` — Override server settings.

---

## API Endpoints

### Vector Store

- `POST /vector_store/set_vector_store`  
  Create or retrieve a vector store for a tenant.

- `POST /vector_store/insert`  
  Insert embedded vectors into a tenant's vector store.

- `POST /vector_store/search`  
  Search for embedded vectors in a tenant's vector store.

### User Management

- `POST /vector_store_users/set`  
  Create or set a user for a tenant.

---

## How to Call the API

You can use `curl`, `httpie`, or any HTTP client to call the endpoints.  
Below are some example requests:

### 1. Create or Get a Vector Store

```sh
curl -X POST http://localhost:19680/vector_store/set_vector_store \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin:admin_password" \
  -d '{
    "tenant_code": "mytenant",
    "vector_dimension": 256
  }'
```

### 2. Insert Embedded Vectors

```sh
curl -X POST http://localhost:19680/vector_store/insert \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer user:password" \
  -d '{
    "tenant_code": "mytenant",
    "data": [
      {
        "chunk": "This is a test.",
        "model": "all-MiniLM-L6-v2",
        "vector": [0.1, 0.2, 0.3, ...]
      }
    ]
  }'
```

### 3. Search Embedded Vectors

```sh
curl -X POST http://localhost:19680/vector_store/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer user:password" \
  -d '{
    "tenant_code": "mytenant",
    "model": "all-MiniLM-L6-v2",
    "limit": 10,
    "offset": 0,
    "nprobe": 10,
    "round_decimal": -1,
    "score_threshold": 0.8,
    "metric_type": "COSINE",
    "vector": [0.1, 0.2, 0.3, ...]
  }'
```

### 4. Create or Set a User

```sh
curl -X POST http://localhost:19680/vector_store_users/set \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer admin:admin_password" \
  -d '{
    "tenant_code": "mytenant"
  }'
```

---

## Useful Points

- All endpoints require a valid `tenant_code` in the request body and a `token` in the `Authorization` header (format: `user:password`).
- The `/vector_store/set_vector_store` endpoint must be called by a super user (admin/root).
- You can use environment variables or config files to manage credentials and server settings.
- Logs are written to the `logs/` directory and to the console.
- The API is designed to be thread-safe and production-ready.
- You can run tests using `pytest` in the project root.
- The project supports both [Uvicorn](https://www.uvicorn.org/) and [Hypercorn](https://pgjones.gitlab.io/hypercorn/) as ASGI servers.
- For development, use the `FLOUDS_API_ENV=Development` environment variable to load development-specific settings.

---

## Testing

Run all tests with:

```sh
pytest
```

---

## Logging

Logs are written to the `logs/` directory and to the console.  
Configure log file and level in [app/config/appsettings.json](app/config/appsettings.json) or via environment variables.

---

## Docker Usage

You can run FloudsVectors.Py as a Docker container for easy deployment.

### 1. Build the Docker image

```sh
docker build -t floudsvectors-py .
```

### 2. Run the container

```sh
docker run -p 19680:19680 \
  -e FLOUDS_API_ENV=Production \
  -e FLOUDS_DEBUG_MODE=0 \
  -e FLOUDS_PORT=19680 \
  floudsvectors-py
```

- The default port is `19680` (see `appsettings.json` or override with `FLOUDS_PORT`).
- You can override any config value using environment variables.

### 3. Mount persistent data or logs (optional)

If you want to persist logs or other data outside the container:

```sh
docker run -p 19680:19680 \
  -v $(pwd)/logs:/flouds-py/logs \
  -e FLOUDS_API_ENV=Production \
  floudsvectors-py
```

---

**Tips:**
- For development mode, set `FLOUDS_API_ENV=Development` and `FLOUDS_DEBUG_MODE=1`.
- You can use Docker Compose for more advanced setups (e.g., with Milvus as a service).
- Make sure Milvus is accessible from inside the container (networking).

---

## License

Copyright (c) 2024 Goutam Malakar.  
All rights reserved.

---

*For more details, see the code and comments in each module.*

**Interested in collaborating? Please open an issue or pull request!**