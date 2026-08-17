import unittest
from pathlib import Path

from core.config import DEFAULT_CONFIG
from core.corpus import (
    GUIDELINE_MANIFEST,
    DocumentSection,
    chunk_sections,
    preprocess_document,
)


class CorpusPreprocessingTests(unittest.TestCase):
    def test_controlled_manifest(self):
        self.assertEqual(len(GUIDELINE_MANIFEST), 10)
        guideline_ids = [entry.guideline_id for entry in GUIDELINE_MANIFEST]
        self.assertEqual(len(guideline_ids), len(set(guideline_ids)))

    def test_text_document_to_structured_chunks(self):
        fixture_path = (
            Path(__file__).resolve().parent.parent
            / "test_data"
            / "phase3_sample_guideline.txt"
        )
        chunks = preprocess_document(
            fixture_path,
            source="phase3-synthetic",
            title="Synthetic Guideline Fixture",
        )

        self.assertTrue(chunks)
        self.assertTrue(all(chunk.content for chunk in chunks))
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        self.assertEqual(len(chunk_ids), len(set(chunk_ids)))
        self.assertTrue(
            all(
                chunk.source == "phase3-synthetic"
                and chunk.title == "Synthetic Guideline Fixture"
                and chunk.section
                for chunk in chunks
            )
        )
        recognised_sections = {
            "Clinical Presentation",
            "Diagnosis",
            "Differential Diagnosis",
            "Red Flags",
        }
        self.assertTrue(any(chunk.section in recognised_sections for chunk in chunks))

    def test_oversized_section_and_metadata_preservation(self):
        section = DocumentSection(
            source="synthetic-source",
            title="Synthetic Oversized Section",
            page=3,
            section="Diagnosis",
            text="Synthetic diagnostic chunking sentence. " * 80,
        )

        chunks = chunk_sections([section])

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk.page == 3 for chunk in chunks))
        self.assertTrue(all(chunk.section == "Diagnosis" for chunk in chunks))
        self.assertTrue(
            all(len(chunk.content) <= DEFAULT_CONFIG.chunk_size for chunk in chunks)
        )


if __name__ == "__main__":
    unittest.main()
