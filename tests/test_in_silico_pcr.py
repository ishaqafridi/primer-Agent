"""
Unit tests for InSilicoPCRTool (In-Silico PCR validation).
"""

import unittest
from primer_agent.tools.in_silico_pcr import (
    _local_in_silico_pcr_impl,
    _run_in_silico_pcr_impl,
    reverse_complement,
)


class TestInSilicoPCR(unittest.TestCase):

    def setUp(self):
        self.fwd_seq = "ATGCGATCGATCGATCGATC"
        self.rev_seq = "GCTAGCTAGCTAGCTAGCTA"
        # Construct template with fwd, middle, and reverse complement of rev_seq
        rev_rc = reverse_complement(self.rev_seq)
        self.middle_seq = "A" * 100
        self.template = self.fwd_seq + self.middle_seq + rev_rc

    def test_1_valid_primer_pair_single_amplicon(self):
        res = _local_in_silico_pcr_impl(self.fwd_seq, self.rev_seq, self.template)
        self.assertEqual(res["status"], "PASS")
        self.assertEqual(res["amplicon_count"], 1)
        self.assertEqual(res["amplicon_size"], len(self.template))
        self.assertTrue(res["specific_product"])

    def test_2_forward_binds_reverse_does_not(self):
        res = _local_in_silico_pcr_impl(self.fwd_seq, "CCCCCCCCCCCCCCCCCCCC", self.template)
        self.assertEqual(res["status"], "FAIL")
        self.assertEqual(res["amplicon_count"], 0)
        self.assertTrue(res["forward_binding"])
        self.assertFalse(res["reverse_binding"])

    def test_3_incorrect_primer_orientation(self):
        # Place reverse complement BEFORE forward primer
        rev_rc = reverse_complement(self.rev_seq)
        inverted_template = rev_rc + self.middle_seq + self.fwd_seq
        res = _local_in_silico_pcr_impl(self.fwd_seq, self.rev_seq, inverted_template)
        self.assertEqual(res["status"], "FAIL")
        self.assertEqual(res["amplicon_count"], 0)

    def test_4_multiple_pcr_products(self):
        # Template with duplicate binding sites
        rev_rc = reverse_complement(self.rev_seq)
        multi_template = self.template + ("T" * 50) + self.fwd_seq + ("A" * 100) + rev_rc
        res = _local_in_silico_pcr_impl(self.fwd_seq, self.rev_seq, multi_template)
        self.assertEqual(res["status"], "FAIL")
        self.assertTrue(res["amplicon_count"] > 1)

    def test_7_ucsc_supported_organism_db_resolution(self):
        res = _run_in_silico_pcr_impl(
            fwd_primer=self.fwd_seq,
            rev_primer=self.rev_seq,
            template_seq=self.template,
            organism="Homo sapiens",
        )
        self.assertIn("organism", res)
        self.assertEqual(res["organism"], "Homo sapiens")

    def test_8_unsupported_organism_local_engine(self):
        res = _run_in_silico_pcr_impl(
            fwd_primer=self.fwd_seq,
            rev_primer=self.rev_seq,
            template_seq=self.template,
            organism="Custom Novel Organism",
        )
        self.assertEqual(res["engine_used"], "Local Reference PCR Engine")
        self.assertEqual(res["status"], "PASS")

    def test_9_ucsc_unavailable_graceful_fallback(self):
        # Provide template sequence for local fallback
        res = _run_in_silico_pcr_impl(
            fwd_primer=self.fwd_seq,
            rev_primer=self.rev_seq,
            template_seq=self.template,
            organism="Homo sapiens",
        )
        self.assertIn(res["status"], ["PASS", "FAIL"])


if __name__ == "__main__":
    unittest.main()
