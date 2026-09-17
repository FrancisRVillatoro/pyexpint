#!/usr/bin/env bash

main() {
    if [[ $# -ne 1 ]]; then
        echo "Usage: $0 CAMPAIGN_ID" >&2
        return 2
    fi

    CAMPAIGN_ID="$1"

    HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    ROOT="${PYEXPINT_HOME_ROOT:-$HOME/pyexpint_toms}"

    if [[ ! -f "$HERE/config/picasso.env" ]]; then
        echo "ERROR: missing config: $HERE/config/picasso.env" >&2
        return 3
    fi

    source "$HERE/config/picasso.env"

    RUN_DIR="$PYEXPINT_FSCRATCH_ROOT/runs/$CAMPAIGN_ID"

    if [[ ! -d "$RUN_DIR" ]]; then
        echo "ERROR: missing campaign directory: $RUN_DIR" >&2
        return 4
    fi

    if [[ ! -f "$RUN_DIR/campaign.env" ]]; then
        echo "ERROR: missing campaign.env: $RUN_DIR/campaign.env" >&2
        return 5
    fi

    source "$RUN_DIR/campaign.env"

    if [[ -e "$RUN_DIR/metadata/jobid.txt" ]]; then
        echo "ERROR: job already recorded in $RUN_DIR/metadata/jobid.txt" >&2
        return 6
    fi

    if [[ ! -f "$RUN_DIR/slurm/toms_timing_single.slurm" ]]; then
        echo "ERROR: missing staged Slurm file:" >&2
        echo "  $RUN_DIR/slurm/toms_timing_single.slurm" >&2
        return 7
    fi

    cd "$RUN_DIR" || {
        echo "ERROR: cannot cd to $RUN_DIR" >&2
        return 8
    }

    JOBID_RAW="$(
        /usr/bin/sbatch --parsable \
          --partition="$PYEXPINT_PARTITION" \
          --constraint="$PYEXPINT_CONSTRAINT" \
          --nodes=1 \
          --ntasks=1 \
          --cpus-per-task=1 \
          --mem="$PYEXPINT_TOMS_MEM" \
          --time="$PYEXPINT_TOMS_TIME" \
          --output="$RUN_DIR/logs/toms_%j.out" \
          --error="$RUN_DIR/logs/toms_%j.err" \
          --export="ALL,PYEXPINT_CAMPAIGN_ID=$CAMPAIGN_ID,PYEXPINT_RUN_DIR=$RUN_DIR,PYEXPINT_RUNTIME=$PYEXPINT_RUNTIME,PYEXPINT_SOURCE_MANIFEST_SHA256=$PYEXPINT_SOURCE_MANIFEST_SHA256,PYEXPINT_PYTHON_MODULE=$PYEXPINT_PYTHON_MODULE,PYEXPINT_PYTHON=$PYEXPINT_PYTHON,PYEXPINT_MIN_PYTHON=$PYEXPINT_MIN_PYTHON,PYEXPINT_MIN_NUMPY=$PYEXPINT_MIN_NUMPY,PYEXPINT_MIN_SCIPY=$PYEXPINT_MIN_SCIPY,PYEXPINT_TOMS_BLOCKS=$PYEXPINT_TOMS_BLOCKS" \
          "$RUN_DIR/slurm/toms_timing_single.slurm"
    )"

    SBATCH_RC=$?

    if [[ "$SBATCH_RC" -ne 0 ]]; then
        echo "ERROR: sbatch failed with status $SBATCH_RC" >&2
        printf 'SBATCH_RAW=%q\n' "$JOBID_RAW" >&2
        return 9
    fi

    #
    # Picasso may prepend ANSI colour sequences to sbatch output.
    # Keep digits and an optional ';cluster' payload only after removing
    # CSI escape sequences and line endings.
    #
    JOBID_CLEAN="$(
        printf '%s' "$JOBID_RAW" |
        sed $'s/\033\\[[0-9;]*[[:alpha:]]//g' |
        tr -d '\r\n'
    )"

    JOBID="${JOBID_CLEAN%%;*}"

    if [[ ! "$JOBID" =~ ^[0-9]+$ ]]; then
        echo "ERROR: sbatch returned a non-numeric job id." >&2
        printf 'SBATCH_RAW=%q\n' "$JOBID_RAW" >&2
        printf 'SBATCH_CLEAN=%q\n' "$JOBID_CLEAN" >&2
        printf 'JOBID=%q\n' "$JOBID" >&2
        return 10
    fi

    printf '%s\n' "$JOBID" \
        > "$RUN_DIR/metadata/jobid.txt"

    printf '%s\n' "24" \
        > "$RUN_DIR/metadata/expected_cases.txt"

    printf '%s\n' "single" \
        > "$RUN_DIR/metadata/job_kind.txt"

    printf '%s\n' "balanced_toms_timing" \
        > "$RUN_DIR/metadata/campaign_profile.txt"

    mkdir -p "$PYEXPINT_HOME_ROOT/state"

    printf '%s\n' "$JOBID" \
        > "$PYEXPINT_HOME_ROOT/state/${CAMPAIGN_ID}.jobid"

    date -Is \
        > "$RUN_DIR/metadata/submitted_at.txt"

    printf 'TOMS_TIMING_SUBMITTED campaign=%s jobid=%s blocks=%s\n' \
        "$CAMPAIGN_ID" \
        "$JOBID" \
        "$PYEXPINT_TOMS_BLOCKS"

    return 0
}

main "$@"
