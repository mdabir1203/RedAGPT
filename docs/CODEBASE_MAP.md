# RedAGPT Codebase Map

This document provides a high-level tour of the repository structure and the purpose of each major module. Use it as the first stop when you need to understand where functionality lives or where a change should be made.

## Top-level layout

| Path | Description |
| ---- | ----------- |
| `chatbot.py` | Streamlit UI that renders the landing page, payment CTA, and audit console. Talks to `LoginChecker` for orchestrating scans and `tools/payments.py` for Stripe checkout. |
| `main.py` | CLI entry point for running automated login audits from the terminal. Provides log tailing for long-running checks. |
| `requirements.txt` | Fully pinned Python dependency set used in production and CI. Generated from `unpinned_requirements.txt`. |
| `unpinned_requirements.txt` | Human-maintained list of dependency constraints. Run `make update-requirements-txt` to regenerate the pinned lockfile. |
| `audio/` | Static audio assets referenced by the Streamlit sidebar. |
| `imgs/` | Static images for the landing page and documentation. |
| `tools/` | Backend utilities (login automation, Stripe helpers, logging adapters, and supporting datasets). |
| `tests/` | Documentation for the (currently manual) testing flow. |
| `docs/` | Architectural and contributor documentation (this file). |

## `tools/` package

| Path | Description |
| ---- | ----------- |
| `tools/__init__.py` | Marks the `tools` directory as a package. |
| `tools/login_checker.py` | Core automation logic. Builds an AutoGPT agent with LangChain, initialises vector-store memory (Redis with FAISS fallback), and executes hydra/selenium task chains. Writes structured logs and summaries to disk. |
| `tools/payments.py` | Stripe checkout helper that validates configuration and creates hosted sessions. Raises `StripeCheckoutError` for UI-friendly error handling. |
| `tools/stream_to_logger.py` | Lightweight file-like adapter that redirects stdout into the Python logging framework. |
| `tools/data/` | Wordlists used by the hydra brute-force command. |
| `tools/logs/` | Runtime log output and generated security summaries. Created on demand. |

## Front-end flow (`chatbot.py`)

1. Loads environment variables via `python-dotenv`.
2. Configures the Streamlit page (title, icon, background, sidebar audio).
3. Provides navigation between:
   * **Overview** – marketing landing page, feature grid, Stripe CTA.
   * **Security audit** – validated form for running an automated login test.
4. Uses `LoginChecker` to execute audits and renders the resulting report/logs to the user.

## CLI flow (`main.py`)

1. Presents a minimal TUI for selecting the login checker.
2. Validates inputs (local vs remote, URL syntax).
3. Spawns `LoginChecker.run` in a background process, tailing the generated log file.
4. Prints the agent’s final response and location of generated artefacts.

## Operational dependencies

* **Environment variables** – configure API keys (`OPENAI_API_KEY`, `STRIPE_*`, etc.) via `.env`.
* **Python runtime** – Python 3.11 is required for the latest LangChain and OpenAI client releases.
* **Vector store** – optional Redis instance referenced by `REDIS_URL`; falls back to in-process FAISS vectors when unavailable.
* **External tooling** – assumes `hydra` is installed on the host for credential brute forcing.

## Regeneration recipes

* Refresh pinned dependencies: `make update-requirements-txt`
* Create a fresh virtual environment + install deps: `make virtualenv`
* Launch the Streamlit UI: `streamlit run chatbot.py`
* Run the CLI audit: `python main.py`

