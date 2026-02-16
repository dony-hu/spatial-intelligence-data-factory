import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WP_V101 = PROJECT_ROOT / "workpackages" / "wp-address-topology-v1.0.1.json"
WP_V102 = PROJECT_ROOT / "workpackages" / "wp-address-topology-v1.0.2.json"
DEMO_SAMPLES = (
    PROJECT_ROOT / "workpackages" / "bundles" / "address-topology-v1.0.2" / "demo" / "fixed_demo_samples.v1.json"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class AddressTopologyContractAlignmentTests(unittest.TestCase):
    def test_v101_v102_algorithm_and_contract_alignment(self):
        wp101 = _load_json(WP_V101)
        wp102 = _load_json(WP_V102)

        self.assertEqual(wp101["input_contract"], wp102["input_contract"])
        self.assertEqual(
            wp101["process_spec"]["steps"],
            wp102["process_spec"]["steps"],
        )
        self.assertIn("质量阈值>=0.95", wp101["line_spec"]["constraints"])
        self.assertIn("质量阈值>=0.95", wp102["line_spec"]["constraints"])

        self.assertEqual(
            wp101["line_feedback_contract"]["failure_queue_snapshot_ref"],
            wp102["line_feedback_contract"]["failure_queue_snapshot_ref"],
        )
        self.assertEqual(
            wp101["line_feedback_contract"]["replay_result_ref"],
            wp102["line_feedback_contract"]["replay_result_ref"],
        )

        required_base = ["standard_address", "topology_nodes", "topology_edges", "quality_score"]
        for field in required_base:
            self.assertIn(field, wp101["output_contract"]["required"])
            self.assertIn(field, wp102["output_contract"]["required"])

    def test_fixed_demo_samples_cover_success_failure_replay(self):
        wp102 = _load_json(WP_V102)
        samples_doc = _load_json(DEMO_SAMPLES)
        samples = samples_doc["samples"]

        self.assertEqual(len(samples), 3)
        self.assertEqual({item["scenario"] for item in samples}, {"success", "failure", "replay"})

        by_scenario = {item["scenario"]: item for item in samples}
        success = by_scenario["success"]
        failure = by_scenario["failure"]
        replay = by_scenario["replay"]

        self.assertGreaterEqual(success["expected"]["quality_score_min"], 0.95)
        self.assertEqual(
            failure["expected"]["queue_ref"],
            wp102["line_feedback_contract"]["failure_queue_snapshot_ref"],
        )
        self.assertEqual(
            replay["expected"]["report_ref"],
            wp102["line_feedback_contract"]["replay_result_ref"],
        )
        self.assertEqual(replay["replay_of"], failure["sample_id"])


if __name__ == "__main__":
    unittest.main()
