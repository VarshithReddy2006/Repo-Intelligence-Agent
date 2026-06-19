# Development Setup & Contributor Guide

Welcome to the **Repo Intelligence Agent** project! This document outlines the steps required to set up the backend and frontend for local development, run the test suites, and contribute to the codebase.

---

## 📋 Prerequisites

Before setting up the project locally, ensure you have the following installed:

- **Python 3.10 or 3.11** (Note: Python 3.12 is supported, but 3.10/3.11 is recommended for library stability).
- **Node.js v18 or newer** (for the Astro & React frontend).
- **Git** command-line utility.
- An **NVIDIA NIM API key** (used for DeepSeek V4 Flash inference calls). You can acquire one free of charge at [build.nvidia.com](https://build.nvidia.com).
- At least **2 GB of free disk space** for BGE embedding model downloads.

---

## 🔧 Installation & Setup

### 1. Clone the Repository
Clone the repository to your local workspace and navigate to the project directory:
```bash
git clone https://github.com/your-username/Repo-Intelligence-Agent.git
cd Repo-Intelligence-Agent
```

### 2. Backend Setup
Set up a Python virtual environment to isolate the project dependencies:

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

Install all required Python dependencies:
```bash
pip install -r requirements.txt
```

### 3. Backend Environment Configuration
Create a local `.env` file in the root directory by copying the example template:
```bash
cp .env.example .env
```

Open `.env` and fill in the required environment variables:
```env
DEEPSEEK_API_KEY=nvapi-your-nvidia-nim-api-key-here
GITHUB_TOKEN=ghp_your-github-personal-access-token-here
CHROMA_DB_PATH=data/chroma_db
LLM_PROVIDER=deepseek
DEEPSEEK_MODEL=deepseek-ai/deepseek-v4-flash
```

> [!TIP]
> The `GITHUB_TOKEN` is optional but highly recommended to raise GitHub API rate limits when cloning repositories.

### 4. Start the Backend API Server
Launch the FastAPI backend server using Uvicorn with hot-reload enabled:
```bash
python -m uvicorn backend.api:app --host 127.0.0.1 --port 8000 --reload
```
The backend API documentation will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## 🎨 Frontend Setup

The frontend application is built using Astro 4 and React components.

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install the package dependencies:
   ```bash
   npm install
   ```
3. Start the Astro local development server:
   ```bash
   npm run dev
   ```
4. Access the frontend dashboard at [http://localhost:4321](http://localhost:4321).

---

## 🧪 Testing Guidelines

We utilize `pytest` to verify backend business logic, retrieval services, and AST parsers.

### Running Backend Tests
Ensure your virtual environment is active, then run:
```bash
pytest tests/ -v
```

### Writing New Tests
- Place your test files under the `tests/` directory.
- Name files with the prefix `test_` (e.g., `test_my_feature.py`).
- Implement descriptive assertions and leverage mock adapters for network calls to avoid hitting remote API quotas during unit runs.

---

## 🤝 Contribution Workflow

1. **Fork** the repository and create your feature branch:
   ```bash
   git checkout -b feature/amazing-new-feature
   ```
2. Make your modifications, adhering to clean coding standards and documenting changes.
3. Verify changes with `pytest`.
4. Push your branch to GitHub:
   ```bash
   git push origin feature/amazing-new-feature
   ```
5. Open a **Pull Request** detailing your changes.
