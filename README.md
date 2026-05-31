# Bug-Fixing Agent (CS767 Assignment 2)

A ReAct + Reflexion agent that fixes buggy Python programs from the QuixBugs
benchmark using a local Ollama model. Built with LangGraph + Chroma + Streamlit.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Install Ollama from https://ollama.com then:
ollama pull qwen2.5-coder:7b
ollama pull nomic-embed-text
```

## Run

```bash
streamlit run app.py
```

## Evaluate

```bash
python eval/run_eval.py --mode headline
python eval/run_eval.py --mode ablation
python eval/run_eval.py --mode accumulation
```

## Demo

See `demo/demo.md` for the 2-minute video link.

## Architecture

![architecture](docs/architecture.png)

See `docs/report.md` for the full write-up.

## Setup

Prerequisites: Python 3.11+, [Ollama](https://ollama.com).

```bash
git clone <repo-url>
cd bugfix-agent
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

ollama pull qwen2.5-coder:7b
ollama pull nomic-embed-text

# vendor the QuixBugs data
python scripts/fetch_quixbugs.py