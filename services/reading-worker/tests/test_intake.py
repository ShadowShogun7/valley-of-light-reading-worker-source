from __future__ import annotations

import unittest

from reading_worker.intake import IntakeMappingError, build_reading_input


def valid_job() -> dict:
    return {
        "analysis_datetime": "2026-07-26T16:30:00Z",
        "analysis_timezone": "Asia/Taipei",
        "claimed": True,
        "generation_consent_version": "reading-generation-consent-2026-07-26",
        "intake_version": "relationship-intake-v1",
        "public_reading_id": "6cce7c3c-03a9-4d43-b2a7-79f46323dbba",
        "version": "paid-reading-job-v1",
        "final_payload": {
            "relationshipStage": "broke-up-recent",
            "mainQuestion": "any-chance",
            "contactStatus": "cold-chat",
            "generationConsentAccepted": True,
            "generationConsentVersion": "reading-generation-consent-2026-07-26",
            "user": {
                "birthDate": "1992-01-20",
                "birthTime": "08:15",
                "birthPlace": "臺北市",
                "gender": "female",
                "unknownTime": False,
            },
            "partner": {
                "birthDate": "1990-06-05",
                "birthTime": "",
                "birthPlace": "Tokyo",
                "gender": "male",
                "unknownTime": True,
            },
        },
    }


class IntakeTests(unittest.TestCase):
    def test_maps_stable_analysis_instant_to_taipei_clock(self) -> None:
        reading = build_reading_input(valid_job())
        self.assertEqual(reading["context"]["analysis_date"], "2026-07-27")
        self.assertEqual(
            reading["context"]["analysis_datetime"],
            "2026-07-27T00:30:00+08:00",
        )
        self.assertEqual(reading["context"]["contact_status"], "still-in-contact")
        self.assertEqual(reading["context"]["desired_outcome"], "reconnect")
        self.assertEqual(reading["person_a"]["birth_place"], "台北市")
        self.assertEqual(reading["person_b"]["birth_time"], "")
        self.assertEqual(reading["person_b"]["birth_timezone"], "Asia/Tokyo")

    def test_rejects_naive_analysis_datetime(self) -> None:
        job = valid_job()
        job["analysis_datetime"] = "2026-07-26T16:30:00"
        with self.assertRaisesRegex(
            IntakeMappingError,
            "INVALID_ANALYSIS_DATETIME",
        ):
            build_reading_input(job)

    def test_rejects_invalid_paid_choice(self) -> None:
        job = valid_job()
        job["final_payload"]["mainQuestion"] = "predict-the-future"
        with self.assertRaisesRegex(IntakeMappingError, "INVALID_MAIN_QUESTION"):
            build_reading_input(job)

    def test_rejects_generation_consent_mismatch(self) -> None:
        job = valid_job()
        job["final_payload"]["generationConsentVersion"] = "unexpected-consent"
        with self.assertRaisesRegex(
            IntakeMappingError,
            "GENERATION_CONSENT_MISMATCH",
        ):
            build_reading_input(job)

    def test_blank_place_forces_date_only_even_when_clock_time_was_entered(self) -> None:
        job = valid_job()
        job["final_payload"]["user"]["birthPlace"] = ""
        reading = build_reading_input(job)
        self.assertEqual(reading["person_a"]["birth_time"], "")


if __name__ == "__main__":
    unittest.main()
