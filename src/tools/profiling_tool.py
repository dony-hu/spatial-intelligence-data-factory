from typing import Dict, List


class ProfilingTool:
    """Generate lightweight profiling report from TaskSpec context."""

    def run(self, task_spec: Dict) -> Dict:
        context = task_spec.get("context", {})
        sources: List[str] = context.get("data_sources", [])

        details = []
        for src in sources:
            details.append(
                {
                    "source": src,
                    "record_count": 100,
                    "null_ratio": 0.01,
                    "schema_drift": False,
                }
            )

        return {
            "source_count": len(sources),
            "sources": details,
            "quality_summary": {
                "max_null_ratio": max([d["null_ratio"] for d in details], default=0.0),
                "has_schema_drift": any(d["schema_drift"] for d in details),
            },
        }
