import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import Request, urlopen
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = [sys.executable, str(ROOT / "scripts/deploy.py")]


def test_resolved_v1_compose():
    config = json.loads(subprocess.check_output([*LAUNCHER, "config"]))
    services = config["services"]
    assert set(services) == {"core", "jabfy-sim", "ollama", "mosquitto"}
    for name in ("mosquitto", "ollama"):
        assert "@sha256:" in services[name]["image"]
    mounts = services["jabfy-sim"]["volumes"]
    assert [(v["type"], v["source"], v["target"]) for v in mounts] == [
        ("volume", "home", "/app/data")
    ]
    assert all(port["host_ip"] == "127.0.0.1"
               for service in services.values() for port in service.get("ports", []))


@pytest.mark.skipif(os.getenv("JABFY_E2E") != "1", reason="set JABFY_E2E=1 to build and run containers")
def test_live_house_and_persistence():
    project = "jabfy-test-" + uuid4().hex[:12]
    env = dict(os.environ, COMPOSE_PROJECT_NAME=project, SIM_PORT="0", MQTT_PORT="0",
               JABFY_GUARD_MODE="normal")
    compose = ["docker", "compose", "-p", project, "-f", "compose.local.yml", "-f", "compose.v1.yml"]

    def run(*args):
        return subprocess.check_output(args, cwd=ROOT, env=env, text=True)

    def endpoint():
        return "http://" + run(*compose, "port", "jabfy-sim", "8080").strip()

    def api(path, body=None, method=None, timeout=30):
        data = json.dumps(body).encode() if body is not None else None
        req = Request(base + path, data=data, method=method, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=timeout) as response:
            return json.load(response)

    try:
        run(*LAUNCHER, "up")
        base = endpoint()
        state = api("/api/state")
        assert state["guard"]["enabled"] and state["stats"]["bus"]["connected"]
        inventory = json.loads(run(*compose, "exec", "-T", "core", "python", "-c",
            "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/simulation/home').read().decode())"))
        assert any(d["id"] == "kitchen_light" for d in inventory["devices"])
        home = api("/api/home")
        home["name"] = project
        api("/api/home", home, "PUT")
        assert api("/api/devices/kitchen_light/commands", {"action": "turn_on"})["status"] == "executed"
        for _ in range(20):
            lamp = next(d for d in api("/api/ai/context")["devices"] if d["id"] == "kitchen_light")
            if lamp["state"].get("state") == "ON":
                break
            time.sleep(0.25)
        assert lamp["state"]["state"] == "ON"
        if os.getenv("JABFY_E2E_MODEL") == "1":
            model = "qwen2.5:1.5b"
            run(*LAUNCHER, "model", "--model", model)
            assert model in api("/api/ai/models")["models"]
            before = api("/api/state")["stats"]["bus"]["executed"]
            proposal = api("/api/ai/propose", {
                "model": model, "prompt": "Propose uniquement d’allumer la Lampe du salon (salon_lamp).",
            }, timeout=160)
            assert proposal["commands"] == [{"device_id": "salon_lamp", "action": "turn_on", "params": {}}]
            assert api("/api/state")["stats"]["bus"]["executed"] == before
        run(*LAUNCHER, "down")
        env["JABFY_GUARD_MODE"] = "restricted"
        run(*compose, "up", "--no-build", "-d", "--wait", "--wait-timeout", "180")
        base = endpoint()
        assert api("/api/home")["name"] == project
        assert api("/api/devices/kitchen_light/commands", {"action": "turn_on"})["status"] == "rejected"
    finally:
        run(*compose, "down", "--volumes", "--rmi", "local")
