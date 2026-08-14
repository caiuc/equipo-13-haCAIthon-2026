from ia.scripts.bridge import execute


def test_scenarios_operation_keeps_json_contract():
    response = execute("scenarios", {"parameters": {}})
    assert response["success"] is True
    assert "example_network.yaml" in response["data"]["scenarios"]
    assert response["metadata"]["operation"] == "scenarios"
