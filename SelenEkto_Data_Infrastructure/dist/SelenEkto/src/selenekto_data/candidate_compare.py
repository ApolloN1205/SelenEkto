"""Prepare map-cell measurements for display without inventing a landing suitability score."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
import math

METRICS = ('elevation_m', 'slope_deg', 'elevation_rms_m', 'lola_spot_count')


def comparison_series(candidates: Sequence[Mapping]):
    """Return candidate names and separate numeric metric columns.

    Missing or nonfinite measurements are reported as None, not zero.
    These values are not scores or solar measurements.
    """
    if len(candidates) < 2:
        raise ValueError('At least two candidates are required')
    names = []
    metrics = {metric: [] for metric in METRICS}
    for index, row in enumerate(candidates, 1):
        names.append(str(row.get('name') or f'Candidate {index:02d}'))
        for key in METRICS:
            value = row.get(key)
            if value is not None:
                try:
                    value = float(value)
                    if not math.isfinite(value): value = None
                except (TypeError, ValueError):
                    value = None
            metrics[key].append(value)
    return names, metrics
