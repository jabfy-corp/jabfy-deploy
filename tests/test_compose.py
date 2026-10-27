"""Local orchestration contracts, without starting Docker or sibling applications."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_deploy_owns_complete_local_stack_and_preserves_existing_data():
    config = yaml.safe_load((ROOT / "compose.local.yml").read_text())
    assert config["name"] == "jabfy-simulation"  # Preserve old volumes/containers.
    services = config["services"]
    assert set(services) == {"mosquitto", "jabfy-sim", "core", "ollama"}
    sim = services["jabfy-sim"]
    assert "command" not in sim
    assert "../jabfy-simulation/data:/app/data" in sim["volumes"]
    assert "ollama-models:/root/.ollama" in services["ollama"]["volumes"]
    assert services["ollama"]["environment"]["OLLAMA_NO_CLOUD"] == "1"
    assert services["core"]["environment"]["JABFY_SIMULATION_URL"] == "http://jabfy-sim:8080"
    assert services["core"]["environment"]["JABFY_LLM_BASE_URL"] == "http://ollama:11434/v1"
    assert sim["environment"]["JABFY_CORE_URL"] == "http://core:8000"
    assert sim["depends_on"]["mosquitto"]["condition"] == "service_healthy"
    assert services["core"]["build"]["context"] == "../jabfy-core"
    assert sim["build"] == {"context": "..", "dockerfile": "jabfy-simulation/Dockerfile"}
    assert services["mosquitto"]["volumes"] == [
        "./docker/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro"
    ]
    assert (ROOT / "docker/mosquitto.conf").is_file()
    for name, service in services.items():
        assert service["restart"] == "unless-stopped"
        assert "healthcheck" in service
        assert all(port.startswith("127.0.0.1:") for port in service.get("ports", []))
        if name in {"core", "ollama"}:
            assert "ports" not in service
