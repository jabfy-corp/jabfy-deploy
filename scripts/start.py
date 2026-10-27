"""Orchestrate the local V0.0.1 stack from jabfy-deploy and four sibling checkouts."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-ai", action="store_true", help="Do not download a model; manual controls still work")
    parser.add_argument("--model", default="qwen2.5:1.5b", help="Ollama model to download on first use")
    parser.add_argument("--check", action="store_true", help="Check sources and Compose without starting services")
    args = parser.parse_args()
    required = {
        "jabfy-core/app/api/routes_simulation.py": "propose_simulation",
        "jabfy-core/Dockerfile": "FROM",
        "jabfy-bus/jabfy_bus/verification/engine.py": "consume_approval",
        "jabfy-guard/src/jabfy_guard/models.py": "allow_sensitive_simulation",
        "jabfy-simulation/Dockerfile": "FROM",
        "jabfy-simulation/sim/dashboard/guard.py": "HomeGuard",
    }
    for relative, marker in required.items():
        path = ROOT.parent / relative
        if not path.is_file() or marker not in path.read_text(encoding="utf-8"):
            parser.exit(1, f"Missing compatible V0.0.1 checkout: {path}. See docs/v0.0.1.md.\n")
    if not shutil.which("docker"):
        parser.exit(1, "Docker and Compose are required.\n")
    compose = ["docker", "compose", "-f", "compose.local.yml"]
    try:
        subprocess.run([*compose, "config", "--quiet"], cwd=ROOT, check=True)
        if args.check:
            print("V0.0.1 sources and Compose configuration OK (runtime not tested).")
            return
        subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, check=True)
        subprocess.run([*compose, "up", "--build", "-d", "--wait", "--wait-timeout", "180"], cwd=ROOT, check=True)
        if not args.no_ai:
            print(f"Installing {args.model}; first download may take several minutes.", flush=True)
            subprocess.run([*compose, "exec", "-T", "ollama", "ollama", "pull", args.model], cwd=ROOT, check=True)
        print(f"Jabfy V0.0.1: http://127.0.0.1:{os.getenv('SIM_PORT', '8080')}")
        print("Manual controls ready. Refresh the AI model list to use a downloaded model.")
    except subprocess.CalledProcessError as exc:
        parser.exit(1, f"Startup incomplete (exit {exc.returncode}). Check Docker and docker compose -f compose.local.yml logs in jabfy-deploy. Data is retained.\n")


if __name__ == "__main__":
    main()
