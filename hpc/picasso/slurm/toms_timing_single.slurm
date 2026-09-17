#!/usr/bin/env bash
#SBATCH --job-name=pyx_toms
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1

set +e
set +u
set +o pipefail

main() {
    if [[ -z "${PYEXPINT_RUN_DIR:-}" ]]; then
        echo "ERROR: PYEXPINT_RUN_DIR not set" >&2
        return 2
    fi

    if [[ -z "${PYEXPINT_CAMPAIGN_ID:-}" ]]; then
        echo "ERROR: PYEXPINT_CAMPAIGN_ID not set" >&2
        return 3
    fi

    if [[ -z "${PYEXPINT_SOURCE_MANIFEST_SHA256:-}" ]]; then
        echo "ERROR: PYEXPINT_SOURCE_MANIFEST_SHA256 not set" >&2
        return 4
    fi

    PYEXPINT_RUNTIME="${PYEXPINT_RUNTIME:-source}"
    PYEXPINT_PYTHON_MODULE="${PYEXPINT_PYTHON_MODULE:-python/3.11.4}"
    PYEXPINT_PYTHON="${PYEXPINT_PYTHON:-python3}"
    PYEXPINT_TOMS_BLOCKS="${PYEXPINT_TOMS_BLOCKS:-12}"

    cd "$PYEXPINT_RUN_DIR"
    CD_RC=$?

    if [[ "$CD_RC" -ne 0 ]]; then
        echo "ERROR: cannot cd to $PYEXPINT_RUN_DIR" >&2
        return "$CD_RC"
    fi

    module purge
    MODULE_PURGE_RC=$?

    if [[ "$MODULE_PURGE_RC" -ne 0 ]]; then
        echo "ERROR: module purge failed: $MODULE_PURGE_RC" >&2
        return "$MODULE_PURGE_RC"
    fi

    module load "$PYEXPINT_PYTHON_MODULE"
    MODULE_LOAD_RC=$?

    if [[ "$MODULE_LOAD_RC" -ne 0 ]]; then
        echo "ERROR: module load failed: $MODULE_LOAD_RC" >&2
        return "$MODULE_LOAD_RC"
    fi

    export OMP_NUM_THREADS=1
    export MKL_NUM_THREADS=1
    export OPENBLAS_NUM_THREADS=1
    export NUMEXPR_NUM_THREADS=1
    export PYTHONHASHSEED=0

    export PYTHONPATH="$PYEXPINT_RUN_DIR/code/src${PYTHONPATH:+:$PYTHONPATH}"

    {
        echo "campaign=$PYEXPINT_CAMPAIGN_ID"
        echo "job=${SLURM_JOB_ID:-UNSET}"
        echo "node=$(hostname)"
        echo "date=$(date -Is)"
        echo "blocks=$PYEXPINT_TOMS_BLOCKS"
        echo "runtime=$PYEXPINT_RUNTIME"
        echo "source_hash=$PYEXPINT_SOURCE_MANIFEST_SHA256"
        module list 2>&1 || true
        "$PYEXPINT_PYTHON" -V 2>&1 || true
    } | tee "$PYEXPINT_RUN_DIR/metadata/timing_job_header.txt"

    "$PYEXPINT_PYTHON" \
        "$PYEXPINT_RUN_DIR/ops/python/check_runtime.py" \
        --source "$PYEXPINT_RUN_DIR/code/src" \
        --smoke

    CHECK_RC=$?

    printf '%s\n' "$CHECK_RC" \
        > "$PYEXPINT_RUN_DIR/metadata/runtime_check_rc.txt"

    if [[ "$CHECK_RC" -ne 0 ]]; then
        echo "ERROR: runtime check failed: $CHECK_RC" >&2
        return "$CHECK_RC"
    fi

    srun --cpu-bind=cores \
        "$PYEXPINT_PYTHON" \
        "$PYEXPINT_RUN_DIR/ops/python/toms_timing_balanced.py" \
        --outdir "$PYEXPINT_RUN_DIR/results/raw" \
        --metadata-dir "$PYEXPINT_RUN_DIR/metadata" \
        --blocks "$PYEXPINT_TOMS_BLOCKS"

    RUNNER_RC=$?

    printf '%s\n' "$RUNNER_RC" \
        > "$PYEXPINT_RUN_DIR/metadata/toms_runner_rc.txt"

    if [[ "$RUNNER_RC" -ne 0 ]]; then
        echo "ERROR: TOMS runner failed: $RUNNER_RC" >&2
        return "$RUNNER_RC"
    fi

    "$PYEXPINT_PYTHON" \
        "$PYEXPINT_RUN_DIR/ops/python/analyze_toms_timing.py" \
        --raw-dir "$PYEXPINT_RUN_DIR/results/raw" \
        --out-dir "$PYEXPINT_RUN_DIR/results/analysis"

    ANALYZE_RC=$?

    printf '%s\n' "$ANALYZE_RC" \
        > "$PYEXPINT_RUN_DIR/metadata/toms_analyze_rc.txt"

    if [[ "$ANALYZE_RC" -ne 0 ]]; then
        echo "ERROR: TOMS analysis failed: $ANALYZE_RC" >&2
        return "$ANALYZE_RC"
    fi

    echo "TOMS_JOB_FINISHED=1"
    return 0
}

main "$@"
