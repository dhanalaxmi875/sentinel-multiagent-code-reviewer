#!/usr/bin/env python
# coding: utf-8

# # GPU Check

# In[ ]:


get_ipython().system('nvidia-smi')


# In[ ]:


import subprocess
result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
if result.returncode != 0:
    raise RuntimeError('No GPU found! This notebook requires a GPU (T4/P100).')
print('GPU detected successfully')


# # Install Ollama

# In[ ]:


# Install dependencies
get_ipython().system('apt-get update -qq')
get_ipython().system('apt-get install -y -qq zstd pciutils lshw curl')


# In[ ]:


# Install Ollama
get_ipython().system('curl -fsSL https://ollama.com/install.sh | sh')


# In[ ]:


# Set environment variables
import os
os.environ['OLLAMA_NUM_PARALLEL'] = '2'
print('OLLAMA_NUM_PARALLEL set to 2')


# In[ ]:


# Start Ollama server in background
import subprocess
import time
import requests

# Kill any existing ollama serve
get_ipython().system('pkill -f ollama || true')

# Start ollama serve
proc = subprocess.Popen(['ollama', 'serve'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print('Starting Ollama server...')

# Wait for server to be ready
for i in range(60):
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=2)
        if response.status_code == 200:
            print(f'Ollama server ready after {i+1} seconds')
            break
    except:
        time.sleep(1)
else:
    raise RuntimeError('Ollama server failed to start within 60 seconds')


# In[ ]:


# Pull qwen2.5-coder:14b model
get_ipython().system('ollama pull qwen2.5-coder:14b')


# In[ ]:


# List available models
get_ipython().system('ollama list')


# # Clone Repository and Install Dependencies

# In[ ]:


import os
os.chdir('/kaggle/working')

# Clone repository
get_ipython().system('git clone https://github.com/dhanalaxmi875/sentinel-multiagent-code-reviewer.git')
os.chdir('/kaggle/working/sentinel-multiagent-code-reviewer')


# In[ ]:


# Checkout the eval branch (main branch has eval_harness)
get_ipython().system('git checkout main')


# In[ ]:


# Verify eval_harness exists
get_ipython().system('ls eval_harness')


# In[ ]:


# Install dependencies
get_ipython().system('pip install -q -r requirements.txt')
get_ipython().system('pip install -q semgrep pandas matplotlib pytest')


# In[ ]:


# Install package in editable mode
get_ipython().system('pip install -q -e .')


# In[ ]:


# Print versions
import sys
print(f'Python version: {sys.version}')

import semgrep
print(f'Semgrep version: {semgrep.__version__}')


# # Sanity Checks

# In[ ]:


# Check model configuration
import subprocess
config_output = subprocess.check_output(['grep', 'MODEL', 'src/config.py'], text=True)
print('Model configuration:')
print(config_output)

if 'ollama' not in config_output.lower() and 'qwen' not in config_output.lower():
    raise RuntimeError('Model is not configured for Ollama/qwen! Check src/config.py')
print('Model configuration OK')


# In[ ]:


# Print run_eval.py help
get_ipython().system('python eval_harness/run_eval.py --help')


# In[ ]:


# Check manifest_subset.json exists and print sample counts
import json
from pathlib import Path

manifest_path = Path('eval_harness/manifest_subset.json')
if not manifest_path.exists():
    raise RuntimeError('manifest_subset.json not found! Run prepare_dataset.py first.')

with open(manifest_path) as f:
    manifest = json.load(f)

print(f'Total samples in subset: {len(manifest)}')

# Count per CWE and label
cwe_counts = {}
label_counts = {'vulnerable': 0, 'safe': 0}
for sample in manifest:
    cwe = sample['cwe']
    cwe_counts[cwe] = cwe_counts.get(cwe, 0) + 1
    label_counts[sample['label']] += 1

print('\nSample counts per CWE:')
for cwe, count in sorted(cwe_counts.items()):
    print(f'  {cwe}: {count}')

print(f'\nLabel counts: {label_counts}')


# # GPU Speed Check

# In[ ]:


# Run a short generation to verify GPU usage
get_ipython().system('ollama run qwen2.5-coder:14b --verbose \'print("hello world")\'')


# In[ ]:


# Check Ollama process status
get_ipython().system('ollama ps')


# In[ ]:


# Warn if running on CPU
import subprocess
ps_output = subprocess.check_output(['ollama', 'ps'], text=True)
if 'CPU' in ps_output or 'cpu' in ps_output:
    print('WARNING: Model appears to be running on CPU! This will be very slow.')
else:
    print('Model is running on GPU')


# # Timing Test

# In[ ]:


import time
import subprocess

# Run timing test with 3 samples
start_time = time.time()
result = subprocess.run(
    ['python', 'eval_harness/run_eval.py', 
     '--limit', '3', 
     '--runs', '1', 
     '--config', 'full',
     '--manifest', 'eval_harness/manifest_subset.json'],
    capture_output=True,
    text=True
)
elapsed = time.time() - start_time

print(f'Timing test completed in {elapsed:.2f} seconds')
print(f'Per-sample time: {elapsed/3:.2f} seconds')

# Load manifest to get total sample count
with open('eval_harness/manifest_subset.json') as f:
    manifest = json.load(f)
total_samples = len(manifest)

projected_total = (elapsed / 3) * total_samples
print(f'Projected total time for {total_samples} samples: {projected_total/60:.2f} minutes')


# # Main Evaluation Run

# In[ ]:


# Launch main evaluation in background with nohup
import subprocess
import os

log_path = '/kaggle/working/run.log'

# Kill any existing run
get_ipython().system("pkill -f 'run_eval.py' || true")

# Start evaluation in background
proc = subprocess.Popen(
    ['nohup', 'python', 'eval_harness/run_eval.py',
     '--config', 'full',
     '--runs', '1',
     '--manifest', 'eval_harness/manifest_subset.json',
     '--resume'],
    stdout=open(log_path, 'w'),
    stderr=subprocess.STDOUT
)

print(f'Evaluation started in background. PID: {proc.pid}')
print(f'Log file: {log_path}')


# # Monitor Progress (Re-runnable)

# In[ ]:


# Tail last 10 log lines
get_ipython().system('tail -n 10 /kaggle/working/run.log')


# In[ ]:


# Count completed samples
import os
from pathlib import Path

results_dir = Path('eval_harness/results/raw/full')
if results_dir.exists():
    # Find latest run directory
    run_dirs = sorted([d for d in results_dir.iterdir() if d.is_dir()])
    if run_dirs:
        latest_run = run_dirs[-1]
        completed = len(list(latest_run.glob('*.json')))
        print(f'Completed samples: {completed}')
    else:
        print('No run directories found yet')
else:
    print('Results directory not created yet')


# In[ ]:


# Create results.zip for download
get_ipython().system('cd /kaggle/working && zip -r results.zip sentinel-multiagent-code-reviewer/eval_harness/results')


# # Metrics and Visualization

# In[ ]:


# Run metrics computation
import subprocess
from pathlib import Path

# Find latest run directory
results_dir = Path('eval_harness/results/raw/full')
run_dirs = sorted([d for d in results_dir.iterdir() if d.is_dir()])
if not run_dirs:
    raise RuntimeError('No completed runs found. Wait for evaluation to complete.')

latest_run = run_dirs[-1]
print(f'Using results from: {latest_run}')

# Run metrics
get_ipython().system('python eval_harness/metrics.py --manifest eval_harness/manifest_subset.json --results-dir {latest_run}')


# In[ ]:


# Run ablation study (if multiple configs available)
# Note: This requires results from semgrep_only and llm_no_verifier configs
# !python eval_harness/ablation.py --manifest eval_harness/manifest_subset.json --results-base eval_harness/results/raw


# In[ ]:


# Load and display metrics
import json
from pathlib import Path

# Load metrics from previous run (save to file first)
metrics_output = Path('/kaggle/working/metrics.json')

# Re-run metrics with output
get_ipython().system('python eval_harness/metrics.py --manifest eval_harness/manifest_subset.json --results-dir {latest_run} --output {metrics_output}')


# In[ ]:


# Display per-CWE metrics
with open(metrics_output) as f:
    metrics = json.load(f)

print('=== Per-CWE Metrics ===')
print(f"{'CWE':<12} {'Prec':<6} {'Rec':<6} {'F1':<6} {'TP':<4} {'FP':<4} {'FN':<4} {'TN':<4} {'N':<4}")
for cwe in sorted(metrics['per_cwe'].keys()):
    m = metrics['per_cwe'][cwe]
    n = m['vulnerable_samples'] + m['safe_samples']
    print(f"{cwe:<12} {m['precision']:.3f}  {m['recall']:.3f}  {m['f1']:.3f}  {m['tp']:<4} {m['fp']:<4} {m['fn']:<4} {m['tn']:<4} {n:<4}")

print('\n=== Overall Metrics ===')
overall = metrics['overall']
print(f"Precision: {overall['precision']:.3f}")
print(f"Recall: {overall['recall']:.3f}")
print(f"F1: {overall['f1']:.3f}")
print(f"TP: {overall['tp']}, FP: {overall['fp']}, FN: {overall['fn']}, TN: {overall['tn']}")

print('\n=== Macro Average ===')
macro = metrics['macro_avg']
print(f"Precision: {macro['precision']:.3f}")
print(f"Recall: {macro['recall']:.3f}")
print(f"F1: {macro['f1']:.3f}")


# In[ ]:


# Generate confusion matrix
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

outputs_dir = Path('/kaggle/working/outputs')
outputs_dir.mkdir(exist_ok=True)

# Create confusion matrix from overall metrics
overall = metrics['overall']
cm = np.array([[overall['tp'], overall['fp']], [overall['fn'], overall['tn']]])

fig, ax = plt.subplots(figsize=(6, 5))
im = ax.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
ax.figure.colorbar(im, ax=ax)

ax.set(xticks=[0, 1], yticks=[0, 1],
       xticklabels=['Positive', 'Negative'],
       yticklabels=['Positive', 'Negative'],
       ylabel='True label',
       xlabel='Predicted label',
       title='Confusion Matrix')

# Add text annotations
thresh = cm.max() / 2.
for i in range(2):
    for j in range(2):
        ax.text(j, i, format(cm[i, j], 'd'),
                ha='center', va='center',
                color='white' if cm[i, j] > thresh else 'black')

plt.tight_layout()
plt.savefig(outputs_dir / 'confusion_matrix.png', dpi=150)
plt.show()

print('Confusion matrix saved to outputs/confusion_matrix.png')


# In[ ]:


# Generate F1 by CWE chart
fig, ax = plt.subplots(figsize=(10, 6))

cwes = sorted(metrics['per_cwe'].keys())
f1_scores = [metrics['per_cwe'][cwe]['f1'] for cwe in cwes]
sample_counts = [metrics['per_cwe'][cwe]['vulnerable_samples'] + metrics['per_cwe'][cwe]['safe_samples'] for cwe in cwes]

x_pos = np.arange(len(cwes))
bars = ax.bar(x_pos, f1_scores, alpha=0.7)

ax.set_xlabel('CWE')
ax.set_ylabel('F1 Score')
ax.set_title('F1 Score by CWE')
ax.set_xticks(x_pos)
ax.set_xticklabels(cwes, rotation=45, ha='right')
ax.set_ylim([0, 1.0])
ax.axhline(y=0.5, color='r', linestyle='--', alpha=0.5, label='F1=0.5')
ax.legend()

# Add sample count as text on bars
for bar, count in zip(bars, sample_counts):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'n={count}',
            ha='center', va='bottom', fontsize=8)

plt.tight_layout()
plt.savefig(outputs_dir / 'f1_by_cwe.png', dpi=150)
plt.show()

print('F1 by CWE chart saved to outputs/f1_by_cwe.png')


# In[ ]:


# Save CSV outputs
import csv

# Per-CWE CSV
with open(outputs_dir / 'summary_per_cwe.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['CWE', 'Precision', 'Recall', 'F1', 'TP', 'FP', 'FN', 'TN', 'Samples'])
    for cwe in sorted(metrics['per_cwe'].keys()):
        m = metrics['per_cwe'][cwe]
        n = m['vulnerable_samples'] + m['safe_samples']
        writer.writerow([cwe, f"{m['precision']:.3f}", f"{m['recall']:.3f}", f"{m['f1']:.3f}",
                         m['tp'], m['fp'], m['fn'], m['tn'], n])

# Overall CSV
with open(outputs_dir / 'summary_overall.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Metric', 'Value'])
    overall = metrics['overall']
    writer.writerow(['Precision', f"{overall['precision']:.3f}"])
    writer.writerow(['Recall', f"{overall['recall']:.3f}"])
    writer.writerow(['F1', f"{overall['f1']:.3f}"])
    writer.writerow(['TP', overall['tp']])
    writer.writerow(['FP', overall['fp']])
    writer.writerow(['FN', overall['fn']])
    writer.writerow(['TN', overall['tn']])
    macro = metrics['macro_avg']
    writer.writerow(['Macro Precision', f"{macro['precision']:.3f}"])
    writer.writerow(['Macro Recall', f"{macro['recall']:.3f}"])
    writer.writerow(['Macro F1', f"{macro['f1']:.3f}"])

print('CSV files saved to outputs/')


# In[ ]:


# Create final results.zip
get_ipython().system('cd /kaggle/working && zip -r final_results.zip outputs sentinel-multiagent-code-reviewer/eval_harness/results')
print('Final results.zip created with outputs and results')

