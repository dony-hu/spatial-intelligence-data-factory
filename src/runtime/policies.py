from typing import Dict, List


def check_required_approvals(required: List[str], approved: List[str]) -> Dict:
    approved_set = set(approved)
    missing = [item for item in required if item not in approved_set]
    return {
        "pass": len(missing) == 0,
        "required": required,
        "approved": approved,
        "missing": missing,
    }
