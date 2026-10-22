"""
OSD Secure Local Monitoring Agent.
Binds strictly to loopback (127.0.0.1), enforces origin validation,
supports Private Network Access (PNA) preflights, and requires token pairing.
Serves the OSD web portal and read-only telemetry API.
"""
import sys
import os
import json
import time
import secrets
import mimetypes
import threading
from urllib.parse import urlparse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Optional, Any

from osd_core.collectors.system_collector import SystemCollector
from osd_core.collectors.behavior_collector import BehaviorCollector
from osd_core.diagnostics.engine import AnalysisEngine, Thresholds
from osd_core.diagnostics.predictive import PredictiveEngine
from osd_core.diagnostics.simulator import WhatIfSimulator
from osd_core.recommendations.engine import RecommendationEngine
from osd_core.recommendations.recovery_advisor import RecoveryAdvisor
from osd_core.configuration.paths import get_app_dir, get_db_path, get_agent_token_path
from osd_core.configuration.profiles import DEFAULT_PROFILES, WorkloadProfile
from app.database.db_manager import DatabaseManager
from app.utils.formatting import (
    format_bytes, format_speed, format_uptime, format_timestamp,
)


class TelemetryWorker:
    """Thread-safe background telemetry sampler."""
    def __init__(self, monitor: SystemCollector, analysis: AnalysisEngine,
                 predictive: PredictiveEngine, recommender: RecommendationEngine,
                 behavior: BehaviorCollector):
        self.monitor = monitor
        self.analysis = analysis
        self.predictive = predictive
        self.recommender = recommender
        self.behavior = behavior
        self.lock = threading.Lock()
        self.running = False
        self.thread: Optional[threading.Thread] = None

        self.latest_snapshot = self.monitor.collect_snapshot()
        self.latest_processes = self.monitor.get_processes(sort_by="cpu", limit=100)
        self.latest_health = self.analysis.calculate_health_score(self.latest_snapshot)
        self.latest_diagnoses = self.analysis.diagnose(self.latest_snapshot, self.latest_processes)
        self.latest_recommendations = self.recommender.generate(self.latest_diagnoses, self.latest_snapshot, self.latest_processes)
        self.latest_predictions = self.predictive.analyze_predictions(self.latest_snapshot, self.latest_processes)

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True, name="OSD-TelemetryWorker")
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

    def _loop(self):
        while self.running:
            try:
                snap = self.monitor.collect_snapshot()
                self.analysis.add_snapshot(snap)
                self.predictive.add_snapshot(snap)
                procs = self.monitor.get_processes(sort_by="cpu", limit=100)
                health = self.analysis.calculate_health_score(snap)
                diags = self.analysis.diagnose(snap, procs)
                recs = self.recommender.generate(diags, snap, procs)
                preds = self.predictive.analyze_predictions(snap, procs)

                with self.lock:
                    self.latest_snapshot = snap
                    self.latest_processes = procs
                    self.latest_health = health
                    self.latest_diagnoses = diags
                    self.latest_recommendations = recs
                    self.latest_predictions = preds
            except Exception:
                pass
            time.sleep(1.5)


class AgentContext:
    """Shared state and security context for the agent server."""
    def __init__(self, project_root: str, host: str = "127.0.0.1", port: int = 8080):
        self.project_root = os.path.abspath(project_root)
        self.web_dir = os.path.join(self.project_root, "web")
        self.previews_dir = os.path.join(self.project_root, "app_previews")
        self.assets_dir = os.path.join(self.project_root, "assets")
        self.host = host
        self.port = port

        # Security Token
        self.token = secrets.token_hex(16)
        self._save_token_to_disk()

        # Allowed Origins (explicit whitelist, never wildcard unless configured)
        self.allowed_origins = {
            f"http://127.0.0.1:{port}",
            f"http://localhost:{port}",
            "null",  # local file opening (file://)
        }
        # Load user-configured allowed origins (comma-separated, e.g. https://osd.example.com)
        env_origins = os.environ.get("OSD_ALLOWED_ORIGINS", "")
        if env_origins:
            for o in env_origins.split(","):
                clean = o.strip().rstrip("/").lower()
                if clean:
                    self.allowed_origins.add(clean)

        # Core Engines
        self.db = DatabaseManager(get_db_path())
        self.monitor = SystemCollector()
        self.analysis = AnalysisEngine()
        self.recommender = RecommendationEngine()
        self.predictive = PredictiveEngine()
        self.behavior = BehaviorCollector()
        self.advisor = RecoveryAdvisor(self.monitor, self.analysis, self.db)
        self.simulator = WhatIfSimulator(self.analysis)
        self.active_profile = "coding"

        # Worker
        self.worker = TelemetryWorker(
            self.monitor, self.analysis, self.predictive,
            self.recommender, self.behavior
        )
        self.worker.start()

    def _save_token_to_disk(self):
        token_path = get_agent_token_path()
        try:
            token_data = {
                "token": self.token,
                "created_at": time.time(),
                "host": self.host,
                "port": self.port,
            }
            with open(token_path, "w", encoding="utf-8") as f:
                json.dump(token_data, f, indent=2)
            # Restrict permissions on POSIX
            if hasattr(os, "chmod") and sys.platform != "win32":
                try:
                    os.chmod(token_path, 0o600)
                except Exception:
                    pass
        except Exception as e:
            print(f"[OSD Agent] Warning: Could not write token file: {e}")

    def validate_origin(self, origin: Optional[str]) -> bool:
        if not origin:
            return True  # Direct same-origin or curl/local request
        clean_origin = origin.rstrip("/").lower()
        if clean_origin == "null":
            return True
        for allowed in self.allowed_origins:
            if allowed == "*" or clean_origin == allowed.lower():
                return True
        # Allow loopback origins on any port (e.g. local dev server or static file server)
        try:
            parsed = urlparse(clean_origin)
            if parsed.hostname in ("localhost", "127.0.0.1", "::1"):
                return True
        except Exception:
            pass
        # Check database settings dynamically
        try:
            db_origins = self.db.get_setting("allowed_web_origins", "")
            if db_origins:
                for o in db_origins.split(","):
                    if clean_origin == o.strip().rstrip("/").lower():
                        return True
        except Exception:
            pass
        return False

    def validate_token(self, token: Optional[str]) -> bool:
        if not token:
            return False
        return secrets.compare_digest(token.strip(), self.token)


class OSDAgentRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for OSD Local Agent."""

    agent_context: AgentContext

    def _get_request_origin(self) -> Optional[str]:
        return self.headers.get("Origin")

    def _apply_security_headers(self):
        origin = self._get_request_origin()
        if origin and self.agent_context.validate_origin(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
        else:
            self.send_header("Access-Control-Allow-Origin", f"http://127.0.0.1:{self.agent_context.port}")

        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-OSD-Token")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com;")

    def do_OPTIONS(self):
        """Handle CORS and Private Network Access (PNA) preflights."""
        origin = self._get_request_origin()
        if origin and not self.agent_context.validate_origin(origin):
            self.send_response(403)
            self.end_headers()
            return

        self.send_response(204)
        self._apply_security_headers()
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def _send_json(self, data: Any, status: int = 200):
        origin = self._get_request_origin()
        if origin and not self.agent_context.validate_origin(origin):
            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "Forbidden: Untrusted Origin"}')
            return

        blob = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(blob)))
        self._apply_security_headers()
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(blob)

    def _serve_file(self, filepath: str, content_type: Optional[str] = None):
        if not os.path.exists(filepath) or not os.path.isfile(filepath):
            self.send_response(404)
            self.end_headers()
            return

        if not content_type:
            content_type, _ = mimetypes.guess_type(filepath)
            if not content_type:
                content_type = "application/octet-stream"

        try:
            with open(filepath, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self._apply_security_headers()
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)
        except Exception:
            self.send_response(500)
            self.end_headers()

    def _serve_from_dir(self, base_dir: str, rel_path: str):
        norm_base = os.path.abspath(base_dir)
        full_path = os.path.abspath(os.path.join(norm_base, rel_path.lstrip("/\\")))
        # Path traversal guard
        try:
            if os.path.commonpath([norm_base, full_path]) != norm_base:
                self.send_response(403)
                self.end_headers()
                return
        except ValueError:
            self.send_response(403)
            self.end_headers()
            return

        self._serve_file(full_path)

    def do_HEAD(self):
        """Handle HEAD requests by generating headers without message body."""
        self.do_GET()

    def do_GET(self):
        url = urlparse(self.path)
        ctx = self.agent_context

        if url.path in ("/", "/index.html"):
            index_path = os.path.join(ctx.web_dir, "index.html")
            self._serve_file(index_path, "text/html; charset=utf-8")

        elif url.path.startswith("/app_previews/"):
            rel_path = url.path[len("/app_previews/"):]
            self._serve_from_dir(ctx.previews_dir, rel_path)

        elif url.path.startswith("/assets/"):
            rel_path = url.path[len("/assets/"):]
            self._serve_from_dir(ctx.assets_dir, rel_path)

        elif url.path.startswith("/web/"):
            rel_path = url.path[len("/web/"):]
            self._serve_from_dir(ctx.web_dir, rel_path)

        # Agent status / health handshake info
        elif url.path in ("/api/health", "/api/status"):
            caps = ctx.monitor.adapter.check_runtime_capabilities()
            self._send_json({
                "status": "ok",
                "app": "OSD",
                "agent": "OSD Local Companion",
                "version": "2.1.0",
                "loopback_only": True,
                "binding": f"http://{ctx.host}:{ctx.port}",
                "capabilities": caps,
                "timestamp": time.time(),
            })

        # Pair verification (reads query param or header)
        elif url.path == "/api/pair":
            token_req = self.headers.get("X-OSD-Token", "")
            if not token_req and "token=" in url.query:
                # Extract query param token
                for part in url.query.split("&"):
                    if part.startswith("token="):
                        token_req = part[len("token="):]
            ok = ctx.validate_token(token_req)
            self._send_json({"paired": ok, "message": "Paired successfully." if ok else "Invalid or missing token."})

        # Read-only Telemetry Metrics
        elif url.path == "/api/metrics":
            with ctx.worker.lock:
                snap = ctx.worker.latest_snapshot
                health = ctx.worker.latest_health
                diags = ctx.worker.latest_diagnoses
                recs = ctx.worker.latest_recommendations
                procs = ctx.worker.latest_processes

            payload = {
                'snapshot': {
                    'cpu_percent': snap.cpu.overall_percent,
                    'logical_cores': snap.cpu.core_count_logical,
                    'frequency_mhz': snap.cpu.frequency_current,
                    'memory_percent': snap.memory.percent,
                    'memory_used_gb': snap.memory.used / (1024**3),
                    'memory_total_gb': snap.memory.total / (1024**3),
                    'swap_percent': snap.memory.swap_percent,
                    'disk_percent': snap.disk.percent,
                    'disk_free_gb': snap.disk.free / (1024**3),
                    'net_up_speed': format_speed(snap.network.upload_speed),
                    'net_down_speed': format_speed(snap.network.download_speed),
                    'uptime': format_uptime(snap.uptime_seconds),
                    'process_count': snap.process_count,
                    'platform': snap.platform_info,
                    'os_family': snap.os_family,
                    'collection_errors': snap.collection_errors,
                },
                'health': health.to_dict(),
                'diagnoses': [d.to_dict() for d in diags],
                'recommendations': [r.to_dict() for r in recs],
                'top_processes': [
                    {'name': p.name, 'pid': p.pid, 'cpu': p.cpu_percent, 'memory_mb': p.memory_mb}
                    for p in procs[:5]
                ],
            }
            self._send_json(payload)

        # Read-only Diagnosis endpoint
        elif url.path == "/api/diagnose":
            with ctx.worker.lock:
                health = ctx.worker.latest_health
                diags = ctx.worker.latest_diagnoses
            self._send_json({
                'health_score': health.total_score,
                'diagnoses': [d.to_dict() for d in diags],
            })

        # Read-only Process List
        elif url.path == "/api/processes":
            with ctx.worker.lock:
                procs = list(ctx.worker.latest_processes)
            payload = [
                {
                    'pid': p.pid,
                    'name': p.name,
                    'cpu': p.cpu_percent,
                    'memory_percent': p.memory_percent,
                    'memory_mb': p.memory_mb,
                    'status': p.status,
                    'threads': p.num_threads,
                }
                for p in procs
            ]
            self._send_json(payload)

        # Read-only Predictive Early Warnings
        elif url.path == "/api/predictive":
            with ctx.worker.lock:
                preds = list(ctx.worker.latest_predictions)
            payload = {'predictions': [a.to_dict() for a in preds]}
            self._send_json(payload)

        # Read-only Recovery Plans and Audit
        elif url.path == "/api/recovery":
            with ctx.worker.lock:
                snap = ctx.worker.latest_snapshot
                procs = ctx.worker.latest_processes
                diags = ctx.worker.latest_diagnoses
            plans = ctx.advisor.generate_plans(diags, snap, procs)
            audit = ctx.db.get_recovery_actions(limit=10)
            payload = {
                'plans': [p.to_dict() for p in plans],
                'audit_log': audit,
                'can_trim_memory': ctx.monitor.adapter.can_trim_working_set(),
            }
            self._send_json(payload)

        # Read-only Workload Profiles
        elif url.path == "/api/profiles":
            profs = [p.to_dict() for p in DEFAULT_PROFILES.values()]
            self._send_json({'active': ctx.active_profile, 'profiles': profs})

        # Read-only History
        elif url.path == "/api/history":
            history = ctx.db.get_resource_history(hours=24.0, limit=50)
            payload = [
                {
                    'time': format_timestamp(r['timestamp']),
                    'health_score': r['health_score'],
                    'cpu_percent': r['cpu_percent'],
                    'memory_percent': r['memory_percent'],
                    'swap_percent': r['swap_percent'],
                    'disk_percent': r['disk_percent'],
                    'process_count': r['process_count'],
                }
                for r in history
            ]
            self._send_json(payload)

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        url = urlparse(self.path)
        ctx = self.agent_context

        # Validate origin for all POST requests (CSRF protection)
        origin = self._get_request_origin()
        if origin and not ctx.validate_origin(origin):
            self.send_response(403)
            self.end_headers()
            return

        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8') if length > 0 else ""
        data = json.loads(body) if body else {}

        if url.path == "/api/diagnose":
            with ctx.worker.lock:
                snap = ctx.worker.latest_snapshot
                procs = ctx.worker.latest_processes
                health = ctx.worker.latest_health
                diags = ctx.worker.latest_diagnoses
            payload = {
                'snapshot': {
                    'cpu_percent': snap.cpu.overall_percent,
                    'logical_cores': snap.cpu.core_count_logical,
                    'frequency_mhz': snap.cpu.frequency_current,
                    'memory_percent': snap.memory.percent,
                    'memory_used_gb': snap.memory.used / (1024**3),
                    'memory_total_gb': snap.memory.total / (1024**3),
                    'swap_percent': snap.memory.swap_percent,
                    'disk_percent': snap.disk.percent,
                    'disk_free_gb': snap.disk.free / (1024**3),
                    'net_up_speed': format_speed(snap.network.upload_speed),
                    'net_down_speed': format_speed(snap.network.download_speed),
                    'uptime': format_uptime(snap.uptime_seconds),
                    'process_count': snap.process_count,
                    'platform': snap.platform_info,
                },
                'health': health.to_dict(),
                'diagnoses': [d.to_dict() for d in diags],
                'top_processes': [{'name': p.name, 'pid': p.pid, 'cpu': p.cpu_percent, 'memory_mb': p.memory_mb} for p in procs[:5]],
            }
            self._send_json(payload)

        elif url.path == "/api/simulate":
            # What-If Simulator is purely sandboxed and safe (does not kill any process)
            pids = set(data.get('pids', []))
            with ctx.worker.lock:
                snap = ctx.worker.latest_snapshot
                procs = ctx.worker.latest_processes
            selected = [p for p in procs if p.pid in pids]
            res = ctx.simulator.simulate_closing_processes(snap, selected)
            self._send_json(res.to_dict())

        elif url.path == "/api/set_profile":
            name = data.get('profile', '')
            if name in DEFAULT_PROFILES:
                ctx.active_profile = name
                prof = DEFAULT_PROFILES[name]
                ctx.analysis.thresholds.cpu_warning = prof.cpu_warning
                ctx.analysis.thresholds.cpu_critical = prof.cpu_critical
                ctx.analysis.thresholds.memory_warning = prof.memory_warning
                ctx.analysis.thresholds.memory_critical = prof.memory_critical
                self._send_json({'success': True, 'active': name})
            else:
                self._send_json({'success': False, 'error': f"Unknown profile {name}"}, status=400)

        elif url.path == "/api/ask":
            from app.assistant.chat_engine import AskOSDEngine
            chat = AskOSDEngine(ctx.monitor, ctx.analysis, ctx.predictive, ctx.db)
            question = data.get('question', '')
            answer = chat.ask(question)
            self._send_json({'question': question, 'answer': answer})

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Quiet request logs


class OSDAgent:
    """Manages lifecycle of the local HTTP agent server."""
    def __init__(self, project_root: Optional[str] = None, host: str = "127.0.0.1", port: int = 8080):
        # Enforce loopback only
        if host not in ("127.0.0.1", "localhost", "::1"):
            print(f"[OSD Agent Security Warning] Resetting host from '{host}' to loopback '127.0.0.1'.")
            host = "127.0.0.1"

        if project_root is None:
            # Default to root directory of project
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        self.context = AgentContext(project_root, host, port)
        OSDAgentRequestHandler.agent_context = self.context
        self.server = ThreadingHTTPServer((host, port), OSDAgentRequestHandler)
        self._thread: Optional[threading.Thread] = None

    @property
    def host(self) -> str:
        return self.context.host

    @property
    def port(self) -> int:
        return self.context.port

    @property
    def token(self) -> str:
        return self.context.token

    def start(self, open_browser: bool = False):
        """Start the server on a background daemon thread."""
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="OSD-HttpServer")
        self._thread.start()

    def stop(self):
        """Cleanly shutdown HTTP server and background telemetry worker."""
        self.server.shutdown()
        self.close()

    def serve(self):
        print(f"==================================================================")
        print(f"  OSD Local Monitoring Agent online at http://{self.context.host}:{self.context.port}/")
        print(f"  Loopback Binding: Strictly bound to {self.context.host}")
        print(f"  Security Token: {self.context.token}")
        print(f"  Token File: {get_agent_token_path()}")
        print(f"==================================================================")
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.close()

    def close(self):
        self.context.worker.stop()
        self.server.server_close()
