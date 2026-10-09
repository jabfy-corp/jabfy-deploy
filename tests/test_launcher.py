from pathlib import Path
import runpy
import subprocess
import sys
from unittest.mock import Mock

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "start.py"


@pytest.mark.parametrize("args,download", [(["--no-ai"], False), ([], True)])
def test_launcher_builds_waits_and_only_downloads_when_requested(monkeypatch, args, download):
    module = runpy.run_path(str(SCRIPT))
    run = Mock()
    monkeypatch.setattr(module["subprocess"], "run", run)
    monkeypatch.setattr(module["shutil"], "which", lambda name: "/bin/docker")
    monkeypatch.setattr(Path, "is_file", lambda self: True)
    monkeypatch.setattr(Path, "read_text", lambda *a, **kw:
                        "propose_simulation FROM consume_approval allow_sensitive_simulation HomeGuard")
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), *args])
    module["main"]()
    commands = [call.args[0] for call in run.call_args_list]
    assert ["docker", "compose", "-f", "compose.local.yml", "up", "--build", "-d", "--wait", "--wait-timeout", "180"] in commands
    for call in run.call_args_list:
        if call.args[0][:2] == ["docker", "compose"]:
            assert call.kwargs["cwd"] == SCRIPT.parents[1].resolve()
    assert any("pull" in command for command in commands) is download


def test_launcher_stops_when_docker_is_unavailable(monkeypatch):
    module = runpy.run_path(str(SCRIPT))
    run = Mock(side_effect=[None, subprocess.CalledProcessError(1, "docker info")])
    monkeypatch.setattr(module["subprocess"], "run", run)
    monkeypatch.setattr(module["shutil"], "which", lambda name: "/bin/docker")
    monkeypatch.setattr(Path, "is_file", lambda self: True)
    monkeypatch.setattr(Path, "read_text", lambda *a, **kw:
                        "propose_simulation FROM consume_approval allow_sensitive_simulation HomeGuard")
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    with pytest.raises(SystemExit) as error:
        module["main"]()
    assert error.value.code == 1
    assert run.call_count == 2
    assert run.call_args.args[0] == ["docker", "info"]


def test_check_never_starts_services_or_downloads_model(monkeypatch):
    module = runpy.run_path(str(SCRIPT))
    run = Mock()
    monkeypatch.setattr(module["subprocess"], "run", run)
    monkeypatch.setattr(module["shutil"], "which", lambda name: "/bin/docker")
    monkeypatch.setattr(Path, "is_file", lambda self: True)
    monkeypatch.setattr(Path, "read_text", lambda *a, **kw:
                        "propose_simulation FROM consume_approval allow_sensitive_simulation HomeGuard")
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--check"])
    module["main"]()
    assert run.call_count == 1
    assert run.call_args.args[0] == ["docker", "compose", "-f", "compose.local.yml", "config", "--quiet"]


def test_missing_checkout_never_starts_docker(monkeypatch):
    module = runpy.run_path(str(SCRIPT))
    run = Mock()
    monkeypatch.setattr(module["subprocess"], "run", run)
    monkeypatch.setattr(Path, "is_file", lambda self: False)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    with pytest.raises(SystemExit) as error:
        module["main"]()
    assert error.value.code == 1
    run.assert_not_called()
