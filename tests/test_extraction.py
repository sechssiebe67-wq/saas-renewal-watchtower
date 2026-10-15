import datetime as dt
import unittest

from watchtower import extraction


INVOICE = """Acme Cloud GmbH
Rechnung Nr. 2026-0042
Datum: 01.01.2026
Leistung: Acme Workspace
Lizenzen: 50 Benutzer
Abrechnung monatlich
Gesamtbetrag: 1.234,56 EUR
Nächste Verlängerung: 15.03.2027
Kündigungstermin: 13.02.2027
Kündigungsfrist: 30 Tage
"""


class ExtractionTests(unittest.TestCase):
    def test_amount_and_currency(self):
        result = extraction.extract(INVOICE)
        self.assertIsNotNone(result.amount)
        self.assertAlmostEqual(result.amount.value, 1234.56, places=2)
        self.assertEqual(result.currency.value, "EUR")

    def test_dates(self):
        result = extraction.extract(INVOICE)
        self.assertEqual(result.deadline.value, dt.date(2027, 2, 13))
        self.assertEqual(result.renewal_date.value, dt.date(2027, 3, 15))

    def test_notice_and_seats_and_vendor(self):
        result = extraction.extract(INVOICE)
        self.assertEqual(result.notice_days.value, 30)
        self.assertEqual(result.seats_total.value, 50)
        self.assertIn("Acme Cloud", result.vendor.value)

    def test_notice_not_from_payment_terms(self):
        result = extraction.extract("Zahlung innerhalb von 30 Tagen. Gesamtbetrag: 10,00 EUR\n")
        self.assertIsNone(result.notice_days)

    def test_billing_period(self):
        result = extraction.extract(INVOICE)
        self.assertEqual(result.billing_period.value, "monthly")

    def test_confidence_ranges(self):
        result = extraction.extract(INVOICE)
        self.assertGreater(result.overall_confidence(), 0)
        for field in result.fields():
            if field is not None:
                self.assertGreaterEqual(field.confidence, 0.0)
                self.assertLessEqual(field.confidence, 1.0)

    def test_empty_text(self):
        result = extraction.extract("")
        self.assertEqual(result.overall_confidence(), 0.0)
        self.assertIn("empty_text", result.warnings)

    def test_numeric_formats(self):
        self.assertAlmostEqual(extraction._normalize_number("1.234,56"), 1234.56)
        self.assertAlmostEqual(extraction._normalize_number("1,234.56"), 1234.56)
        self.assertAlmostEqual(extraction._normalize_number("1.234"), 1234.0)
        self.assertAlmostEqual(extraction._normalize_number("49,00"), 49.0)

    def test_to_dict_is_json_ready(self):
        import json

        payload = extraction.extract(INVOICE).to_dict()
        json.dumps(payload)
        self.assertIn("amount", payload)
        self.assertEqual(payload["deadline"]["value"], "2027-02-13")


if __name__ == "__main__":
    unittest.main()
