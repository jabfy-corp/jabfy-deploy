"""Local Deploy V1. Run from any directory with Python 3.9+."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def prepare_sources(destination):
    revisions = json.loads((ROOT / "sources.lock.json").read_text())
    for repo, sha in revisions.items():
        if not re.fullmatch(r"jabfy-[a-z]+", repo) or not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise ValueError(f"Invalid source lock for {repo}")
        target = destination / repo
        sibling = ROOT.parent / repo
        local = (sibling / ".git").exists() and subprocess.run(
            ["git", "-C", str(sibling), "cat-file", "-e", f"{sha}^{{commit}}"],
            stderr=subprocess.DEVNULL,
        ).returncode == 0
        source = str(sibling) if local else f"git@github.com:jabfy-corp/{repo}.git"
        subprocess.run(["git", "init", "-q", str(target)], check=True)
        subprocess.run(["git", "-C", str(target), "fetch", "-q", "--depth=1", source, sha], check=True)
        subprocess.run(["git", "-C", str(target), "checkout", "-q", "--detach", sha], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["config", "up", "status", "logs", "model", "down"])
    parser.add_argument("--model", default="qwen2.5:1.5b")
    args = parser.parse_args()
    env = os.environ.copy()
    if args.model.startswith("-") or not args.model.strip():
        parser.error("Invalid model name")
    compose = ["docker", "compose", "-p", env.get("COMPOSE_PROJECT_NAME", "jabfy-v1"),
               "-f", "compose.local.yml", "-f", "compose.v1.yml"]

    def run(*arguments):
        subprocess.run([*compose, *arguments], cwd=ROOT, env=env, check=True)

    if args.action == "up":
        with tempfile.TemporaryDirectory(prefix="jabfy-build-") as temp:
            env["JABFY_BUILD_ROOT"] = temp
            prepare_sources(Path(temp))
            run("build")
        run("up", "--no-build", "-d", "--wait", "--wait-timeout", "180")
        run("port", "jabfy-sim", "8080")
    elif args.action == "model":
        run("exec", "-T", "ollama", "ollama", "pull", args.model)
    elif args.action == "status":
        run("ps", "--all")
    elif args.action == "logs":
        run("logs", "--tail=100")
    elif args.action == "config":
        run("config", "--format", "json")
    else:
        run("down")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
