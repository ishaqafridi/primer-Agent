"""
Unit tests for Target & Transcript Resolver (TargetResolver).
"""

import unittest
from primer_agent.tools.target_resolver import _resolve_target_impl


class TestTargetResolver(unittest.TestCase):

    def test_human_brca1_resolution(self):
        res = _resolve_target_impl("BRCA1", organism="Homo sapiens")
        self.assertEqual(res["status"], "PASS")
        self.assertEqual(res["genome_assembly"], "GRCh38")
        self.assertEqual(res["ucsc_db"], "hg38")
        self.assertTrue(len(res["exons"]) > 0)

    def test_mouse_resolution(self):
        res = _resolve_target_impl("Gapdh", organism="Mus musculus")
        self.assertEqual(res["genome_assembly"], "GRCm39")
        self.assertEqual(res["ucsc_db"], "mm39")

    def test_user_transcript_override(self):
        res = _resolve_target_impl("BRCA1", organism="Homo sapiens", user_transcript="NM_007294.4")
        self.assertEqual(res["transcript_accession"], "NM_007294.4")
        self.assertTrue(res["user_override"])


if __name__ == "__main__":
    unittest.main()
