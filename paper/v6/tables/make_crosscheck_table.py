#!/usr/bin/env python3
"""Parse the supplied EXPINT comparison summary without inventing missing rows.

Usage:
  python tables/make_crosscheck_table.py REPORT TABLE_TEX METADATA_JSON

Only the provided summary is read. This script does not import PyEXPINT, run
Octave, reconstruct historical source identities, or validate software tests.
Scientific-notation strings and coefficient values retain the source precision.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path

NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"


def require_match(pattern: str, text: str) -> re.Match[str]:
    match = re.search(pattern, text, re.MULTILINE)
    if match is None:
        raise ValueError(f"Required report field not found: {pattern}")
    return match


def parse_report(path: Path) -> dict:
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    total = int(require_match(r"^PyEXPINT methods compared with the original EXPINT schemes: (\d+)$", text)[1])
    group = require_match(
        rf"^agree to ({NUMBER}) on both problems: (\d+) "
        rf"\(largest relative difference: scalar ({NUMBER}), matrix ({NUMBER})\)$", text)
    corrections = []
    pattern = (
        rf"^([A-Za-z0-9]+): differs from the 2005 file "
        rf"\(scalar ({NUMBER}), matrix ({NUMBER})\); agrees with its one-line "
        rf"correction \(scalar ({NUMBER}), matrix ({NUMBER})\) OK$")
    for m in re.finditer(pattern, text, re.MULTILINE):
        corrections.append({
            "method": m[1], "original_scalar": m[2], "original_matrix": m[3],
            "corrected_scalar": m[4], "corrected_matrix": m[5],
            "reported_status": "OK", "kind": "one_line_correction"})
    regenerated = require_match(
        rf"^(ModGenLawson45): differs from the 2005 file "
        rf"\(scalar ({NUMBER}), matrix ({NUMBER})\); output coefficients "
        rf"regenerated from the published construction$", text)
    z = require_match(rf"^ModGenLawson45 coefficient functions at z = ({NUMBER}) that differ:$", text)[1]
    coefficients = []
    for m in re.finditer(rf"^\s*([BV]\[\d+,\d+\])\s+PyEXPINT\s+({NUMBER})\s+EXPINT 2005\s+({NUMBER})\s*$", text, re.MULTILINE):
        coefficients.append({"entry_as_printed": m[1], "pyexpint_as_printed": m[2], "expint_2005_as_printed": m[3]})
    result = require_match(r"^RESULT: (\S+)$", text)[1]
    if len(corrections) != 4 or len({c["method"] for c in corrections}) != 4:
        raise ValueError("Expected four distinct one-line correction records")
    if len(coefficients) != 6 or len({c["entry_as_printed"] for c in coefficients}) != 6:
        raise ValueError("Expected six distinct coefficient pairs")
    if int(group[2]) + len(corrections) + 1 != total:
        raise ValueError("Comparison counts do not sum to the reported catalogue size")
    values = [group[1], group[3], group[4], regenerated[2], regenerated[3]]
    values += [c[k] for c in corrections for k in ("original_scalar", "original_matrix", "corrected_scalar", "corrected_matrix")]
    if any(not math.isfinite(float(x)) or float(x) < 0 for x in values):
        raise ValueError("Nonfinite or negative difference in report")
    return {
        "schema": "pyexpint-crosscheck-summary-transcription-1",
        "source_file": "reproducibility/expint_crosscheck/crosscheck_report.txt",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "hash_scope": "supplied bytes; not a historical-execution or software-candidate hash",
        "methods_compared": total,
        "agreeing_group": {
            "count": int(group[2]), "threshold_as_printed": group[1],
            "largest_scalar_relative_difference_as_printed": group[3],
            "largest_matrix_relative_difference_as_printed": group[4],
            "individual_rows_supplied": False},
        "one_line_corrections": corrections,
        "regenerated_entry": {
            "method": regenerated[1], "original_scalar": regenerated[2], "original_matrix": regenerated[3],
            "corrected_final_state_comparison_supplied": False,
            "coefficient_argument_as_printed": z,
            "index_convention": "not specified; reproduced verbatim",
            "coefficient_pairs": coefficients},
        "reported_result": result,
        "not_supplied_by_this_report": [
            "individual results for the 42 agreeing entries", "full problem definitions and options",
            "step-size refinement sequences", "historical source hashes and correction diffs",
            "software-candidate identity", "execution environment", "275-test or clean-installation logs"],
        "scope": "parsing and internal consistency of an author-supplied summary; no numerical rerun"}


def sci(value: str | None) -> str:
    if value is None:
        return r"\textemdash"
    if "e" in value.lower():
        mantissa, exponent = value.lower().split("e")
        exponent = int(exponent)
        return f"${mantissa}\\times10^{{{exponent}}}$" if exponent else f"${mantissa}$"
    return f"${value}$"


def make_table(data: dict) -> str:
    g = data["agreeing_group"]
    rows = ["42 entries (reported maxima) & " + sci(g["largest_scalar_relative_difference_as_printed"]) + " & " + sci(g["largest_matrix_relative_difference_as_printed"]) + r" & \textemdash & \textemdash\\"]
    for c in data["one_line_corrections"]:
        rows.append(c["method"] + " & " + " & ".join(sci(c[k]) for k in ("original_scalar", "original_matrix", "corrected_scalar", "corrected_matrix")) + r"\\")
    r = data["regenerated_entry"]
    rows.append(r["method"] + " & " + sci(r["original_scalar"]) + " & " + sci(r["original_matrix"]) + r" & \textemdash & \textemdash\\")
    coef = [r"\texttt{"+c["entry_as_printed"]+"} & "+r"\texttt{"+c["pyexpint_as_printed"]+"} & "+r"\texttt{"+c["expint_2005_as_printed"]+r"}\\" for c in r["coefficient_pairs"]]
    return r"""% Generated from the unchanged supplied summary; do not edit by hand.
\begin{table}[htbp]
\centering\small
\caption{Numerical statements in the supplied cross-check summary. Top:
relative final-state differences on the scalar and matrix problems, before
and after the four reported one-line corrections. The first row gives the
reported aggregate maxima for 42 entries, not individually reconstructed
results. Dashes denote comparisons not supplied or not applicable, not zero.
Bottom: the six coefficient pairs reported for ModGenLawson45 at $z=-0.3$;
decimal values are reproduced verbatim, and the companion drivers use one-based indices.}\label{tab:crosscheck-summary}
\begin{tabular}{@{}lcccc@{}}\toprule
 & \multicolumn{2}{c}{Original 2005 file} & \multicolumn{2}{c}{One-line correction}\\
Entry & Scalar & Matrix & Scalar & Matrix\\\midrule
""" + "\n".join(rows) + r"""
\bottomrule\end{tabular}

\medskip
\begin{tabular}{@{}lrr@{}}\toprule
Coefficient & PyEXPINT & EXPINT 2005\\\midrule
""" + "\n".join(coef) + r"""
\bottomrule\end{tabular}

\medskip
\begin{minipage}{.96\linewidth}\footnotesize
The summary reports 47 compared entries, 42 agreeing within $10^{-12}$ on
both problems, four agreeing after a one-line correction, and one
regenerated entry. Its final status is \texttt{RESULT: OK}. This summary table
is complemented by the separately archived refinement outputs, problem
definitions, correction diffs and execution-environment record. The regenerated
entry has no separate corrected final-state result in the report. This table
is a transcription, not a new Octave or PyEXPINT execution.
\end{minipage}
\end{table}
"""


def main(argv: list[str]) -> None:
    if len(argv) != 4:
        raise ValueError("Usage: make_crosscheck_table.py REPORT TABLE_TEX METADATA_JSON")
    source, table, metadata = map(Path, argv[1:])
    if source.resolve() in {table.resolve(), metadata.resolve()}:
        raise ValueError("The original report cannot be an output path")
    data = parse_report(source)
    for p in (table, metadata):
        p.parent.mkdir(parents=True, exist_ok=True)
    table.write_text(make_table(data), encoding="utf-8")
    metadata.write_text(json.dumps(data, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print("SUMMARY_COUNTS_CONSISTENT=1")
    print("REPORT_SHA256="+data["source_sha256"])
    print("PARSED=42 aggregate + 4 one-line corrections + 1 regenerated")
    print("NUMERICAL_RERUNS=0")


if __name__ == "__main__":
    main(sys.argv)
