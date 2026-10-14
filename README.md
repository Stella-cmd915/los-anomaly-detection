# Log Anomaly Detection

A pipeline that generates, ingests and preprocesses application logs and detects anomalies with several detectors, including evaluation and a dashboard.

## Tech stack
- Python · SQLite
- Docker

## Features
- Synthetic log generator and tail-based ingestion
- Preprocessing into SQLite
- Pluggable detectors (threshold, rare component, …)
- Evaluation: F1, latency per model (`results/`)
- Small demo pipeline in `demo/`

## Getting started
```bash
pip install -r requirements.txt
python src/log_generator.py
python src/preprocess_to_sqlite.py
python src/run_detection.py
python src/evaluate.py
```

---
Part of the **SIGMA LAB** project portfolio.
