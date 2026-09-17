#!/usr/bin/env bash
#SBATCH --job-name=pyexpint_toms
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1

set -euo pipefail

: "${PYEXPINT_RUN_DIR:?PYEXPINT_RUN_DIR not set}"
: "${PYEXPINT_CAMPAIGN_ID:?PYEXPINT_CAMPAIGN_ID not set}"
: "${PYEXPINT_RUNTIME:?PYEXPINT_RUNTIME not set}"
: "${PYEXPINT_PYTHON_MODULE:=python/3.11.4}"
: "${PYEXPINT_PYTHON:=python3}"
: "${PYEXPINT_MIN_PYTHON:=3.11}"
: "${PYEXPINT_MIN_NUMPY:=1.24}"
: "${PYEXPINT_MIN_SCIPY:=1.10}"

cd "$PYEXPINT_RUN_DIR"

module purge
module load "$PYEXPINT_PYTHON_MODULE"

export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONHASHSEED=0

N_LIST=(64 128 256)
TOL_LIST=(1e-5 1e-7)
BACKENDS=(kiops leja hybrid auto)

idx="${SLURM_ARRAY_TASK_ID}"
b=$(( idx % 4 ))
q=$(( (idx / 4) % 2 ))
n=$(( idx / 8 ))

N="${N_LIST[$n]}"
TOL="${TOL_LIST[$q]}"
BACKEND="${BACKENDS[$b]}"

echo "============================================================"
echo "PyEXPINT Picasso benchmark"
echo "campaign=$PYEXPINT_CAMPAIGN_ID"
echo "job=${SLURM_ARRAY_JOB_ID:-$SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
echo "node=$(hostname)"
echo "N_side=$N dimension=$((N*N)) rtol=$TOL backend=$BACKEND"
echo "runtime=$PYEXPINT_RUNTIME"
echo "date=$(date -Is)"
echo "============================================================"
module list 2>&1 || true
"$PYEXPINT_PYTHON" -V

if [[ "$PYEXPINT_RUNTIME" == "source" ]]; then
    export PYTHONPATH="$PYEXPINT_RUN_DIR/code/src${PYTHONPATH:+:$PYTHONPATH}"
    "$PYEXPINT_PYTHON" "$PYEXPINT_RUN_DIR/ops/python/check_runtime.py" \
      --source "$PYEXPINT_RUN_DIR/code/src" \
      --smoke
    CMD=("$PYEXPINT_PYTHON" "$PYEXPINT_RUN_DIR/ops/python/picasso_benchmark_case.py")
elif [[ "$PYEXPINT_RUNTIME" == "sif" ]]; then
    : "${PYEXPINT_SIF_PATH:?PYEXPINT_SIF_PATH not set for sif runtime}"
    CMD=("${PYEXPINT_APPTAINER:-apptainer}" exec --cleanenv
         --env "PYEXPINT_CAMPAIGN_ID=$PYEXPINT_CAMPAIGN_ID"
         --env "PYEXPINT_SOURCE_MANIFEST_SHA256=${PYEXPINT_SOURCE_MANIFEST_SHA256:-unknown}"
         --env "PYEXPINT_RUNTIME=sif"
         --env "OMP_NUM_THREADS=1"
         --env "MKL_NUM_THREADS=1"
         --env "OPENBLAS_NUM_THREADS=1"
         --env "NUMEXPR_NUM_THREADS=1"
         --bind "$PYEXPINT_RUN_DIR:/work"
         "$PYEXPINT_SIF_PATH"
         python /work/ops/python/picasso_benchmark_case.py)
else
    echo "Unknown PYEXPINT_RUNTIME=$PYEXPINT_RUNTIME" >&2
    exit 2
fi

srun --cpu-bind=cores "${CMD[@]}" \
    --n "$N" \
    --rtol "$TOL" \
    --backend "$BACKEND" \
    --repeats 7 \
    --outdir "$PYEXPINT_RUN_DIR/results/raw"
