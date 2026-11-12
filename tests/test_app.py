import unittest
from unittest.mock import patch

import pandas as pd

import app as dashboard


def sample_data():
    return pd.DataFrame(
        [
            {
                "record_id": "1",
                "year": 2022,
                "sex": "Mujer",
                "age_group": "(20 a 24)",
                "life_stage": "Juventud",
                "month": "Enero",
                "weekday": "Lunes",
                "time_range": "(18:00 a 20:59)",
                "department": "Bogotá, D.C.",
                "municipality": "Bogotá, D.C.",
                "scene": "Vivienda",
                "circumstance": "Violencia entre otros familiares",
                "context": "Contexto A",
                "alleged_aggressor": "Padre",
                "trigger": "Intolerancia",
            },
            {
                "record_id": "2",
                "year": 2023,
                "sex": "Mujer",
                "age_group": "(25 a 29)",
                "life_stage": "Adultez",
                "month": "Febrero",
                "weekday": "Martes",
                "time_range": "(15:00 a 17:59)",
                "department": "Bogotá, D.C.",
                "municipality": "Bogotá, D.C.",
                "scene": "Vivienda",
                "circumstance": "Violencia entre otros familiares",
                "context": "Contexto A",
                "alleged_aggressor": "Pareja",
                "trigger": "Intolerancia",
            },
            {
                "record_id": "3",
                "year": 2023,
                "sex": "Hombre",
                "age_group": "(30 a 34)",
                "life_stage": "Adultez",
                "month": "Marzo",
                "weekday": "Miércoles",
                "time_range": "(12:00 a 14:59)",
                "department": "Antioquia",
                "municipality": "Medellín",
                "scene": "Vivienda",
                "circumstance": "Violencia entre otros familiares",
                "context": "Contexto A",
                "alleged_aggressor": "Hermano",
                "trigger": "Celos",
            },
        ]
    )


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.data = sample_data()
        self.patcher = patch.object(dashboard, "load_data", return_value=self.data)
        self.patcher.start()
        self.client = dashboard.create_app().test_client()

    def tearDown(self):
        self.patcher.stop()

    def test_dashboard_renders_filtered_summary_and_charts(self):
        response = self.client.get(
            "/",
            query_string={"year": "2023", "department": "Bogotá, D.C."},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<strong>1</strong>", response.data)
        self.assertIn(b"Vivienda", response.data)
        self.assertIn(b"2023", response.data)
        self.assertIn(b"model-chart", response.data)

    def test_invalid_year_is_rejected(self):
        response = self.client.get("/", query_string={"year": "1900"})
        self.assertEqual(response.status_code, 400)

    def test_dataset_categories_are_grouped_without_case_or_accent_differences(self):
        counts = dashboard.category_counts(
            pd.Series(["Vía Pública", "vía pública", "Vivienda"])
        )

        self.assertEqual(counts.iloc[0]["label"], "Vía Pública")
        self.assertEqual(counts.iloc[0]["count"], 2)


if __name__ == "__main__":
    unittest.main()
