#!/usr/bin/env bash
#SBATCH --job-name=pyx_toms
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1

set -euo pipefail
: "${PYEXPINT_RUN_DIR:?PYEXPINT_RUN_DIR not set}"
: "${PYEXPINT_CAMPAIGN_ID:?PYEXPINT_CAMPAIGN_ID not set}"
: "${PYEXPINT_PYTHON_MODULE:=python/3.11.4}"
: "${PYEXPINT_PYTHON:=python3}"
: "${PYEXPINT_TOMS_BLOCKS:=12}"

cd "$PYEXPINT_RUN_DIR"
module purge
module load "$PYEXPINT_PYTHON_MODULE"

export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONHASHSEED=0

export PYTHONPATH="$PYEXPINT_RUN_DIR/code/src${PYTHONPATH:+:$PYTHONPATH}"

{
  echo "campaign=$PYEXPINT_CAMPAIGN_ID"
  echo "job=$SLURM_JOB_ID"
  echo "node=$(hostname)"
  echo "date=$(date -Is)"
  echo "blocks=$PYEXPINT_TOMS_BLOCKS"
  echo "runtime=$PYEXPINT_RUNTIME"
  echo "source_hash=$PYEXPINT_SOURCE_MANIFEST_SHA256"
  module list 2>&1 || true
  "$PYEXPINT_PYTHON" -V
} | tee "$PYEXPINT_RUN_DIR/metadata/timing_job_header.txt"

# Minimum versions are supplied through PYEXPINT_MIN_* environment variables.
# check_runtime.py intentionally has a single interface shared by login, stage,
# and compute-node checks.
"$PYEXPINT_PYTHON" "$PYEXPINT_RUN_DIR/ops/python/check_runtime.py" \
  --source "$PYEXPINT_RUN_DIR/code/src" --smoke

srun --cpu-bind=cores "$PYEXPINT_PYTHON" \
  "$PYEXPINT_RUN_DIR/ops/python/toms_timing_balanced.py" \
  --outdir "$PYEXPINT_RUN_DIR/results/raw" \
  --metadata-dir "$PYEXPINT_RUN_DIR/metadata" \
  --blocks "$PYEXPINT_TOMS_BLOCKS"

"$PYEXPINT_PYTHON" "$PYEXPINT_RUN_DIR/ops/python/analyze_toms_timing.py" \
  --raw-dir "$PYEXPINT_RUN_DIR/results/raw" \
  --out-dir "$PYEXPINT_RUN_DIR/results/analysis"
