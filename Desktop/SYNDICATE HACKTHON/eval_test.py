import json
from app import run_3way_matching_agent

# Test Suite Definitions
eval_dataset = [
    {
        "name": "Exact 3-Way Match",
        "po": {"contracted_unit_price": 100.0, "qty_ordered": 5},
        "grn": {"qty_received": 5},
        "invoice": {"qty_billed": 5, "unit_price": 100.0, "total_amount": 500.0},
        "expected_pass": True
    },
    {
        "name": "Quantity Shortage Detection",
        "po": {"contracted_unit_price": 100.0, "qty_ordered": 10},
        "grn": {"qty_received": 7},
        "invoice": {"qty_billed": 10, "unit_price": 100.0, "total_amount": 1000.0},
        "expected_pass": False
    }
]

def run_evals(api_key: str):
    passed_tests = 0
    total_tests = len(eval_dataset)

    print("🧪 Running Autonomous CFO Eval Suite...\n")
    for test in eval_dataset:
        result = run_3way_matching_agent(test["po"], test["grn"], test["invoice"], api_key)
        passed = result["three_way_match_pass"] == test["expected_pass"]
        
        if passed:
            passed_tests += 1
            print(f"✅ PASS: {test['name']}")
        else:
            print(f"❌ FAIL: {test['name']} (Got: {result['three_way_match_pass']}, Expected: {test['expected_pass']})")

    accuracy = (passed_tests / total_tests) * 100
    print(f"\n📊 Accuracy Benchmark: {accuracy:.1f}% ({passed_tests}/{total_tests} passed)")

if __name__ == "__main__":
    import sys
    key = sys.argv[1] if len(sys.argv) > 1 else ""
    run_evals(key)