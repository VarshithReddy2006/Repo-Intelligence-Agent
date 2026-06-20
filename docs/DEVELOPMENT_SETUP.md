# 🛠️ Development Setup & Contributor Guide

Welcome to the **Repo Intelligence Agent** contributor guide! This document outlines the steps required to configure your local development environment, start backend and frontend services, run the test suites, and adhere to our development workflows.

---

## 📋 Prerequisites

Before setting up the project, ensure you have the following installed:

- **Python:** Version 3.10, 3.11, or 3.12. (Active unit tests are validated against Python 3.12).
- **Node.js:** Version 18 or newer (LTS recommended).
- **Git:** Command-line utility for source control operations.
- **NVIDIA NIM API Key:** Required for DeepSeek V4 Flash inference. You can acquire a free-tier key at [build.nvidia.com](https://build.nvidia.com).
- **Disk Space:** At least 2 GB of free disk space is required to store local Hugging Face model cache structures (specifically for `BAAI/bge-small-en-v1.5` embeddings).

---

## 🔧 Backend Ingestion & API Setup

### 1. Clone the Project
Clone the repository and enter the project directory:
```bash
git clone https://github.com/your-username/Repo-Intelligence-Agent.git
cd Repo-Intelligence-Agent
```

### 2. Configure Python Virtual Environment
Isolate Python dependencies to prevent version collisions.

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

**On macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
Install all backend packages:
```bash
pip install -r requirements.txt
```

### 4. Configure Environmental Variables
Copy the environmental template into an active `.env` configuration:

```bash
cp .env.example .env
```

Open the `.env` file and insert your API key and settings:
```env
DEEPSEEK_API_KEY=nvapi-your-nvidia-nim-api-key-here
GITHUB_TOKEN=ghp_your-github-personal-access-token-here # Optional: raises clone rate limits
CHROMA_DB_PATH=data/chroma_db
LLM_PROVIDER=deepseek
DEEPSEEK_MODEL=deepseek-ai/deepseek-v4-flash
DEEPSEEK_BASE_URL=https://integrate.api.nvidia.com/v1
```

### 5. Launch the Backend Server
Start the Uvicorn development server. The project defaults to port **8001** to prevent conflicts with standard developer systems:
```bash
# Recommended: Starts uvicorn with watch filters enabled in backend/main.py
python backend/main.py

# Alternative: direct uvicorn execution specifying port 8001
python -m uvicorn backend.api:app --host 127.0.0.1 --port 8001 --reload
```
- The interactive OpenAPI documentation will be served at [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs).
- The raw JSON schema is available at [http://127.0.0.1:8001/openapi.json](http://127.0.0.1:8001/openapi.json).

---

## 🎨 Astro Dashboard Setup

The user interface is an Astro 4 static-site framework embedding interactive React client components.

### 1. Navigate and Install Packages
Navigate to the frontend directory and install dependencies:
```bash
cd frontend
npm install
```

### 2. Configure Frontend Environment
Ensure the frontend matches backend routing by checking `frontend/.env` (it defaults to `PUBLIC_API_URL=http://127.0.0.1:8001`).

### 3. Run Astro Development Server
Start the development server:
```bash
npm run dev
```
- Open [http://localhost:4321](http://localhost:4321) in your browser to view the interface.

---

## 🧪 Testing Guidelines

We use `pytest` for backend unit testing. All tests are located inside the `tests/` directory.

### Running the Test Suite
Activate your virtual environment and run the test suite:
```bash
pytest tests/ -v
```

> [!CAUTION]
> Avoid running raw `pytest` in the root folder without a target path. Doing so causes pytest to traverse `data/cloned_repos/` (which contains cloned codebases like FastAPI), resulting in import errors and test collection failures. Always run `pytest tests/`.

---

## 💅 Styling & Formatting Standards

- **Backend Linting:** We use `Ruff` for linting and code formatting. Run it from your virtual environment before submitting changes:
  ```bash
  ruff check .
  ruff format .
  ```
- **Frontend CSS:** The UI uses Vanilla CSS structured inside Astro templates. Tailwind CSS configurations (`tailwind.config.mjs`) are loaded but custom responsive rules are written manually to maintain control over visual transitions.
- **Documentation:** Maintain markdown files with clean lists, relative links, and valid Mermaid diagram syntax.
