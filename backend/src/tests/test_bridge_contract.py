from ia.scripts.bridge import execute


def test_scenarios_contract_uses_structured_response():
    response = execute("scenarios", {"simulationId": "sim-test", "parameters": {}})
    assert response["success"] is True
    assert "example_network.yaml" in response["data"]["scenarios"]
    assert response["metadata"]["operation"] == "scenarios"
    assert response["metadata"]["simulationId"] == "sim-test"
