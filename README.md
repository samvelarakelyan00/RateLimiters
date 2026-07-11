# Rate Limiters in Python

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136+-green.svg)](https://fastapi.tiangolo.com)
[![Redis](https://img.shields.io/badge/Redis-8.0+-red.svg)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-28.0+-blue.svg)](https://docker.com)
[![pytest](https://img.shields.io/badge/pytest-9.0+-yellow.svg)](https://pytest.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-ready, distributed rate‑limiting library that implements **five core algorithms** with Redis back‑end, FastAPI integration, and comprehensive test suites. Designed for high‑concurrency environments, this project serves as both a practical reference and a turn‑key solution for protecting APIs, microservices, and web applications.

---

## 📖 Table of Contents

- [Overview](#overview)
- [Why Rate Limiting?](#why-rate-limiting)
- [Algorithms](#algorithms)
- [Technology Stack](#technology-stack)
- [Getting Started](#getting-started)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

This repository contains **five independent** implementations of the most widely used rate‑limiting algorithms. Each algorithm is:

- **Fully functional** – production‑ready code with atomic Redis operations.
- **Distributed by design** – scales horizontally using a shared Redis store.
- **Containerized** – Docker and Docker Compose for reproducible environments.
- **Thoroughly tested** – unit, integration, concurrency, and security tests.
- **Easy to integrate** – FastAPI dependency injection makes adoption a breeze.

Whether you are building an API gateway, securing microservices, or simply learning about traffic control, this project gives you a clean, well‑documented reference implementation for each strategy.

---

## 🔒 Why Rate Limiting?

Rate limiting is essential for any production system:

- **Protect Resources** – prevent denial of service and resource exhaustion.
- **Ensure Fairness** – provide equal access to all clients.
- **Control Costs** – manage API usage and infrastructure spending.
- **Maintain Availability** – absorb traffic spikes without degradation.
- **Enforce Compliance** – implement usage quotas and SLA guarantees.

---

## 🧠 Algorithms

This project implements **five** distinct algorithms, each with its own trade‑offs. You can choose the one that best fits your use case.

| # | Algorithm | Status | Description | Best For |
|---|-----------|--------|-------------|----------|
| 1 | **Leaky Bucket** | ✅ Complete | Processes requests at a constant rate, smoothing out bursts. Excess requests are queued or dropped. | Systems that need a stable, predictable request flow (e.g., batch processing, downstream protection). |
| 2 | **Token Bucket** | 🔄 Planned | Accumulates tokens at a fixed rate; each request consumes a token. Short bursts are allowed. | APIs where occasional bursts are acceptable (mobile apps, public endpoints). |
| 3 | **Fixed Window Counter** | 🔄 Planned | Counts requests in fixed, non‑overlapping time windows (e.g., per minute). Resets completely at each boundary. | Simple, low‑traffic use cases where precision is not critical. |
| 4 | **Sliding Window Log** | 🔄 Planned | Stores timestamps of every request; counts those within the last N seconds. Provides exact accuracy. | Financial systems, compliance‑critical applications that require perfect precision. |
| 5 | **Sliding Window Counter** | 🔄 Planned | Hybrid approach using weighted averages of current and previous windows. Balances accuracy and memory. | Production systems that need good accuracy without excessive memory usage. |

---

## 🛠 Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | 3.12+ |
| Web Framework | FastAPI | 0.136+ |
| Distributed Cache | Redis | 8.0+ |
| Package Manager | uv | Latest |
| Container Runtime | Docker, Docker Compose | 28.0+ |
| Test Framework | pytest, pytest-asyncio | 9.0+, 1.4+ |
| Test Containers | testcontainers | 4.14+ |
| Data Validation | Pydantic | 2.13+ |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12 or higher
- Docker and Docker Compose
- `uv` package manager (recommended)

### Clone the Repository

```bash
git clone git@github.com:samvelarakelyan00/RateLimiters.git
cd RateLimiters
```

### Choose an Algorithm

Each algorithm lives in its own sub‑directory (e.g., `LeakyBucket/`, `TokenBucket/`, etc.). Inside each folder, you will find:

- A dedicated `README.md` with detailed setup, usage instructions, and testing guides specific to that algorithm.
- A complete Dockerized environment with its own `Makefile`, `docker-compose.yml`, and test suites.

Navigate to the algorithm you are interested in and follow the instructions provided there.

```bash
cd LeakyBucket
# Then read the README.md inside
```

## General Workflow (applies to all algorithms)

1. Copy the environment file and adjust if needed:

```bash
cp .env.example .env
```
2. Install dependencies:

```bash
uv sync
```
3. Start the service (with or without tests) using the provided Makefile:

```bash
make up            # start without tests
make up-tests      # start and run all tests on startup
```
4. Run the test suite in isolation:

```bash
make test-with-docker
```
For detailed commands and options, refer to the `README.md` inside the specific algorithm folder.

---

## 📂 Project Structure 
Each algorithm is isolated in its own top‑level directory, making it easy to add new algorithms or maintain existing ones without interference.

| Directory | Description |
| --- | --- |
| `RateLimiters/` | Top-level directory containing all algorithms |
| ├── `LeakyBucket/` | Complete implementation of Leaky Bucket |
| │   ├── `app/` | Application source code |
| │   ├── `tests/` | Comprehensive test suite |
| │   ├── `docker-compose.yml` | Multi‑container orchestration |
| │   ├── `Makefile` | Automation commands |
| │   ├── `README.md` | Algorithm‑specific documentation |
| │   └── ... | Other configuration files |
| ├── `TokenBucket/` | (Planned) |
| ├── `FixedWindowCounter/` | (Planned) |
| ├── `SlidingWindowLog/` | (Planned) |
| └── `SlidingWindowCounter/` | (Planned) |
|	 `.gitignore`	|	Git ignore file|	|	`.README.md`	|	This file|	|	`.LICENSE`	|	License file|	 \\ \\ \\ \\ \\ \\ \\
the project structure table continues as needed...
details about contributing and coding standards follow below.
---

### details about coding standards follow below.
detailed standards include PEP 8 with Black formatting, type hints for all functions, docstrings for public APIs, and maintaining or improving existing test coverage.