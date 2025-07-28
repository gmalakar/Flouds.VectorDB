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
    "host": "0.0.0.0",
    "port": 19680
  },
  "vectordb": {
    "endpoint": "http://localhost",
    "port": 19530,
    "username": "root",
    "password": "Milvus",
    "default_dimension": 384,
    "admin_role_name": "flouds_admin_role",
    "primary_key": "flouds_vector_id",
    "primary_key_data_type": "VARCHAR",
    "vector_field_name": "flouds_vector",
    "index_params": {
      "nlist": 1024,
      "metric_type": "COSINE",
      "index_type": "IVF_FLAT"
    }
  },
  "logging": {
    "folder": "logs",
    "app_log_file": "flouds.log"
  }
}
```

You can override any setting using environment variables or the `.env` file.

---

## Requirements

- Python 3.9+
- Milvus (standalone or cluster)
- See [app/requirements.txt](app/requirements.txt) for Python dependencies
- [Uvicorn](https://www.uvicorn.org/) for running the server

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
   - You can override any setting using environment variables or the `.env` file.

4. **Run the server:**
   ```sh
   python -m app.main
   ```
   Or with Uvicorn:
   ```sh
   uvicorn app.main:app --host 0.0.0.0 --port 19680 --reload
   ```

---

## Environment Variables and .env File

The `.env` file is used to configure environment variables for the container, including Milvus connection details, logging paths, and other settings.

**Example `.env`:**
```
FLOUDS_API_ENV=Production
FLOUDS_DEBUG_MODE=0
VECTORDB_USERNAME=admin
VECTORDB_PASSWORD=yourpassword
VECTORDB_ENDPOINT=localhost
VECTORDB_PORT=19530
FLOUDS_LOG_PATH=/var/log/flouds
VECTORDB_LOG_PATH=/your/host/logs
```

- The `.env` file allows you to configure the container without modifying code or the Dockerfile.
- It is used to set environment variables for Milvus connection, logging, debug mode, and other runtime options.
- You can keep different `.env` files for development, testing, and production.
- The container will read this file at startup and apply the settings automatically.

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
    "vector_dimension": 384
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

## Docker Usage

FloudsVectors.Py is available as a pre-built image on [Docker Hub](https://hub.docker.com/r/gmalakar/flouds-vector).

### 1. Pull the Docker image from Docker Hub

```sh
docker pull gmalakar/flouds-vector:latest
```

### 2. Prepare your `.env` file

See above for an example `.env` file.  
This file is essential for configuring your deployment.

### 3. Build the Docker image locally (optional)

You can build the image manually:

```sh
docker build -t floudsvectors-py .
```

Or use the provided PowerShell helper script:

```sh
./build-flouds-vector.ps1
```

### 4. Start the container

You can start the container manually:

```sh
docker run -p 19680:19680 \
  --env-file .env \
  -v /your/host/logs:/var/log/flouds \
  floudsvectors-py
```

Or use the provided helper scripts:

```sh
# Windows
./start-flouds-vectordb.ps1

# Linux/macOS
./start-flouds-vectordb.sh
```

- The default port is `19680` (see `appsettings.json` or override with `FLOUDS_PORT`).
- You can override any config value using environment variables or your `.env` file.
- The following Milvus connection variables are optional and can be set as needed:
  - `VECTORDB_USERNAME`
  - `VECTORDB_PASSWORD`
  - `VECTORDB_ENDPOINT`
  - `VECTORDB_PORT`

### 5. Mount persistent data or logs (optional)

If you want to persist logs or other data outside the container:

```sh
docker run -p 19680:19680 \
  -v $(pwd)/logs:/var/log/flouds \
  --env-file .env \
  floudsvectors-py
```

---

**Tips:**
- For development mode, set `FLOUDS_API_ENV=Development` and `FLOUDS_DEBUG_MODE=1` in your `.env`.
- You can use Docker Compose for more advanced setups (e.g., with Milvus as a service).
- Make sure Milvus is accessible from inside the container (networking).

---

## Logging

Logs are written to the `/var/log/flouds` directory inside the container and can be mapped to your host for persistence.  
Configure log file and level in [app/config/appsettings.json](app/config/appsettings.json) or via environment variables.

---

## Testing

Run all tests with:

```sh
pytest
```

---

## Useful Points

- All endpoints require a valid `tenant_code` in the request body and a `token` in the `Authorization` header (format: `user:password`).
- The `/vector_store/set_vector_store` endpoint must be called by a super user (admin/root).
- You can use environment variables or config files to manage credentials and server settings.
- The API is designed to be thread-safe and production-ready.
- The project uses [Uvicorn](https://www.uvicorn.org/) as the ASGI server.
- For development, use the `FLOUDS_API_ENV=Development` environment variable to load development-specific settings.

---

## License

Copyright (c) 2024 Goutam Malakar.  
All rights reserved.

---

*For more details, see the code and comments in each module.*

**Interested in collaborating? Please open an issue or pull request!**