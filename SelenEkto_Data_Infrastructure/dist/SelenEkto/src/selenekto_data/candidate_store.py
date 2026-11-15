"""Simple, testable candidate selection store for the SelenEkto local map."""
from __future__ import annotations

class CandidateStore:
    def __init__(self):
        self.records = []
        self.next_number = 1

    def add(self, selected):
        if selected is None:
            raise ValueError('Click a terrain cell before adding it.')
        row, col = selected['row'], selected['col']
        if any(r['row'] == row and r['col'] == col for r in self.records):
            raise ValueError('This cell is already in your candidate list.')
        record = {**selected, 'name': f'Candidate {self.next_number:02d}'}
        self.next_number += 1
        self.records.append(record)
        return record

    def remove_positions(self, positions):
        for i in sorted(set(positions), reverse=True):
            if i < 0 or i >= len(self.records):
                raise IndexError(i)
            del self.records[i]

    def as_rows(self):
        return list(self.records)
