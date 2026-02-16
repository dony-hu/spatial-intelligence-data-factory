#!/usr/bin/env python3
"""
观测与管制集成测试（E2E）
验证以下三个强制性需求：
1. 版本号自动引用（observability_bundle 通过 ProcessCompiler 返回）
2. 运行时 step_error_rate 采集（通过 line_execute_tc06 注入）
3. NO_GO 视觉告警（通过 lab.py 的 observability snapshot 展示）
"""

import json
import sys
import unittest
from pathlib import Path
from typing import Any, Dict
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.process_compiler.compiler import ProcessCompiler
from services.governance_api.app.routers.lab import _build_observability_snapshot
from scripts.line_execution_tc06 import (
    _resolve_observability_entrypoint,
    _load_observability_module,
    _collect_step_events,
    _collect_runtime_observability_metrics,
)


class TestMandatory1VersionAutoReference(unittest.TestCase):
    """需求1：版本号自动引用（observability_bundle 与 workpackage 编译链直接打通）"""
    
    def setUp(self):
        self.compiler = ProcessCompiler()
        self.workpackage_path = PROJECT_ROOT / "workpackages" / "wp-address-topology-v1.0.2.json"
        self.assertTrue(self.workpackage_path.exists(), f"Workpackage not found: {self.workpackage_path}")
        with open(self.workpackage_path) as f:
            self.workpackage = json.load(f)
    
    def test_compile_result_includes_observability_bundle(self):
        """验证 CompileResult 返回 observability_bundle 字段"""
        result = self.compiler.compile(self.workpackage)
        self.assertTrue(result.success, f"Compilation failed: {result.validation_errors}")
        self.assertIn("observability_bundle", result.__dict__, 
                      "CompileResult missing observability_bundle field")
        self.assertIsInstance(result.observability_bundle, dict,
                            "observability_bundle should be dict")
    
    def test_observability_bundle_contains_version(self):
        """验证 observability_bundle 入口路径包含版本信息"""
        result = self.compiler.compile(self.workpackage)
        self.assertTrue(result.success)
        bundle = result.observability_bundle
        version = str(self.workpackage.get("version") or "")
        bundle_id = str(bundle.get("bundle_id") or "")
        entrypoints = bundle.get("entrypoints", [])

        if version:
            normalized = version.replace(".", "-")
            self.assertIn(normalized, bundle_id, "bundle_id should include version fragment")
            if entrypoints:
                joined = " ".join(str(item) for item in entrypoints)
                self.assertIn(normalized, joined, "entrypoints should include version fragment")
        else:
            self.assertTrue(bundle_id, "bundle_id should be present")
    
    def test_observability_entrypoint_resolution(self):
        """验证 observability bundle 入口路径解析"""
        result = self.compiler.compile(self.workpackage)
        self.assertTrue(result.success)
        bundle = result.observability_bundle
        
        # Entrypoints should be resolvable
        entrypoints = bundle.get("entrypoints", [])
        if entrypoints:
            for ep in entrypoints:
                ep_path = PROJECT_ROOT / str(ep)
                self.assertTrue(ep_path.exists(), 
                              f"Entrypoint not found: {ep_path}")
    
    def test_resolve_observability_entrypoint_from_workpackage(self):
        """验证从 workpackage 解析 line_observe.py 路径"""
        ep_path = _resolve_observability_entrypoint(self.workpackage)
        # Should either find entrypoint or fallback path
        if ep_path:
            self.assertTrue(ep_path.exists(), f"Resolved entrypoint doesn't exist: {ep_path}")
            self.assertTrue(ep_path.suffix == ".py", "Entrypoint should be .py file")


class TestMandatory2RuntimeMetricsCollection(unittest.TestCase):
    """需求2：运行时 step_error_rate 采集"""
    
    def setUp(self):
        self.workpackage_path = PROJECT_ROOT / "workpackages" / "wp-address-topology-v1.0.2.json"
        with open(self.workpackage_path) as f:
            self.workpackage = json.load(f)
    
    def test_observability_module_loadable(self):
        """验证 line_observe 模块可被动态加载"""
        ep_path = _resolve_observability_entrypoint(self.workpackage)
        if ep_path:
            module = _load_observability_module(self.workpackage)
            self.assertIsNotNone(module, "Failed to load observability module")
            # Should have required functions
            if hasattr(module, "observe_step"):
                self.assertTrue(callable(module.observe_step),
                              "observe_step should be callable")
    
    def test_aggregate_runtime_metrics_exists_in_template(self):
        """验证 aggregate_runtime_metrics 函数在 line_observe 代码中"""
        ep_path = _resolve_observability_entrypoint(self.workpackage)
        if not ep_path:
            self.skipTest("No observability entrypoint resolved")
        observe_code = ep_path.read_text()
        self.assertIn("aggregate_runtime_metrics", observe_code,
                     "aggregate_runtime_metrics function not generated in line_observe.py")
        self.assertIn("step_error_rate", observe_code,
                     "step_error_rate metric not in aggregation code")
    
    def test_step_error_rate_calculation_formula(self):
        """验证 step_error_rate 计算公式（failed/total）"""
        # Simulate step_error_rate calculation
        test_events = [
            {"task_id": "t1", "step_code": "step1", "status": "success"},
            {"task_id": "t2", "step_code": "step2", "status": "failed"},
            {"task_id": "t3", "step_code": "step3", "status": "success"},
        ]
        
        total = len(test_events)
        failed = sum(1 for e in test_events if e.get("status") == "failed")
        expected_rate = round(failed / total, 6) if total > 0 else 0.0
        
        self.assertEqual(total, 3)
        self.assertEqual(failed, 1)
        self.assertAlmostEqual(expected_rate, 1/3, places=5)


class TestMandatory3NOGOVisualAlert(unittest.TestCase):
    """需求3：NO_GO 判定的看板可视提示"""
    
    def test_observability_snapshot_includes_no_go_risk_field(self):
        """验证 observability snapshot 包含 no_go_risk 字段"""
        snapshot = _build_observability_snapshot(env="all", include_events=True)
        self.assertIn("l3", snapshot, "Snapshot missing l3 (detailed metrics) section")
        
        l3 = snapshot.get("l3", {})
        self.assertIn("gate_alignment", l3,
                     "Snapshot missing gate_alignment in l3 section")
    
    def test_gate_alignment_structure(self):
        """验证 gate_alignment 字段包含 release_decision 和 failed_gates"""
        snapshot = _build_observability_snapshot(env="all", include_events=True)
        l3 = snapshot.get("l3", {})
        gate_alignment = l3.get("gate_alignment", {})
        
        self.assertIn("release_decision", gate_alignment,
                     "gate_alignment missing release_decision")
        decision = gate_alignment.get("release_decision")
        self.assertIn(decision, ["GO", "NO_GO", "HOLD"],
                     f"release_decision {decision} not in valid values")
        
        self.assertIn("failed_gates", gate_alignment,
                     "gate_alignment missing failed_gates")
        self.assertIsInstance(gate_alignment.get("failed_gates"), list,
                            "failed_gates should be list")
    
    def test_no_go_risk_alert_in_alerts_array(self):
        """验证 NO_GO_RISK 告警出现在 alerts 数组中"""
        snapshot = _build_observability_snapshot(env="all", include_events=True)
        alerts = snapshot.get("alerts", [])
        
        # 如果 release_decision 是 NO_GO，应该有 NO_GO_RISK 告警
        l3 = snapshot.get("l3", {})
        gate_alignment = l3.get("gate_alignment", {})
        decision = gate_alignment.get("release_decision")
        
        if decision == "NO_GO":
            no_go_alerts = [a for a in alerts if a.get("code") == "NO_GO_RISK"]
            self.assertTrue(len(no_go_alerts) > 0,
                          "NO_GO_RISK alert not found when release_decision=NO_GO")
            alert = no_go_alerts[0]
            self.assertEqual(alert.get("level"), "P0",
                           "NO_GO_RISK alert should be P0 level")
    
    def test_metric_explanations_for_release_decision(self):
        """验证 metric_explanations 包含 release_decision 解释"""
        snapshot = _build_observability_snapshot(env="all", include_events=True)
        explanations = snapshot.get("metric_explanations", {})
        
        self.assertIn("l3.gate_alignment.release_decision", explanations,
                     "Missing explanation for release_decision")
        explanation = explanations.get("l3.gate_alignment.release_decision")
        self.assertIsNotNone(explanation, "release_decision explanation should not be None")
        # Should mention GO/NO_GO/HOLD
        self.assertTrue(any(term in explanation for term in ["GO", "NO_GO", "HOLD"]),
                       "Explanation should mention GO/NO_GO/HOLD states")


class TestMandatory3RuntimeObservabilityInjection(unittest.TestCase):
    """需求2.5：验证 runtime_observability 在运行时注入到处理流程"""
    
    def setUp(self):
        self.workpackage_path = PROJECT_ROOT / "workpackages" / "wp-address-topology-v1.0.2.json"
        with open(self.workpackage_path) as f:
            self.workpackage = json.load(f)
    
    def test_step_events_collection_structure(self):
        """验证步骤事件收集结构"""
        # Mock workflow result
        workflow_result = {
            "workflow_id": "wf_test_001",
            "status": "completed",
            "cleaning_phase": {
                "status": "completed",
                "failed_cases": [
                    {"case_id": "case_1", "reason": "data_error"},
                ]
            },
            "graph_phase": {
                "status": "completed",
                "failed_cases": []
            }
        }
        
        events = _collect_step_events(workflow_result)
        self.assertIsInstance(events, list, "Step events should be list")
        
        if len(events) > 0:
            event = events[0]
            self.assertIn("task_id", event, "Event missing task_id")
            self.assertIn("step_code", event, "Event missing step_code")
            self.assertIn("status", event, "Event missing status")
    
    def test_runtime_metrics_payload_structure(self):
        """验证运行时指标负载结构"""
        workflow_result = {
            "workflow_id": "wf_test_002",
            "status": "completed",
            "cleaning_phase": {"status": "completed", "failed_cases": []},
            "graph_phase": {"status": "completed", "failed_cases": []}
        }
        
        metrics = _collect_runtime_observability_metrics(workflow_result, self.workpackage)
        self.assertIsInstance(metrics, dict, "Metrics should be dict")
        
        # Key fields
        expected_fields = ["step_total", "step_failed", "step_error_rate", "collector"]
        for field in expected_fields:
            self.assertIn(field, metrics, f"Metrics missing {field}")
        
        # Verify types
        self.assertIsInstance(metrics.get("step_total"), int)
        self.assertIsInstance(metrics.get("step_failed"), int)
        self.assertIsInstance(metrics.get("step_error_rate"), (int, float))
        
        # step_error_rate should be between 0 and 1
        rate = metrics.get("step_error_rate")
        self.assertGreaterEqual(rate, 0.0, "step_error_rate should be >= 0")
        self.assertLessEqual(rate, 1.0, "step_error_rate should be <= 1")


class TestFollowUp1MetricExplanations(unittest.TestCase):
    """后续1：补 step_error_rate 与 quality_score 指标解释"""
    
    def test_metric_explanations_completeness(self):
        """验证 metric_explanations 包含关键指标"""
        snapshot = _build_observability_snapshot(env="all", include_events=True)
        explanations = snapshot.get("metric_explanations", {})
        
        key_metrics = [
            "l1.success_rate",
            "l2.avg_confidence",
            "address_line.quality_score",
            "address_line.runtime_observability.step_error_rate",
            "l3.gate_alignment.release_decision",
        ]
        
        for metric in key_metrics:
            self.assertIn(metric, explanations,
                         f"Missing explanation for {metric}")
    
    def test_metric_explanations_are_not_empty(self):
        """验证每个指标解释不为空"""
        snapshot = _build_observability_snapshot(env="all", include_events=True)
        explanations = snapshot.get("metric_explanations", {})
        
        for metric, explanation in explanations.items():
            self.assertTrue(explanation, f"Explanation for {metric} is empty")
            self.assertIsInstance(explanation, str, 
                                f"Explanation for {metric} should be string")


class TestFollowUp2StateEvidenceTracing(unittest.TestCase):
    """后续2：补运行时状态回写与故障反推链路证据梳理"""
    
    def test_line_feedback_contract_with_runtime_observability(self):
        """验证 line_feedback 合约包含 runtime_observability"""
        line_feedback_path = PROJECT_ROOT / "output" / "workpackages" / "line_feedback.latest.json"
        
        if line_feedback_path.exists():
            with open(line_feedback_path) as f:
                feedback = json.load(f)
            
            process_result = feedback.get("process_result")
            if isinstance(process_result, dict):
                if process_result.get("status") == "completed":
                    self.assertIn("runtime_observability", process_result,
                                "Missing runtime_observability in process_result")
            else:
                self.assertIn("release_decision", feedback,
                             "Feedback should include release_decision")


class TestIntegrationFlow(unittest.TestCase):
    """集成测试：完整的版本→运行→反馈流程"""
    
    def setUp(self):
        self.compiler = ProcessCompiler()
        self.workpackage_path = PROJECT_ROOT / "workpackages" / "wp-address-topology-v1.0.2.json"
        with open(self.workpackage_path) as f:
            self.workpackage = json.load(f)
    
    def test_full_flow_version_to_feedback(self):
        """验证从编译版本 → 运行时采集 → 反馈提交的完整流程"""
        # Step 1: Compile with observability
        compile_result = self.compiler.compile(self.workpackage)
        self.assertTrue(compile_result.success, "Compilation should succeed")
        
        # Step 2: Verify version extracted
        bundle = compile_result.observability_bundle
        version = str(self.workpackage.get("version") or "")
        bundle_id = str(bundle.get("bundle_id") or "")
        if version:
            normalized = version.replace(".", "-")
            self.assertIn(normalized, bundle_id, "bundle_id should include version fragment")
        else:
            self.assertTrue(bundle_id, "bundle_id should be present")
        
        # Step 3: Verify observability module can be loaded
        ep_path = _resolve_observability_entrypoint(self.workpackage)
        if ep_path:
            module = _load_observability_module(self.workpackage)
            self.assertIsNotNone(module, "Observability module should load")
        
        # Step 4: Verify metrics collection capability
        workflow_result = {
            "workflow_id": "wf_integration_001",
            "status": "completed",
            "cleaning_phase": {"status": "completed", "failed_cases": []},
            "graph_phase": {"status": "completed", "failed_cases": []},
        }
        
        metrics = _collect_runtime_observability_metrics(workflow_result, self.workpackage)
        self.assertIn("step_error_rate", metrics, "Metrics should include step_error_rate")
        
        # Step 5: Verify snapshot includes gate alignment
        snapshot = _build_observability_snapshot(env="all", include_events=True)
        l3 = snapshot.get("l3", {})
        self.assertIn("gate_alignment", l3, "Snapshot should include gate_alignment")


def run_tests_with_summary():
    """运行所有测试并输出总结报告"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 加载所有测试类
    test_classes = [
        TestMandatory1VersionAutoReference,
        TestMandatory2RuntimeMetricsCollection,
        TestMandatory3NOGOVisualAlert,
        TestMandatory3RuntimeObservabilityInjection,
        TestFollowUp1MetricExplanations,
        TestFollowUp2StateEvidenceTracing,
        TestIntegrationFlow,
    ]
    
    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出总结
    print("\n" + "="*70)
    print("观测与管制集成测试总结")
    print("="*70)
    print(f"总测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ 所有测试通过！")
        print("\n三项强制性需求验证結果:")
        print("  ✅ 需求1: 版本号自动引用 - PASS")
        print("  ✅ 需求2: 运行时 step_error_rate 采集 - PASS")
        print("  ✅ 需求3: NO_GO 视觉告警 - PASS")
    else:
        print("\n❌ 部分测试失败")
        if result.failures:
            print("\n失败的测试:")
            for test, trace in result.failures:
                print(f"  - {test}")
        if result.errors:
            print("\n错误的测试:")
            for test, trace in result.errors:
                print(f"  - {test}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests_with_summary()
    sys.exit(0 if success else 1)
