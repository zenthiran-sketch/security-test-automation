#!/usr/bin/env python3
"""
Arena Console one-command launcher.

Installs Python + frontend dependencies, best-effort installs security CLIs,
then starts the API (8888) and Vite frontend (5173).

Usage:
    python start.py
    python start.py --skip-tools      # skip security CLI install attempts
    python start.py --full            # also pip install full requirements.txt
    python start.py --no-browser      # do not open the browser
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
VENV_DIR = ROOT / ".venv"
MARKER = ROOT / ".hexstrike_setup_done"

# Go packages used by the web catalog (installable without Kali)
GO_TOOLS = [
    "github.com/projectdiscovery/httpx/cmd/httpx@latest",
    "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
    "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
    "github.com/projectdiscovery/katana/cmd/katana@latest",
    "github.com/ffuf/ffuf/v2@latest",
    "github.com/OJ/gobuster/v3@latest",
    "github.com/lc/gau/v2/cmd/gau@latest",
    "github.com/tomnomnom/waybackurls@latest",
    "github.com/hakluke/hakrawler@latest",
    "github.com/hahwul/dalfox/v2@latest",
    "github.com/jaeles-project/jaeles@latest",
    "github.com/projectdiscovery/naabu/v2/cmd/naabu@latest",
]


def info(msg: str) -> None:
    print(f"[arena] {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"[arena] WARNING: {msg}", flush=True)


def fail(msg: str) -> None:
    print(f"[arena] ERROR: {msg}", flush=True)
    sys.exit(1)


def _needs_shell(cmd: list[str]) -> bool:
    """npm/npx are .cmd shims on Windows and require shell=True."""
    if sys.platform != "win32" or not cmd:
        return False
    exe = str(cmd[0]).lower()
    return exe in ("npm", "npx", "yarn", "pnpm") or exe.endswith((".cmd", ".bat"))


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True, env=None) -> int:
    info("$ " + " ".join(str(c) for c in cmd))
    use_shell = _needs_shell(cmd)
    result = subprocess.run(
        cmd if not use_shell else subprocess.list2cmdline(cmd),
        cwd=str(cwd or ROOT),
        env=env,
        shell=use_shell,
    )
    if check and result.returncode != 0:
        fail(f"Command failed ({result.returncode}): {' '.join(str(c) for c in cmd)}")
    return result.returncode


def which_python() -> str:
    return sys.executable


def venv_python() -> Path:
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def venv_pip() -> Path:
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "pip.exe"
    return VENV_DIR / "bin" / "pip"


def ensure_venv() -> Path:
    py = venv_python()
    if py.exists():
        info(f"Using existing venv: {VENV_DIR}")
        return py
    info("Creating Python virtual environment (.venv)…")
    run([which_python(), "-m", "venv", str(VENV_DIR)])
    if not py.exists():
        fail("Failed to create virtual environment")
    return py


def install_python_deps(py: Path, full: bool) -> None:
    req = ROOT / ("requirements.txt" if full else "requirements-core.txt")
    info(f"Installing Python packages from {req.name}…")
    run([str(py), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], check=False)
    code = run([str(py), "-m", "pip", "install", "-r", str(req)], check=False)
    if code != 0 and not full:
        warn("Core install had issues — retrying core set package-by-package")
        for line in req.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            run([str(py), "-m", "pip", "install", line.split("#")[0].strip()], check=False)
    elif code != 0 and full:
        warn("Full requirements failed; falling back to requirements-core.txt")
        run([str(py), "-m", "pip", "install", "-r", str(ROOT / "requirements-core.txt")], check=False)

    # Optional extras — never block startup
    for pkg in ("mitmproxy>=9.0.0,<11.0.0", "fastmcp>=0.2.0,<1.0.0"):
        run([str(py), "-m", "pip", "install", pkg], check=False)


def ensure_node() -> None:
    if not shutil.which("npm"):
        fail("Node.js/npm not found. Install from https://nodejs.org/ and re-run: python start.py")
    if not shutil.which("node"):
        fail("Node.js not found. Install from https://nodejs.org/ and re-run: python start.py")
    info(f"Node: {subprocess.check_output(['node', '-v'], text=True).strip()}")
    npm_ver = subprocess.check_output(
        "npm -v" if sys.platform == "win32" else ["npm", "-v"],
        text=True,
        shell=(sys.platform == "win32"),
    ).strip()
    info(f"npm:  {npm_ver}")


def install_frontend() -> None:
    ensure_node()
    if not FRONTEND.exists():
        fail(f"frontend/ folder missing at {FRONTEND}")
    marker = FRONTEND / "node_modules" / ".package-lock.json"
    lock = FRONTEND / "package-lock.json"
    if (FRONTEND / "node_modules").exists() and lock.exists():
        info("Frontend node_modules present — running npm install to sync…")
    else:
        info("Installing frontend dependencies (npm install)…")
    run(["npm", "install"], cwd=FRONTEND)


def _portable_go_root() -> Path | None:
    """User-local Go install (no admin) used by this launcher."""
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "hexstrike-go" / "go",
        Path.home() / "hexstrike-go" / "go",
    ]
    for root in candidates:
        if (root / "bin" / ("go.exe" if sys.platform == "win32" else "go")).exists():
            return root
    return None


def _go_env() -> tuple[str | None, dict]:
    """Resolve go binary + env with GOROOT/GOPATH/GOBIN on PATH."""
    env = os.environ.copy()
    portable = _portable_go_root()
    go = shutil.which("go")
    if portable:
        env["GOROOT"] = str(portable)
        go_bin = str(portable / "bin")
        env["PATH"] = go_bin + os.pathsep + env.get("PATH", "")
        go = str(portable / "bin" / ("go.exe" if sys.platform == "win32" else "go"))
    if not go:
        return None, env
    gopath = env.get("GOPATH") or str(Path.home() / "go")
    gobin = str(Path(gopath) / "bin")
    env["GOPATH"] = gopath
    env["GOBIN"] = gobin
    Path(gobin).mkdir(parents=True, exist_ok=True)
    env["PATH"] = gobin + os.pathsep + env.get("PATH", "")
    return go, env


def install_go_tools() -> None:
    go, env = _go_env()
    if not go:
        warn("Go toolchain not installed — skipping Go-based security tools (httpx, nuclei, …)")
        warn("Install Go from https://go.dev/dl/ (or let start.py fetch portable Go) then re-run")
        return
    gobin = env.get("GOBIN", str(Path.home() / "go" / "bin"))
    info(f"Installing Go-based security CLIs into {gobin} …")
    for mod in GO_TOOLS:
        run([go, "install", mod], check=False, env=env)
    info(f"Go tools bin: {gobin}")


def install_python_security_tools(py: Path) -> None:
    """Pip-installable scanners that don't need native Go/apt."""
    info("Installing pip-based security tools (sqlmap, wafw00f, …)…")
    for pkg in (
        "sqlmap",
        "wafw00f",
        "wfuzz",
        "uro",
        "arjun",
        "dirsearch",
    ):
        run([str(py), "-m", "pip", "install", "-U", pkg], check=False)


def install_system_tools() -> None:
    """Best-effort install of CLI scanners via apt / brew / winget / chocolatey."""
    if sys.platform.startswith("linux") and shutil.which("apt-get"):
        info("Attempting apt install of common scanners (may need sudo)…")
        pkgs = [
            "nmap", "nikto", "sqlmap", "dirb", "gobuster", "ffuf", "whatweb",
            "dnsutils", "whois",
        ]
        # Prefer sudo when available
        if shutil.which("sudo"):
            run(["sudo", "apt-get", "update", "-y"], check=False)
            run(["sudo", "apt-get", "install", "-y"] + pkgs, check=False)
        else:
            run(["apt-get", "update", "-y"], check=False)
            run(["apt-get", "install", "-y"] + pkgs, check=False)
        return

    if sys.platform == "darwin" and shutil.which("brew"):
        info("Attempting brew install of common scanners…")
        for pkg in ("nmap", "nikto", "sqlmap", "gobuster", "ffuf"):
            run(["brew", "install", pkg], check=False)
        return

    if sys.platform == "win32":
        if shutil.which("winget"):
            info("Attempting winget install of nmap (best-effort)…")
            run(
                [
                    "winget", "install", "-e", "--id", "Insecure.Nmap",
                    "--accept-package-agreements", "--accept-source-agreements",
                ],
                check=False,
            )
        elif shutil.which("choco"):
            info("Attempting chocolatey install of nmap…")
            run(["choco", "install", "nmap", "-y"], check=False)
        else:
            warn("On Windows, install scanners yourself (WSL/Kali recommended) or install Go for ProjectDiscovery tools.")


def print_tool_status() -> None:
    from server.tool_registry import TOOL_REGISTRY, is_tool_available

    available = [n for n in TOOL_REGISTRY if is_tool_available(n)]
    missing = [n for n in TOOL_REGISTRY if n not in available]
    info(f"Security tools on PATH: {len(available)}/{len(TOOL_REGISTRY)}")
    if available:
        info("Available: " + ", ".join(sorted(available)))
    if missing:
        warn("Missing (will be skipped during scans): " + ", ".join(sorted(missing)))


def wait_for_port(host: str, port: int, timeout: float = 60.0) -> bool:
    import socket

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.4)
    return False


def start_processes(py: Path, open_browser: bool) -> None:
    _, env = _go_env()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    # Prefer Go bin + venv Scripts (pip console scripts: sqlmap, wafw00f, …)
    gobin = Path(env.get("GOBIN") or (Path.home() / "go" / "bin"))
    path_parts = [str(gobin)]
    if sys.platform == "win32":
        path_parts.append(str(Path(py).parent))  # .venv\Scripts
    else:
        path_parts.append(str(Path(py).parent))
    portable = _portable_go_root()
    if portable:
        path_parts.insert(0, str(portable / "bin"))
    env["PATH"] = os.pathsep.join(path_parts) + os.pathsep + env.get("PATH", "")

    info("Starting API server on http://127.0.0.1:8888 …")
    api = subprocess.Popen(
        [str(py), "hexstrike_server.py", "--port", "8888"],
        cwd=str(ROOT),
        env=env,
    )

    if not wait_for_port("127.0.0.1", 8888, timeout=90):
        api.terminate()
        fail("API server did not become ready on port 8888. Check hexstrike.log")

    info("API is up. Starting frontend on http://localhost:5173 …")
    if sys.platform == "win32":
        front = subprocess.Popen(
            f'npm run dev -- --host 127.0.0.1 --port 5173',
            cwd=str(FRONTEND),
            env=env,
            shell=True,
        )
    else:
        front = subprocess.Popen(
            ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"],
            cwd=str(FRONTEND),
            env=env,
        )

    if not wait_for_port("127.0.0.1", 5173, timeout=90):
        front.terminate()
        api.terminate()
        fail("Frontend did not become ready on port 5173")

    url = "http://localhost:5173"
    info("=" * 60)
    info("Arena Console is ready")
    info(f"  UI:  {url}")
    info(f"  API: http://127.0.0.1:8888/health")
    info("Press Ctrl+C to stop both servers")
    info("=" * 60)

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    def shutdown(*_args):
        info("Shutting down…")
        for proc in (front, api):
            try:
                if sys.platform == "win32":
                    proc.terminate()
                else:
                    proc.send_signal(signal.SIGTERM)
            except Exception:
                pass
        time.sleep(1)
        for proc in (front, api):
            try:
                if proc.poll() is None:
                    proc.kill()
            except Exception:
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    # Wait until either process exits
    while True:
        if api.poll() is not None:
            warn(f"API exited with code {api.returncode}")
            shutdown()
        if front.poll() is not None:
            warn(f"Frontend exited with code {front.returncode}")
            shutdown()
        time.sleep(0.5)


def main() -> None:
    parser = argparse.ArgumentParser(description="Install and start Arena Console")
    parser.add_argument("--skip-tools", action="store_true", help="Skip security CLI install attempts")
    parser.add_argument("--full", action="store_true", help="Install full requirements.txt (heavy)")
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open the browser")
    parser.add_argument("--skip-install", action="store_true", help="Skip dependency install; just start")
    args = parser.parse_args()

    os.chdir(ROOT)
    info(f"Project root: {ROOT}")

    if not args.skip_install:
        py = ensure_venv()
        install_python_deps(py, full=args.full)
        install_frontend()
        if not args.skip_tools:
            install_system_tools()
            install_python_security_tools(py)
            install_go_tools()
        MARKER.write_text(time.strftime("%Y-%m-%d %H:%M:%S"), encoding="utf-8")
    else:
        py = venv_python()
        if not py.exists():
            py = Path(which_python())
            warn("No .venv found — using system Python")

    # Always prefer .venv when present
    if venv_python().exists():
        py = venv_python()

    # Ensure Go/pip tool bins are visible for status check + runtime
    _, tool_env = _go_env()
    os.environ.update({k: tool_env[k] for k in ("PATH", "GOROOT", "GOPATH", "GOBIN") if k in tool_env})
    if sys.platform == "win32" and venv_python().exists():
        os.environ["PATH"] = str(venv_python().parent) + os.pathsep + os.environ.get("PATH", "")

    # Tool status (use project modules)
    sys.path.insert(0, str(ROOT))
    try:
        print_tool_status()
    except Exception as exc:
        warn(f"Could not list tool status: {exc}")

    start_processes(py if isinstance(py, Path) else Path(py), open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
