"""
Unit tests for OSD Local Agent security controls.
Verifies:
1. Loopback-only binding (127.0.0.1).
2. Random pairing session token generation.
3. CORS origin validation (local origin vs untrusted origin).
4. Private Network Access (PNA) preflight header response.
5. Read-only API behavior and rejection of unauthorized actions.
"""
import json
import urllib.request
import urllib.error
import pytest

from osd_core.agent.server import OSDAgent


@pytest.fixture(scope="module")
def agent_server():
    """Start OSDAgent on a free loopback port for the test session."""
    agent = OSDAgent(host="127.0.0.1", port=18899)
    agent.start(open_browser=False)
    yield agent
    agent.stop()


def test_agent_loopback_only(agent_server):
    """Verify agent is bound strictly to 127.0.0.1."""
    assert agent_server.host == "127.0.0.1"
    assert agent_server.port == 18899
    assert agent_server.token is not None
    assert len(agent_server.token) == 32  # 16 bytes hex


def test_agent_health_endpoint(agent_server):
    """Verify /api/health returns operational status."""
    url = f"http://127.0.0.1:{agent_server.port}/api/health"
    req = urllib.request.Request(url, headers={"Origin": "http://127.0.0.1:8000"})
    with urllib.request.urlopen(req, timeout=3.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data.get("status") == "ok"
        assert data.get("app") == "OSD"


def test_agent_cors_allowed_origin(agent_server):
    """Verify local origin receives valid CORS headers."""
    url = f"http://127.0.0.1:{agent_server.port}/api/health"
    req = urllib.request.Request(url, headers={"Origin": "http://localhost:8000"})
    with urllib.request.urlopen(req, timeout=3.0) as resp:
        headers = dict(resp.headers)
        assert headers.get("Access-Control-Allow-Origin") == "http://localhost:8000"


def test_agent_pna_preflight_headers(agent_server):
    """Verify OPTIONS preflight request handles Private Network Access (PNA)."""
    url = f"http://127.0.0.1:{agent_server.port}/api/metrics"
    req = urllib.request.Request(
        url,
        method="OPTIONS",
        headers={
            "Origin": "http://localhost:8000",
            "Access-Control-Request-Private-Network": "true"
        }
    )
    with urllib.request.urlopen(req, timeout=3.0) as resp:
        assert resp.status == 204
        headers = dict(resp.headers)
        assert headers.get("Access-Control-Allow-Private-Network") == "true"
        assert "GET" in headers.get("Access-Control-Allow-Methods", "")


def test_agent_metrics_endpoint(agent_server):
    """Verify /api/metrics returns real system snapshot data."""
    url = f"http://127.0.0.1:{agent_server.port}/api/metrics"
    req = urllib.request.Request(url, headers={"Origin": "http://127.0.0.1:8000"})
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        payload = json.loads(resp.read().decode())
        assert "snapshot" in payload
        assert "health" in payload
        assert "diagnoses" in payload
        assert payload["snapshot"]["cpu_percent"] >= 0.0


def test_agent_diagnose_endpoint(agent_server):
    """Verify /api/diagnose returns real analysis results without crashing."""
    url = f"http://127.0.0.1:{agent_server.port}/api/diagnose"
    req = urllib.request.Request(url, headers={"Origin": "http://127.0.0.1:8000"})
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        payload = json.loads(resp.read().decode())
        assert "diagnoses" in payload
        assert "health_score" in payload
        assert 0 <= payload["health_score"] <= 100


def test_agent_blocks_unauthorized_external_origin(agent_server):
    """Verify that untrusted external origins receive 403 Forbidden on POST requests."""
    url = f"http://127.0.0.1:{agent_server.port}/api/diagnose"
    req = urllib.request.Request(
        url,
        data=b"{}",
        headers={
            "Origin": "https://malicious-external-site.com",
            "Content-Type": "application/json"
        }
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req, timeout=3.0)
    assert exc_info.value.code == 403
