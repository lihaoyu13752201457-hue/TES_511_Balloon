#!/usr/bin/env python3
"""Unit tests for shipped TES extract (energy field index 4)."""
from __future__ import annotations

import gzip
import sys
import tempfile
import unittest
from pathlib import Path

# import shipped module
sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_targeted_stats as ex  # noqa: E402


class TestExtractTesStats(unittest.TestCase):
    def _write_mini_sim(self, path: Path, events: list[list[tuple[int, float]]]) -> None:
        """events: list of HT hits (det, energy_keV) per SE event."""
        lines = ["# mini sim\n", "Type SIM\n"]
        for hits in events:
            lines.append("SE\n")
            for det, e in hits:
                # HTsim det;x;y;z;energy;time
                lines.append(
                    f"HTsim {det}; 0.0; 0.0; 0.0; {e:.5f};0.00000e+00;1\n"
                )
        raw = "".join(lines).encode()
        with gzip.open(path, "wb") as f:
            f.write(raw)

    def test_energy_field_index_4_not_time(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "mini.sim.gz"
            # one event: det4 energy 500 keV (in band), time field is 0
            self._write_mini_sim(p, [[(4, 500.0)]])
            stats = ex.extract_tes_stats([p])
            self.assertEqual(stats["n_events"], 1)
            self.assertEqual(stats["n_tes"], 1)
            self.assertEqual(stats["n_band480_550"], 1)

    def test_out_of_band_and_multi_hit_sum(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "mini.sim.gz"
            # event1: 200+300 = 500 in band; event2: 100 only -> tes but not band
            self._write_mini_sim(p, [[(4, 200.0), (4, 300.0)], [(2, 100.0)]])
            stats = ex.extract_tes_stats([p])
            self.assertEqual(stats["n_events"], 2)
            self.assertEqual(stats["n_tes"], 2)
            self.assertEqual(stats["n_band480_550"], 1)

    def test_ignores_det_outside_1_to_6(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "mini.sim.gz"
            self._write_mini_sim(p, [[(20, 511.0)]])
            stats = ex.extract_tes_stats([p])
            self.assertEqual(stats["n_events"], 1)
            self.assertEqual(stats["n_tes"], 0)
            self.assertEqual(stats["n_band480_550"], 0)

    def test_real_targeted_sim_has_band_counts(self):
        """Drive real path: REF e+ targeted sim must yield many band events."""
        pkg = Path(__file__).resolve().parents[1]
        sim = (
            pkg
            / "05_targeted_stats/per_point/REF/eplus/TrajVal_REF_eplus_tgt.inc1.id1.sim.gz"
        )
        if not sim.exists():
            self.skipTest("targeted REF eplus sim not on disk")
        # sample first ~2000 SE only via early stop by using full extract would be slow;
        # call extract on real file but trust function; assert n_band > 1000 for full 1e6
        stats = ex.extract_tes_stats([sim])
        self.assertEqual(stats["n_events"], 1_000_000)
        self.assertGreater(stats["n_band480_550"], 10_000)
        self.assertGreater(stats["n_tes"], stats["n_band480_550"])


if __name__ == "__main__":
    unittest.main()
