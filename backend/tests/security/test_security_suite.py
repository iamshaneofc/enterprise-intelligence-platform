"""Pytest test suite executing Promptfoo security tests deterministically.

Ensures that security assertions from `promptfooconfig.yaml` are executed
as part of automated CI without requiring external node binaries.
"""
import pytest
import yaml
from pathlib import Path
from backend.tests.security.promptfoo_provider import call_api


def load_promptfoo_tests():
    """Load test cases defined in promptfooconfig.yaml."""
    config_path = Path(__file__).parent / "promptfooconfig.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config.get("tests", [])


@pytest.mark.parametrize("test_case", load_promptfoo_tests(), ids=lambda t: t.get("description", "security_test"))
def test_promptfoo_security_spec(test_case):
    """Execute a single Promptfoo security test case and evaluate assertions."""
    desc = test_case.get("description")
    vars_dict = test_case.get("vars", {})
    query = vars_dict.get("query", "")
    asserts = test_case.get("assert", [])

    # Call the security provider
    res = call_api(prompt=query, context={"vars": vars_dict})
    assert "error" not in res, f"Provider execution error for test '{desc}': {res.get('error')}"

    output = res.get("output", "")
    output_lower = output.lower()

    for assertion in asserts:
        assert_type = assertion.get("type")
        expected_value = assertion.get("value")

        if assert_type == "icontains":
            assert expected_value.lower() in output_lower, (
                f"[{desc}] Failed 'icontains': Expected '{expected_value}' in output.\nGot: {output}"
            )
        elif assert_type == "not-icontains":
            assert expected_value.lower() not in output_lower, (
                f"[{desc}] Failed 'not-icontains': Forbidden text '{expected_value}' found in output.\nGot: {output}"
            )
        elif assert_type == "contains":
            assert expected_value in output, (
                f"[{desc}] Failed 'contains': Expected '{expected_value}' in output.\nGot: {output}"
            )
        elif assert_type == "not-contains":
            assert expected_value not in output, (
                f"[{desc}] Failed 'not-contains': Forbidden text '{expected_value}' found in output.\nGot: {output}"
            )
        else:
            pytest.fail(f"Unsupported assertion type: {assert_type}")

