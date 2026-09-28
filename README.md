# FastAPI Starter

A modular, clean FastAPI project structure with a single health check endpoint.

## Project Structure

```text
codetest/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application initialization
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py               # Pydantic Settings & environment configurations
│   └── api/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           ├── router.py           # API v1 router collector
│           └── endpoints/
│               ├── __init__.py
│               └── health.py       # GET /api/v1/health endpoint
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Getting Started

### 1. Create and Activate a Virtual Environment

```bash
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS
python -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Development Server

```bash
uvicorn app.main:app --reload
```

The server will start at `http://127.0.0.1:8000`.

## API Documentation & Endpoints

- **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check Endpoint**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)
