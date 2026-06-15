# Rate Limiters in Python

[![Python Version](https://shields.io)](https://python.org)
[![Package Manager](https://shields.io)](https://github.com)

A comprehensive Python implementation of 5 core rate-limiting algorithms, complete with thorough unit test suites. This repository serves as an educational and practical reference for understanding network traffic control and rate-limiting strategies.

## 📌 Table of Contents
- [Algorithms](#-algorithms)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [Running Tests](#-running-tests)
- [Project Structure](#-project-structure)

## 🧠 Algorithms

This project implements and tests the following 5 rate-limiting algorithms:

1. **Leaky Bucket** 
   - 🔄 *Status: Under Construction*
   - 📝 Description: Smooths out bursts of traffic by releasing requests at a constant, predictable rate.
2. **Token Bucket**
   - ⏳ *Status: Planned*
   - 📝 Description: Allows for sudden bursts of traffic by accumulating tokens up to a specified maximum capacity.
3. **Fixed Window Counter**
   - ⏳ *Status: Planned*
   - 📝 Description: Simple algorithm that tracks request counts within strictly bounded, non-overlapping time windows.
4. **Sliding Window Log**
   - ⏳ *Status: Planned*
   - 📝 Description: Highly accurate algorithm that stores timestamps for every single request to eliminate boundary bursts.
5. **Sliding Window Counter**
   - ⏳ *Status: Planned*
   - 📝 Description: A memory-efficient hybrid approach that uses a weighted average of the current and previous window counts.

## 🛠 Tech Stack

- **Python 3.12+** — core runtime environment.
- **uv** — ultra-fast Python package resolver and project manager.
- **FastAPI** — Fake Auth Service for testing rate limiter.
- **Pydantic** — For input/output models, data structures
- **Docker, Docker Compose** — For containerization
- **pytest** — robust framework used for writing and running the test suites.

## ⚡ Quick Start

This project utilizes `uv` for seamless runtime virtualization. You do not need to manually configure environment files or source the `.venv` directory.

1. Clone the repository:
   ```bash
   git clone https://github.com<your-username>/RateLimiters.git
   cd RateLimiters
   ```

2. Resolve environments and install dependencies:
   ```bash
   uv sync
   ```

3. Spin up the application locally:
   ```bash
   uv run fastapi dev
   ```

## 🧪 Running Tests

The test suite is partitioned to validate isolated pieces of code as well as extreme load scenarios. Run tests inside the target strategy workspace.

Run tests of a rate limiter: (example)
```bash
cd /LeakyBucket/tests/unit/
python3 test_rate_limiter.py
```

#### Or just configure your environment (PyCharm, VS Code...) for running all tests at once

## 📂 Project Structure

```text
RateLimiters/
├── .venv/                      # Virtual environment (managed by uv)
├── LeakyBucket/                # Dedicated Leaky Bucket module
│   ├── app/                    # Application source code
│   │   ├── api/                # API Routing and Layering
│   │   │   ├── dependencies/   # FastAPI Dependency Injection
│   │   │   │   ├── auth_dep.py
│   │   │   │   └── auth_rate_limiters.py
│   │   │   └── v1/             # API Version 1 Namespace
│   │   │       ├── endpoints/  # Route handlers
│   │   │       └── __init__.py
│   │   ├── core/               # App configuration and system-level security
│   │   │   ├── security/       # Core Rate Limiting engines
│   │   │   │   ├── rate_limit_profiles.py
│   │   │   │   ├── rate_limit_service.py
│   │   │   │   └── rate_limiter.py
│   │   │   └── settings/       # Global configuration states
│   │   │       └── __init__.py
│   │   ├── schemas/            # Pydantic data serialization schemas
│   │   │   └── user_schemas.py
│   │   ├── services/           # Business logic isolation layer
│   │   │   └── auth.py
│   │   └── main.py             # Application entry point
│   ├── tests/                  # Multi-layer testing matrices
│   │   ├── component/          # Component isolation tests
│   │   ├── concurrency/        # Race condition & multi-thread stress verification
│   │   ├── end-to-end/         # Complete E2E flow assertions
│   │   ├── integration/        # Module-to-module communication checks
│   │   ├── load/               # Heavy-traffic simulation tests
│   │   ├── security-abuse/     # Exploitation and perimeter evasion simulation
│   │   └── unit/               # Granular function-level tests
│   └── Dockerfile              # Multi-stage production container blueprint
├── .gitignore
├── pyproject.toml             # Global dependency manifest
├── uv.lock                    # Cryptographically locked dependency state
└── README.md                  # System overview documentation
```