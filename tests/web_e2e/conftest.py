import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HOST = "127.0.0.1"
DEFAULT_SERVER_WAIT_SEC = float(os.getenv("WEB_E2E_SERVER_WAIT_SEC", "45"))
DEFAULT_OPTIMIZE_TIMEOUT_SEC = float(os.getenv("WEB_E2E_OPTIMIZE_TIMEOUT_SEC", "90"))
DEFAULT_OPTIMIZE_RETRIES = int(os.getenv("WEB_E2E_OPTIMIZE_RETRIES", "3"))
DEFAULT_OPTIMIZE_RETRY_DELAY_SEC = float(os.getenv("WEB_E2E_OPTIMIZE_RETRY_DELAY_SEC", "1.5"))


def _e2e_log(message: str) -> None:
    print(f"[web_e2e] {message}", flush=True)


def _find_free_port(host: str = DEFAULT_HOST) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _http_get(url: str) -> Dict[str, Any]:
    req = urllib.request.Request(url=url, method="GET")
    with urllib.request.urlopen(req, timeout=5) as resp:
        body = resp.read().decode("utf-8")
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type:
            return json.loads(body)
        return {"text": body}


def _http_post(url: str, payload: Dict[str, Any], timeout_sec: float = 10.0) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        method="POST",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _wait_server(base_url: str, timeout_sec: float = 35.0) -> None:
    deadline = time.time() + timeout_sec
    health_urls = [
        f"{base_url}/v1/governance/ops/summary",
        f"{base_url}/v1/governance/lab/observability/snapshot?env=dev",
    ]
    last_error = "unknown"
    while time.time() < deadline:
        ready = True
        for health_url in health_urls:
            try:
                _http_get(health_url)
            except Exception as exc:
                ready = False
                last_error = f"{health_url}: {exc.__class__.__name__}"
                break
        if ready:
            _e2e_log(f"server ready base_url={base_url}")
            return
        time.sleep(0.3)
    raise RuntimeError(f"server not ready: {base_url}; last_error={last_error}")


def _post_with_retry(
    url: str,
    payload: Dict[str, Any],
    *,
    timeout_sec: float,
    retries: int,
    retry_delay_sec: float,
) -> Dict[str, Any]:
    max_attempts = max(1, retries + 1)
    last_error: Exception | None = None
    started_at = time.time()
    for attempt in range(1, max_attempts + 1):
        try:
            if attempt > 1:
                _e2e_log(f"retrying optimize request attempt={attempt}/{max_attempts}")
            return _http_post(url, payload, timeout_sec=timeout_sec)
        except urllib.error.HTTPError as exc:
            # 4xx denotes request contract errors and should not be retried.
            last_error = exc
            if 400 <= exc.code < 500:
                _e2e_log(
                    "optimize request failed with non-retriable status "
                    f"attempt={attempt}/{max_attempts} status={exc.code}"
                )
                break
            _e2e_log(
                "optimize request failed with HTTPError "
                f"attempt={attempt}/{max_attempts} status={exc.code}"
            )
        except Exception as exc:
            last_error = exc
            _e2e_log(
                "optimize request failed "
                f"attempt={attempt}/{max_attempts} timeout_sec={timeout_sec} error={exc.__class__.__name__}"
            )
        if attempt >= max_attempts:
            break
        _wait_server(url.rsplit("/v1/governance/", 1)[0], timeout_sec=min(15.0, timeout_sec))
        time.sleep(retry_delay_sec * attempt)
    if last_error is None:
        raise RuntimeError("optimize request failed with unknown error")
    _e2e_log(
        "optimize request exhausted retries "
        f"attempts={max_attempts} elapsed_sec={round(time.time() - started_at, 3)}"
    )
    raise last_error


@pytest.fixture(scope="session")
def base_url() -> str:
    external = os.getenv("WEB_E2E_BASE_URL", "").strip()
    if external:
        return external.rstrip("/")
    return f"http://{DEFAULT_HOST}:{_find_free_port()}"


@pytest.fixture(scope="session", autouse=True)
def local_governance_server(base_url: str):
    if os.getenv("WEB_E2E_BASE_URL", "").strip():
        _wait_server(base_url, timeout_sec=DEFAULT_SERVER_WAIT_SEC)
        yield
        return

    port = base_url.rsplit(":", 1)[-1]
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT}:{env.get('PYTHONPATH', '')}".rstrip(":")

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "services.governance_api.app.main:app",
            "--host",
            DEFAULT_HOST,
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_server(base_url, timeout_sec=DEFAULT_SERVER_WAIT_SEC)
        yield
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.fixture(scope="session")
def lab_change_context(base_url: str) -> Dict[str, str]:
    optimize_payload = {
        "caller": "web-e2e-runner",
        "sample_spec": "sample",
        "sample_size": 3,
        "candidate_count": 1,
        "records": [
            {"raw_id": "web-r1", "raw_text": "上海市浦东新区张江路88号"},
            {"raw_id": "web-r2", "raw_text": "北京市海淀区中关村大街27号"},
            {"raw_id": "web-r3", "raw_text": "深圳市南山区科技南十二路2号"},
        ],
    }
    optimize_url = f"{base_url}/v1/governance/lab/optimize/web-e2e-batch"
    _wait_server(base_url, timeout_sec=DEFAULT_SERVER_WAIT_SEC)
    started_at = time.time()
    optimize = _post_with_retry(
        optimize_url,
        optimize_payload,
        timeout_sec=DEFAULT_OPTIMIZE_TIMEOUT_SEC,
        retries=DEFAULT_OPTIMIZE_RETRIES,
        retry_delay_sec=DEFAULT_OPTIMIZE_RETRY_DELAY_SEC,
    )
    _e2e_log(
        "optimize completed "
        f"elapsed_sec={round(time.time() - started_at, 3)} timeout_sec={DEFAULT_OPTIMIZE_TIMEOUT_SEC}"
    )

    change_id = str(optimize["change_id"])
    to_ruleset_id = str(optimize.get("to_ruleset_id", ""))
    if not to_ruleset_id:
        detail = _http_get(f"{base_url}/v1/governance/change-requests/{change_id}")
        to_ruleset_id = str(detail["to_ruleset_id"])

    return {"change_id": change_id, "to_ruleset_id": to_ruleset_id}


@pytest.fixture()
def governance_api(base_url: str):
    class _API:
        @staticmethod
        def post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
            return _http_post(f"{base_url}{path}", payload)

        @staticmethod
        def get(path: str) -> Dict[str, Any]:
            return _http_get(f"{base_url}{path}")

    return _API


@pytest.fixture(scope="session", autouse=True)
def ensure_playwright_browser_ready() -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    launch_attempts = [
        ("chromium", {}),
        ("chromium", {"channel": "chrome"}),
    ]
    errors: list[str] = []
    try:
        with sync_api.sync_playwright() as p:
            for engine_name, kwargs in launch_attempts:
                engine = getattr(p, engine_name)
                launch_kwargs = {"headless": True, **kwargs}
                try:
                    browser = engine.launch(**launch_kwargs)
                    browser.close()
                    return
                except Exception as exc:
                    label = f"{engine_name}:{kwargs.get('channel', 'bundled')}"
                    errors.append(f"{label} -> {exc}")
    except Exception as exc:  # pragma: no cover - depends on local browser install
        errors.append(str(exc))
    pytest.skip(
        "Playwright browser is not installed or unavailable; "
        + " ; ".join(errors)
    )
