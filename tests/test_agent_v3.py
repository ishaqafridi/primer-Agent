"""
Integration tests for PrimerAgent v3.0 — Strict Validation-First Pipeline.

Tests verify the VALIDATE → REJECT → SCORE → RANK → RETURN workflow:
1. All QC pass → PASS with score 60-100
2. Any critical QC fail → FAIL with score=None (NOT SCORED)
3. Agent returns only valid pairs, never fills with failed primers
"""

import unittest
from primer_agent.react_agent import PrimerReActAgent
from primer_agent.tools.primer_evaluator import _evaluate_primer_pair_impl
from primer_agent.tools.parameter_adjuster import _adjust_parameters_impl


class TestStrictValidationPipeline(unittest.TestCase):

    def _make_passing_inputs(self):
        """Create a complete set of QC-passing inputs."""
        candidate = {
            "pair_idx": 1,
            "fwd_seq": "ATGCGATCGATCGATCGATC",
            "rev_seq": "GCTAGCTAGCTAGCTAGCTA",
            "fwd_tm": 60.0,
            "rev_tm": 60.2,
            "tm_diff": 0.2,
            "fwd_gc": 50.0,
            "rev_gc": 50.0,
            "product_size": 150,
        }
        fwd_blast = {"off_target_hits": 0, "pass": True}
        rev_blast = {"off_target_hits": 0, "pass": True}
        fwd_struct = {"hairpin_mfe": 0.0, "hairpin_pass": True, "self_dimer_mfe": 0.0, "self_dimer_pass": True}
        rev_struct = {"hairpin_mfe": 0.0, "hairpin_pass": True, "self_dimer_mfe": 0.0, "self_dimer_pass": True}
        hetero_struct = {"hetero_dimer_mfe": 0.0, "hetero_dimer_pass": True}
        pcr_result = {"status": "PASS", "amplicon_count": 1, "amplicon_size": 150, "reason": "OK"}
        exon_result = {"exon_junction": True, "genomic_dna_risk": "reduced"}
        return candidate, fwd_blast, rev_blast, fwd_struct, rev_struct, hetero_struct, pcr_result, exon_result

    def test_10_all_checks_pass_returns_score_60_100(self):
        """All QC checks pass → status=PASS, score in 60-100 range."""
        inputs = self._make_passing_inputs()
        res = _evaluate_primer_pair_impl(*inputs)

        self.assertTrue(res["pass"])
        self.assertEqual(res["status"], "PASS")
        self.assertTrue(res["recommended"])
        self.assertIsNotNone(res["score"])
        self.assertGreaterEqual(res["score"], 60.0)
        self.assertLessEqual(res["score"], 100.0)
        self.assertIsNotNone(res["breakdown"])
        self.assertEqual(len(res["failures"]), 0)

    def test_11_pcr_failure_returns_score_none(self):
        """In-Silico PCR >1 product → FAIL, score=None, NOT SCORED."""
        candidate, fwd_blast, rev_blast, fwd_struct, rev_struct, hetero_struct, _, exon_result = self._make_passing_inputs()
        pcr_result = {"status": "FAIL", "amplicon_count": 3, "amplicon_size": 0, "reason": "Multiple amplicons"}

        res = _evaluate_primer_pair_impl(
            candidate=candidate, fwd_blast=fwd_blast, rev_blast=rev_blast,
            fwd_struct=fwd_struct, rev_struct=rev_struct, hetero_struct=hetero_struct,
            pcr_result=pcr_result, exon_result=exon_result,
        )

        self.assertFalse(res["pass"])
        self.assertEqual(res["status"], "FAIL")
        self.assertFalse(res["recommended"])
        self.assertIsNone(res["score"])
        self.assertIsNone(res["breakdown"])
        self.assertTrue(any("CRITICAL" in f for f in res["failures"]))

    def test_12_hairpin_failure_returns_score_none(self):
        """Hairpin failure → FAIL, score=None, NOT SCORED."""
        candidate, fwd_blast, rev_blast, _, rev_struct, hetero_struct, pcr_result, exon_result = self._make_passing_inputs()
        fwd_struct_fail = {"hairpin_mfe": -3.5, "hairpin_pass": False, "self_dimer_mfe": 0.0, "self_dimer_pass": True}

        res = _evaluate_primer_pair_impl(
            candidate=candidate, fwd_blast=fwd_blast, rev_blast=rev_blast,
            fwd_struct=fwd_struct_fail, rev_struct=rev_struct, hetero_struct=hetero_struct,
            pcr_result=pcr_result, exon_result=exon_result,
        )

        self.assertFalse(res["pass"])
        self.assertIsNone(res["score"])
        self.assertEqual(res["status"], "FAIL")

    def test_13_hetero_dimer_failure_returns_score_none(self):
        """Hetero-dimer failure → FAIL, score=None, NOT SCORED."""
        candidate, fwd_blast, rev_blast, fwd_struct, rev_struct, _, pcr_result, exon_result = self._make_passing_inputs()
        hetero_fail = {"hetero_dimer_mfe": -8.0, "hetero_dimer_pass": False}

        res = _evaluate_primer_pair_impl(
            candidate=candidate, fwd_blast=fwd_blast, rev_blast=rev_blast,
            fwd_struct=fwd_struct, rev_struct=rev_struct, hetero_struct=hetero_fail,
            pcr_result=pcr_result, exon_result=exon_result,
        )

        self.assertFalse(res["pass"])
        self.assertIsNone(res["score"])
        self.assertEqual(res["status"], "FAIL")

    def test_14_gc_clamp_failure_returns_score_none(self):
        """3' GC clamp failure → FAIL, score=None, NOT SCORED."""
        _, fwd_blast, rev_blast, fwd_struct, rev_struct, hetero_struct, pcr_result, exon_result = self._make_passing_inputs()
        candidate_bad_clamp = {
            "pair_idx": 1,
            "fwd_seq": "ATGCGATCGATCGATAAAAT",  # 3' end = AAAAT → 0 G/C
            "rev_seq": "GCTAGCTAGCTAGCTAGCTA",
            "fwd_tm": 60.0, "rev_tm": 60.2, "tm_diff": 0.2,
            "fwd_gc": 50.0, "rev_gc": 50.0, "product_size": 150,
        }

        res = _evaluate_primer_pair_impl(
            candidate=candidate_bad_clamp, fwd_blast=fwd_blast, rev_blast=rev_blast,
            fwd_struct=fwd_struct, rev_struct=rev_struct, hetero_struct=hetero_struct,
            pcr_result=pcr_result, exon_result=exon_result,
        )

        self.assertFalse(res["pass"])
        self.assertIsNone(res["score"])
        self.assertTrue(any("GC clamp" in f for f in res["failures"]))

    def test_15_numerical_score_never_overrides_failure(self):
        """Verify that no numerical score (68, 79, 88) can override a QC failure."""
        candidate, fwd_blast, rev_blast, fwd_struct, rev_struct, _, pcr_result, exon_result = self._make_passing_inputs()
        hetero_fail = {"hetero_dimer_mfe": -8.0, "hetero_dimer_pass": False}

        res = _evaluate_primer_pair_impl(
            candidate=candidate, fwd_blast=fwd_blast, rev_blast=rev_blast,
            fwd_struct=fwd_struct, rev_struct=rev_struct, hetero_struct=hetero_fail,
            pcr_result=pcr_result, exon_result=exon_result,
        )

        # Must be FAIL regardless of what score the breakdown would have produced
        self.assertFalse(res["pass"])
        self.assertIsNone(res["score"])  # NOT SCORED, not 68 or 79 or 88

    def test_16_parameter_critic_triggered_on_failure(self):
        """Parameter adjustment is triggered when PCR fails."""
        failures = ["CRITICAL: In-Silico PCR failed — Multiple potential PCR amplicons detected."]
        current_params = {"PRIMER_MAX_SELF_ANY_TH": 45.0}

        updated_params, logs = _adjust_parameters_impl(failures, current_params)
        self.assertIn("PRIMER_MAX_SELF_ANY_TH", updated_params)
        self.assertTrue(len(logs) > 0)
        self.assertLess(updated_params["PRIMER_MAX_SELF_ANY_TH"], 45.0)

    def test_17_agent_returns_only_valid_pairs(self):
        """Agent returns only PASS pairs; never fills with FAIL candidates."""
        agent = PrimerReActAgent(max_iterations=2)
        result = agent.run(
            gene_name="BRCA1",
            organism="Homo sapiens",
            application="Standard PCR",
            num_return=3,
            skip_blast=True,
        )

        self.assertIn("validated_results", result)
        self.assertIn("reasoning_trace", result)
        self.assertLessEqual(result["state"]["iteration_count"], 2)

        # Every item in validated_results must be a PASS candidate
        for r in result["validated_results"]:
            self.assertTrue(r["pass"])
            self.assertIsNotNone(r["score"])
            self.assertGreaterEqual(r["score"], 60.0)

        # num_returned must not exceed num_requested
        self.assertLessEqual(result.get("num_returned", 0), 3)


if __name__ == "__main__":
    unittest.main()
