from __future__ import annotations

import unittest

from calculation.western.immanuel_adapter import KNOWN_PLACES
from reading_worker.runtime import _pin_longest_known_place_coordinates


class RuntimeLocationTests(unittest.TestCase):
    def test_new_taipei_uses_longest_alias_not_taipei(self) -> None:
        person = {"birth_place": "New Taipei, Taiwan"}
        _pin_longest_known_place_coordinates(person, KNOWN_PLACES)
        self.assertEqual(person["latitude"], 25.0169)
        self.assertEqual(person["longitude"], 121.4628)

    def test_exact_taipei_still_uses_taipei_coordinates(self) -> None:
        person = {"birth_place": "taipei"}
        _pin_longest_known_place_coordinates(person, KNOWN_PLACES)
        self.assertEqual(person["latitude"], 25.0330)
        self.assertEqual(person["longitude"], 121.5654)


if __name__ == "__main__":
    unittest.main()
