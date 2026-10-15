import unittest
import zlib

from watchtower.pdf import extract_pdf_text, extract_text


def _make_pdf(lines):
    parts = [b"BT /F1 12 Tf"]
    for line in lines:
        parts.append(b"(" + line.encode("latin-1") + b") Tj")
    parts.append(b"ET")
    content = b" ".join(parts)
    compressed = zlib.compress(content)
    return (
        b"%PDF-1.4\n1 0 obj\n<< /Length " + str(len(compressed)).encode() + b" >>\n"
        b"stream\n" + compressed + b"\nendstream\nendobj\n%%EOF"
    )


class PdfTests(unittest.TestCase):
    def test_flate_stream_extraction(self):
        pdf = _make_pdf(["Acme Cloud GmbH", "Gesamtbetrag: 1.234,56 EUR"])
        text = extract_pdf_text(pdf)
        self.assertIn("Acme Cloud GmbH", text)
        self.assertIn("1.234,56 EUR", text)

    def test_extract_text_dispatches_on_extension(self):
        pdf = _make_pdf(["Hello World"])
        self.assertIn("Hello World", extract_text("invoice.pdf", pdf))

    def test_plain_text(self):
        self.assertEqual(extract_text("notes.txt", b"line one\nline two"), "line one\nline two")

    def test_empty(self):
        self.assertEqual(extract_pdf_text(b""), "")

    def test_pdf_escapes(self):
        content = b"BT (50% \\u2013 test \\(ok\\)) Tj ET"
        stream = zlib.compress(content)
        pdf = b"%PDF-1.4\nstream\n" + stream + b"\nendstream\n"
        text = extract_pdf_text(pdf)
        self.assertIn("test (ok)", text)


if __name__ == "__main__":
    unittest.main()
