"""
Unit tests for AmpliconValidator.
"""

import unittest
from primer_agent.tools.amplicon_validator import _validate_amplicon_impl


class TestAmpliconValidator(unittest.TestCase):

    def test_5_amplicon_outside_qpcr_range(self):
        pcr_result = {
            "status": "PASS",
            "amplicon_count": 1,
            "amplicon_size": 850,  # 850 bp > 200 bp max for qPCR
            "amplicons": [{"amplicon_size": 850}],
            "orientation": "correct",
        }
        res = _validate_amplicon_impl(pcr_result, application="qPCR")
        self.assertEqual(res["status"], "FAIL")
        self.assertTrue(any("outside" in f.lower() for f in res["failures"]))

    def test_6_correct_target_plus_off_target_product(self):
        pcr_result = {
            "status": "FAIL",
            "amplicon_count": 2,
            "amplicon_size": 140,
            "amplicons": [
                {"amplicon_size": 140},
                {"amplicon_size": 520},
            ],
            "orientation": "correct",
            "reason": "Multiple potential PCR amplicons detected.",
        }
        res = _validate_amplicon_impl(pcr_result, application="qPCR")
        self.assertEqual(res["status"], "FAIL")
        self.assertTrue(len(res["warnings"]) > 0 or len(res["failures"]) > 0)


if __name__ == "__main__":
    unittest.main()
