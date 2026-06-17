# Running the ContextOS eval on Google Colab (free GPU)

Upload the local bundle (`contextos-eval-bundle.tar.gz`, contains code + corpus +
10k scenarios) — no re-scraping needed. The GPU makes the LLM-judged / multi-model
passes far faster than the M1.

## 0. New notebook + GPU
colab.research.google.com → New notebook → **Runtime ▸ Change runtime type ▸ T4 GPU ▸ Save**.

## 1. Confirm GPU
```python
!nvidia-smi
```

## 2. Install Ollama + start the server (GPU auto-detected)
The Ollama installer needs `zstd`, which Colab's image lacks — install it first.
```python
!apt-get -qq update && apt-get -qq install -y zstd
!curl -fsSL https://ollama.com/install.sh | sh
import subprocess, time
subprocess.Popen(["ollama", "serve"])
time.sleep(6)
!ollama --version
```

## 3. Pull the models you want to compare
```python
!ollama pull llama3.1:8b
!ollama pull mistral:7b
!ollama pull qwen2.5:7b
```

## 4. Upload the bundle and extract
```python
from google.colab import files
files.upload()                       # pick contextos-eval-bundle.tar.gz
!mkdir -p /content/ctx && tar xzf contextos-eval-bundle.tar.gz -C /content/ctx
!ls /content/ctx                     # should show: backend  contextos-evaluation
```

## 5. Python deps (Colab already has torch/transformers/pandas/scipy/matplotlib)
```python
!pip install -q sentence-transformers bert-score tiktoken rank-bm25 spacy networkx \
    pydantic pydantic-settings redis sqlalchemy tqdm
!python -m spacy download en_core_web_sm
```

## 6. (Recommended) Mount Drive so results survive disconnects
```python
from google.colab import drive
drive.mount('/content/drive')
!mkdir -p /content/drive/MyDrive/contextos_results
```

## 7. Run the cross-LLM judged comparison on the GPU
```python
%cd /content/ctx/contextos-evaluation
!python multi_model.py --limit 300 \
    --models llama3.1:8b,mistral:7b,qwen2.5:7b \
    --out-dir /content/drive/MyDrive/contextos_results/multimodel
```
Output: `comparison.md` + `comparison.json` + per-model `results_*.csv` in that
folder. Resumable — re-run the cell after a disconnect and it continues.

## 8. (Optional) Parallel shard of the full 10k while your Mac runs the other half
Mac runs `--shard 0/2`, Colab runs the other shard:
```python
!python runner.py --full --shard 1/2 --judge-subset 300 \
    --run-name colab_shard --out-dir /content/drive/MyDrive/contextos_results/colab_shard
```
Later merge: `python merge_results.py merged.csv mac/results.csv colab/results.csv`
then `python -m analysis.report <dir-with-merged-as-results.csv>`.

## Notes
- Free tier: ~12 h sessions, ~90 min idle disconnect, GPU not always granted. Keep
  the tab active; Drive + resumability protect progress.
- If an import errors, `pip install <package>` and re-run the cell.
- Token/cost reduction is identical across models (computed before the LLM); the
  comparison proves the *quality* claim holds across model families.
