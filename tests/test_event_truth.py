"""Independent nonzero insertion positions, complete releases and selected-region censoring."""

import unittest

from similar_sound_search.events.metrics import reference_notes
from similar_sound_search.storage import InputError


class NoteTruthCase(unittest.TestCase):
    def values(self):
        tone = {
            "asset_id": "tone",
            "audio": {"sample_rate_hz": 1000, "sample_count": 2400},
            "events": [
                {"start_frame": 0, "end_frame": 1100},
                {"start_frame": 650, "end_frame": 1750},
                {"start_frame": 1300, "end_frame": 2400},
            ],
        }
        mixture = {
            "asset_id": "mixture",
            "audio": {"sample_rate_hz": 1000, "sample_count": 8000},
            "identity": {"recipe": {"kind": "mixture", "target_asset": "tone"}},
            "insertions": [[750, 3150]],
        }
        return tone, mixture

    def test_nonzero_insertion_keeps_true_release_beyond_region(self):
        tone, mixture = self.values()
        notes = reference_notes(mixture, tone, 0, 2400)
        self.assertEqual(
            [(n["start_frame"], n["end_frame"]) for n in notes],
            [(750, 1850), (1400, 2500), (2050, 3150)],
        )
        self.assertEqual([n["selection_end_censored"] for n in notes], [False, True, True])

    def test_target_outside_selected_region_is_absent(self):
        tone, mixture = self.values()
        mixture["insertions"] = [[3000, 5400]]
        self.assertEqual(reference_notes(mixture, tone, 0, 2400), [])

    def test_multiple_insertions_and_exact_complete_region(self):
        tone, mixture = self.values()
        mixture["insertions"].append([5000, 7400])
        notes = reference_notes(mixture, tone, 750, 3150)
        self.assertEqual(len(notes), 3)
        self.assertTrue(all(not n["selection_end_censored"] for n in notes))
        self.assertEqual(reference_notes(mixture, None, 0, 8000), [])

    def test_geometry_or_target_identity_drift_fails(self):
        tone, mixture = self.values()
        mixture["insertions"] = [[750, 3149]]
        with self.assertRaises(InputError):
            reference_notes(mixture, tone, 0, 2400)
        mixture["insertions"] = [[750, 3150]]
        mixture["identity"]["recipe"]["target_asset"] = "different"
        with self.assertRaises(InputError):
            reference_notes(mixture, tone, 0, 2400)
