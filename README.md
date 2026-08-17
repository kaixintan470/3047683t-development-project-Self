# MedAI Clinical Reasoning System

## Purpose

This local dissertation prototype evaluates an evidence-grounded clinical reasoning pipeline. It is a research system, not a medical device, and its output must not be used as clinical advice.

## Architecture

```text
Structured Interview
→ Query Generation
→ MedCPT + FAISS Guideline Retrieval
→ Independent Qwen2.5-3B / Gemma2-2B Reasoning
→ Binary Sufficiency and Dual AND Gate
→ KAS / LCS
→ DCS
→ Approved or Neutral Follow-up Loop
```

The Django interface only collects and displays data. Clinical routing and validation remain in `core/pipeline.py` and the modules it calls.

## Conda environment

The validated environment uses Python 3.11 and is named `medical_ai`.

```powershell
conda create -n medical_ai python=3.11 -y
conda activate medical_ai
python -m pip install -r requirements.txt
```

The pinned dependencies provide Django, PDF extraction, Ollama client access, PyTorch, Transformers, and FAISS CPU.

## Ollama models

Install and start Ollama, then make both configured models available:

```powershell
ollama pull qwen2.5:3b
ollama pull gemma2:2b
ollama list
```

The application expects Ollama at `http://127.0.0.1:11434`. It uses Qwen for query generation and local judging as well as SLM-A; Gemma is the independent SLM-B. No third model family is required.

## Guideline corpus and index

Place the 10 controlled official guideline PDFs in `corpus/guidelines/` using the filenames defined for Phase 3. The `corpus/` directory is ignored by Git, so each installation must supply its own licensed/downloaded local documents.

The first real retrieval run preprocesses the PDFs, downloads the MedCPT Query and Article encoders into the ignored `models/` cache, and creates an ignored FAISS index under `corpus/index/`. To build it explicitly:

```powershell
python -c "from core.adapters.medcpt_faiss import MedCPTFAISS; MedCPTFAISS('corpus/guidelines', 'corpus/index').build()"
```

## Run Django

```powershell
conda activate medical_ai
python manage.py migrate
python manage.py ensure_test_account
python manage.py check
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

The deterministic local prototype account created by the setup command is:

```text
Email: admin@example.com
Password: 123456
```

Passwords are stored through Django's built-in password hashing. The SQLite database is local runtime data and remains ignored by Git.

## Tests

```powershell
python manage.py check
python -m unittest discover -s tests -v
python manage.py test portal
python -m unittest tests.test_real_services -v
```

The real-service suite requires Ollama, both local models, the controlled corpus, MedCPT model downloads, and sufficient local memory. Its first run is substantially slower while the index is built.

## Evaluation

`test_data/cases.json` contains only the tiny representative dataset used to verify the Chapter 4 runner. Run a real evaluation with:

```powershell
python -c "from evaluation.runner import run_evaluation; from core.pipeline import create_real_pipeline; run_evaluation('test_data/cases.json', 'evaluation_results/run.json', lambda patient: create_real_pipeline(patient, lambda question: input(question + ' ')))"
```

Regenerate metrics from a saved run without rerunning models:

```powershell
python -c "from evaluation.metrics import regenerate_metrics; print(regenerate_metrics('evaluation_results/run.json'))"
```

## Known limitations

- This is a local research prototype and has not been clinically validated.
- Small local language models can produce malformed or variable structured output.
- The controlled corpus covers a limited urological and sexual-health guideline set.
- CPU-only MedCPT indexing and Ollama inference can be slow.
- Chapter 4 parameter sweeps and a larger expert-reviewed evaluation dataset are not included.
