"""Explainable relative candidate preferences; NOT a lunar landing safety assessment.

Do not impute or invent missing measurements. No score is produced if a positively
weighted criterion is missing. Higher score means a closer match to the user's
preferences *among just the compared candidates*.
"""
from __future__ import annotations
import math
from collections.abc import Mapping, Sequence

CRITERIA = {
    "Gentler slope": ("slope_deg", "lower", "degrees"),
    "Lower elevation uncertainty": ("elevation_rms_m", "lower", "m RMS"),
    "Lower slope uncertainty": ("slope_rms_deg", "lower", "degrees RMS"),
    "More direct LOLA observations": ("lola_spot_count", "higher", "spots/pixel"),
}
DEFAULT_WEIGHTS = {"Gentler slope": 5, "Lower elevation uncertainty": 3,
                   "Lower slope uncertainty": 2, "More direct LOLA observations": 1}


def evaluate(records: Sequence[Mapping], weights: Mapping):
    """Return ordered rows, including explicit exclusions and metric contributions.

    Normalization uses the min and max across selected candidates with finite
    readings; identical readings receive 0.5, indicating no distinction.
    It is a relative preference index, not a probability of success or safety.
    """
    if len(records) < 2:
        raise ValueError("Choose two or more named candidates to compare.")
    clean = {}
    for label in CRITERIA:
        value = weights.get(label, 0)
        if type(value) is not int or not 0 <= value <= 10:
            raise ValueError(f"Weight for {label} must be a whole number from 0 to 10.")
        clean[label] = value
    if not any(clean.values()):
        raise ValueError("Increase at least one weight above zero.")
    ranges = {}
    for label, (field, _, _) in CRITERIA.items():
        valid = []
        for r in records:
            x = r.get(field)
            if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x):
                valid.append(float(x))
        ranges[label] = (min(valid), max(valid)) if valid else None
    results = []
    for record in records:
        missing, pieces, total = [], {}, 0.0
        for label, (field, direction, units) in CRITERIA.items():
            weight = clean[label]
            if weight == 0:
                continue
            x = record.get(field)
            if not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x):
                missing.append(f"{label} ({field})")
                continue
            low, high = ranges[label]
            norm = 0.5 if high == low else ((float(x) - low) / (high - low))
            if direction == "lower":
                norm = 1.0 - norm
            pieces[label] = {"reading": float(x), "units": units,
                             "relative_score": round(norm, 6), "weight": weight}
            total += norm * weight
        score = None if missing else round(100 * total / sum(clean.values()), 2)
        results.append({"name": str(record.get("name", "Unnamed")),
                        "region": str(record.get("region", "Unknown")),
                        "score": score, "missing": missing, "criteria": pieces})
    results.sort(key=lambda r: (r["score"] is None, -(r["score"] or 0), r["name"]))
    return {"weights": clean, "rows": results,
            "explanation": "Scores are relative to the selected candidates and selected preferences, not landing suitability or safety. No score is calculated when weighted data is missing. A tie is not resolved."}
