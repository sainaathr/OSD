"""
OSD Web Companion — Full interactive live browser dashboard for OSD.
Provides an HTTP web interface at http://localhost:8080 connected to the
real-time SystemMonitor, AnalysisEngine, PredictiveEngine, RecoveryAdvisor,
AskOSDEngine, WhatIfSimulator, ProfileManager, and DatabaseManager.
"""
import sys
import os
import json
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import mimetypes

# Ensure root in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.monitoring.system_monitor import SystemMonitor
from app.monitoring.behavior_monitor import ProcessBehaviorMonitor
from app.analysis.engine import AnalysisEngine, Thresholds
from app.analysis.predictive_engine import PredictiveEngine
from app.analysis.simulator import WhatIfSimulator
from app.recommendations.engine import RecommendationEngine
from app.recommendations.recovery_advisor import RecoveryAdvisor
from app.assistant.chat_engine import AskOSDEngine, AskOSenseEngine
from app.profiles.profile_manager import ProfileManager
from app.database.db_manager import DatabaseManager
from app.utils.formatting import (
    format_bytes, format_speed, format_uptime, format_timestamp,
    health_score_color, health_score_label
)

# Shared instances
db = DatabaseManager()
monitor = SystemMonitor()
analysis = AnalysisEngine()
recommender = RecommendationEngine()
predictive = PredictiveEngine()
behavior = ProcessBehaviorMonitor()
advisor = RecoveryAdvisor(monitor, analysis, db)
chat_engine = AskOSDEngine(monitor, analysis, predictive, db)
simulator = WhatIfSimulator(analysis)
profile_mgr = ProfileManager(db)

import threading

class TelemetryWorker:
    """Background sampling thread that continuously keeps system metrics and process CPU cache warm."""
    def __init__(self):
        self.lock = threading.Lock()
        self.latest_snapshot = monitor.collect_snapshot()
        self.latest_processes = monitor.get_processes(sort_by="cpu", limit=100)
        self.latest_health = analysis.calculate_health_score(self.latest_snapshot)
        self.latest_diagnoses = analysis.diagnose(self.latest_snapshot, self.latest_processes)
        self.latest_recommendations = recommender.generate(self.latest_diagnoses, self.latest_snapshot, self.latest_processes)
        self.latest_predictions = predictive.analyze_predictions(self.latest_snapshot, self.latest_processes)
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        self.thread.start()

    def _loop(self):
        while self.running:
            try:
                snap = monitor.collect_snapshot()
                analysis.add_snapshot(snap)
                predictive.add_snapshot(snap)
                procs = monitor.get_processes(sort_by="cpu", limit=100)
                health = analysis.calculate_health_score(snap)
                diags = analysis.diagnose(snap, procs)
                recs = recommender.generate(diags, snap, procs)
                preds = predictive.analyze_predictions(snap, procs)
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

telemetry_worker = TelemetryWorker()
telemetry_worker.start()

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OSD — Predictive OS Health & Recovery Assistant</title>
  <style>
    :root {
      --bg-primary: #111315;
      --bg-secondary: #171918;
      --bg-card: #1B1E1D;
      --bg-card-hover: #222624;
      --bg-sidebar: #171918;
      --border: #303331;
      --text-primary: #F4F4EF;
      --text-secondary: #A4A69F;
      --text-muted: #72756E;
      --accent-violet: #E8FF65;
      --accent-violet-dim: #242923;
      --accent-cyan: #82B9B1;
      --green: #82B9B1;
      --amber: #E5A93C;
      --red: #E05252;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg-primary);
      color: var(--text-primary);
      display: flex;
      height: 100vh;
      overflow: hidden;
    }
    /* Sidebar */
    .sidebar {
      width: 220px;
      background: var(--bg-sidebar);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      padding: 16px 12px;
      gap: 3px;
      flex-shrink: 0;
      overflow-y: auto;
    }
    .logo {
      font-size: 0.95rem;
      font-weight: 800;
      letter-spacing: 0.08em;
      color: var(--text-primary);
      padding: 0 8px 4px 8px;
    }
    .tagline {
      font-size: 0.70rem;
      letter-spacing: 0.04em;
      color: var(--text-muted);
      padding: 0 8px 12px 8px;
      border-bottom: 1px solid var(--border);
      margin-bottom: 8px;
    }
    .nav-btn {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 12px;
      border-radius: 4px;
      color: var(--text-secondary);
      background: transparent;
      border: none;
      cursor: pointer;
      font-size: 0.82rem;
      font-weight: 500;
      transition: all 0.15s ease;
      text-align: left;
      width: 100%;
    }
    .nav-btn:hover { background: #222624; color: var(--text-primary); }
    .nav-btn.active { background: #242826; border-left: 3px solid var(--accent-violet); color: var(--text-primary); font-weight: 600; }
    .sidebar-footer {
      margin-top: auto;
      font-size: 0.70rem;
      color: var(--text-muted);
      text-align: center;
      padding-top: 10px;
      border-top: 1px solid var(--border);
    }
    /* Main Content */
    .main {
      flex: 1;
      overflow-y: auto;
      padding: 24px 32px;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }
    .header h1 { font-size: 1.55rem; font-weight: 800; }
    .header p { font-size: 0.82rem; color: var(--text-secondary); }
    .btn-action {
      background: var(--accent-cyan);
      color: var(--bg-primary);
      border: none;
      padding: 9px 18px;
      border-radius: 8px;
      font-weight: 700;
      font-size: 0.88rem;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: opacity 0.15s;
    }
    .btn-action:hover { opacity: 0.9; }
    .btn-secondary {
      background: var(--bg-card);
      color: var(--text-primary);
      border: 1px solid var(--border);
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 0.82rem;
      cursor: pointer;
    }
    .btn-secondary:hover { background: var(--bg-card-hover); }
    /* Cards */
    .card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px 18px;
    }
    .health-card {
      display: grid;
      grid-template-columns: 200px 1fr;
      gap: 24px;
      align-items: center;
    }
    .score-circle {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      border: 3px solid var(--accent-violet);
      border-radius: 50%;
      width: 140px;
      height: 140px;
      margin: 0 auto;
      background: var(--bg-secondary);
    }
    .score-title { font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; }
    .score-num { font-size: 2.6rem; font-weight: 900; }
    .score-label { font-size: 0.78rem; font-weight: 600; }
    .breakdown-row {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 7px;
      font-size: 0.82rem;
    }
    .breakdown-name { width: 45px; color: var(--text-secondary); }
    .progress-bar {
      flex: 1;
      height: 7px;
      background: var(--bg-primary);
      border-radius: 4px;
      overflow: hidden;
    }
    .progress-fill {
      height: 100%;
      background: var(--accent-cyan);
      border-radius: 4px;
      transition: width 0.3s;
    }
    /* Grid */
    .grid-4 {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 14px;
    }
    .grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }
    .metric-card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px 16px;
    }
    .metric-title {
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-secondary);
      margin-bottom: 6px;
    }
    .metric-value {
      font-size: 1.6rem;
      font-weight: 700;
      color: var(--text-primary);
      margin-bottom: 2px;
    }
    .metric-sub {
      font-size: 0.72rem;
      color: var(--text-muted);
    }
    /* Tables */
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.82rem;
    }
    th {
      text-align: left;
      padding: 9px 12px;
      background: var(--bg-secondary);
      color: var(--text-secondary);
      font-weight: 600;
      border-bottom: 2px solid var(--accent-violet);
    }
    td {
      padding: 9px 12px;
      border-bottom: 1px solid var(--border);
    }
    tr:hover { background: rgba(255,255,255,0.02); }
    .badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.72rem;
      font-weight: 700;
    }
    .badge-healthy { background: rgba(74, 222, 128, 0.15); color: var(--green); }
    .badge-info { background: rgba(96, 165, 250, 0.15); color: #60a5fa; }
    .badge-warning { background: rgba(251, 191, 36, 0.15); color: var(--amber); }
    .badge-critical { background: rgba(239, 68, 68, 0.15); color: var(--red); }
    .page { display: none; }
    .page.active { display: flex; flex-direction: column; gap: 18px; }
    /* Chat bubbles */
    .chat-bubble {
      padding: 12px 16px;
      border-radius: 10px;
      font-size: 0.85rem;
      line-height: 1.5;
      margin-bottom: 10px;
      max-width: 85%;
    }
    .chat-user {
      background: var(--accent-violet-dim);
      border: 1px solid var(--accent-violet);
      align-self: flex-end;
      color: white;
    }
    .chat-assistant {
      background: var(--bg-card);
      border: 1px solid var(--border);
      align-self: flex-start;
      color: var(--text-primary);
    }
    .prompt-pill {
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--accent-cyan);
      border-radius: 20px;
      padding: 5px 12px;
      font-size: 0.75rem;
      cursor: pointer;
      display: inline-block;
      margin: 3px;
    }
    .prompt-pill:hover { background: var(--bg-card-hover); }
  </style>
</head>
<body>

  <!-- Sidebar (11 OSD Views) -->
  <div class="sidebar">
    <div class="logo">⚡ OSD</div>
    <div class="tagline">Predictive Recovery Assistant</div>

    <button class="nav-btn active" onclick="switchPage('overview', this)">📊 Overview</button>
    <button class="nav-btn" onclick="switchPage('processes', this)">⚙️ Processes</button>
    <button class="nav-btn" onclick="switchPage('performance', this)">📈 Performance</button>
    <button class="nav-btn" onclick="switchPage('diagnosis', this)">🔍 Diagnosis</button>
    <button class="nav-btn" onclick="switchPage('predictive', this)">🔮 Predictive Alerts</button>
    <button class="nav-btn" onclick="switchPage('recovery', this)">🛡️ Recovery Advisor</button>
    <button class="nav-btn" onclick="switchPage('assistant', this)">💬 Ask OSD</button>
    <button class="nav-btn" onclick="switchPage('history', this)">⏳ System History</button>
    <button class="nav-btn" onclick="switchPage('simulator', this)">🧪 What-If Simulator</button>
    <button class="nav-btn" onclick="switchPage('profiles', this)">🎯 Workload Profiles</button>
    <button class="nav-btn" onclick="switchPage('settings', this)">⚙ Settings</button>

    <div class="sidebar-footer">
      v2.0.0 Pro • 100% Local Engine
    </div>
  </div>

  <!-- Main Container -->
  <div class="main">

    <!-- PAGE 1: OVERVIEW -->
    <div id="page-overview" class="page active">
      <div class="header">
        <div>
          <h1>System Health Overview</h1>
          <p id="live-status">Connecting to OSD live telemetry...</p>
        </div>
        <button class="btn-action" onclick="triggerDiagnosis()">🔍 Diagnose My PC</button>
      </div>

      <!-- Health Score Card -->
      <div class="card health-card">
        <div class="score-circle">
          <div class="score-title">Health Score</div>
          <div class="score-num" id="health-score">--</div>
          <div class="score-label" id="health-label">Calculating...</div>
        </div>
        <div>
          <div style="font-size: 0.8rem; font-weight: 700; color: var(--text-secondary); margin-bottom: 12px;">Score Breakdown (Weighted)</div>
          <div class="breakdown-row">
            <span class="breakdown-name">CPU</span>
            <div class="progress-bar"><div class="progress-fill" id="bar-cpu" style="width: 100%"></div></div>
            <span id="val-cpu" style="width: 32px; text-align: right;">--</span>
          </div>
          <div class="breakdown-row">
            <span class="breakdown-name">RAM</span>
            <div class="progress-bar"><div class="progress-fill" id="bar-mem" style="width: 100%"></div></div>
            <span id="val-mem" style="width: 32px; text-align: right;">--</span>
          </div>
          <div class="breakdown-row">
            <span class="breakdown-name">Swap</span>
            <div class="progress-bar"><div class="progress-fill" id="bar-swap" style="width: 100%"></div></div>
            <span id="val-swap" style="width: 32px; text-align: right;">--</span>
          </div>
          <div class="breakdown-row">
            <span class="breakdown-name">Disk</span>
            <div class="progress-bar"><div class="progress-fill" id="bar-disk" style="width: 100%"></div></div>
            <span id="val-disk" style="width: 32px; text-align: right;">--</span>
          </div>
          <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 6px;" id="factors-list"></div>
        </div>
      </div>

      <!-- Quick Metrics Grid -->
      <div class="grid-4">
        <div class="metric-card">
          <div class="metric-title">Processor (CPU)</div>
          <div class="metric-value" id="card-cpu">--%</div>
          <div class="metric-sub" id="card-cpu-sub">-- cores</div>
        </div>
        <div class="metric-card">
          <div class="metric-title">Physical Memory</div>
          <div class="metric-value" id="card-mem">--%</div>
          <div class="metric-sub" id="card-mem-sub">-- GB available</div>
        </div>
        <div class="metric-card">
          <div class="metric-title">Storage Drive</div>
          <div class="metric-value" id="card-disk">--%</div>
          <div class="metric-sub" id="card-disk-sub">-- GB free</div>
        </div>
        <div class="metric-card">
          <div class="metric-title">Network Activity</div>
          <div class="metric-value" id="card-net">0 KB/s</div>
          <div class="metric-sub" id="card-net-sub">↑ 0 KB/s  ↓ 0 KB/s</div>
        </div>
      </div>

      <!-- Top Processes & Active Findings -->
      <div class="grid-2">
        <div class="card">
          <div style="font-weight: 700; font-size: 0.95rem; margin-bottom: 12px;">Top Resource Consumers</div>
          <div id="top-procs-list" style="display: flex; flex-direction: column; gap: 8px;"></div>
        </div>
        <div class="card">
          <div style="font-weight: 700; font-size: 0.95rem; margin-bottom: 12px;">Active Diagnostic Bottlenecks</div>
          <div id="alerts-list" style="display: flex; flex-direction: column; gap: 8px;"></div>
        </div>
      </div>
    </div>

    <!-- PAGE 2: PROCESSES -->
    <div id="page-processes" class="page">
      <div class="header">
        <div>
          <h1>Process Explorer</h1>
          <p>Active processes sorted by CPU and memory consumption</p>
        </div>
        <input type="text" id="proc-search" placeholder="Filter processes..." oninput="filterProcesses()" style="background: var(--bg-card); border: 1px solid var(--border); color: white; padding: 8px 14px; border-radius: 6px; width: 220px;">
      </div>
      <div class="card" style="padding: 0; overflow: hidden;">
        <table>
          <thead>
            <tr>
              <th>PID</th>
              <th>Name</th>
              <th>CPU %</th>
              <th>RAM %</th>
              <th>Memory (MB)</th>
              <th>Status</th>
              <th>Threads</th>
            </tr>
          </thead>
          <tbody id="processes-tbody"></tbody>
        </table>
      </div>
    </div>

    <!-- PAGE 3: PERFORMANCE -->
    <div id="page-performance" class="page">
      <div class="header">
        <div>
          <h1>Performance Monitors</h1>
          <p>Real-time rolling hardware activity charts</p>
        </div>
      </div>
      <div class="grid-2">
        <div class="card">
          <div style="font-weight: 700; font-size: 0.9rem; margin-bottom: 8px;">CPU Load History (%)</div>
          <canvas id="chart-cpu" width="400" height="150" style="width: 100%; height: 150px; background: var(--bg-secondary); border-radius: 6px;"></canvas>
        </div>
        <div class="card">
          <div style="font-weight: 700; font-size: 0.9rem; margin-bottom: 8px;">Memory Usage History (%)</div>
          <canvas id="chart-mem" width="400" height="150" style="width: 100%; height: 150px; background: var(--bg-secondary); border-radius: 6px;"></canvas>
        </div>
      </div>
    </div>

    <!-- PAGE 4: DIAGNOSIS -->
    <div id="page-diagnosis" class="page">
      <div class="header">
        <div>
          <h1>Root-Cause Investigation</h1>
          <p>Correlated multi-resource bottlenecks with evidence strength scoring</p>
        </div>
        <button class="btn-action" onclick="triggerDiagnosis()">🔍 Run Full Diagnostic Scan</button>
      </div>
      <div id="diag-results" style="display: flex; flex-direction: column; gap: 12px;"></div>
    </div>

    <!-- PAGE 5: PREDICTIVE ALERTS -->
    <div id="page-predictive" class="page">
      <div class="header">
        <div>
          <h1>🔮 Predictive Performance Engine</h1>
          <p>Time-series slope estimation, time-to-exhaustion forecasts, and early pressure warnings</p>
        </div>
        <button class="btn-secondary" onclick="loadPredictiveAlerts()">🔄 Refresh Forecast</button>
      </div>
      <div id="predictive-alerts-container" style="display: flex; flex-direction: column; gap: 12px;"></div>
    </div>

    <!-- PAGE 6: RECOVERY ADVISOR -->
    <div id="page-recovery" class="page">
      <div class="header">
        <div>
          <h1>🛡️ Autonomous Recovery Advisor</h1>
          <p>Safe 6-step recovery workflow with verified before-and-after outcome auditing</p>
        </div>
        <button class="btn-secondary" onclick="loadRecoveryPlans()">🔄 Refresh Plans</button>
      </div>
      <div class="card" style="border-left: 4px solid var(--accent-cyan); line-height: 1.5; font-size: 0.85rem;">
        <b>Safe Recovery Workflow:</b> Detect ➔ Investigate ➔ Recommend ➔ Consent ➔ Execute ➔ Verify.<br>
        <span style="color: var(--text-muted);">OSD revalidates process identity before execution and protects critical OS processes. Working set trimming and priority throttling are non-invasive.</span>
      </div>
      <div id="recovery-plans-container" style="display: flex; flex-direction: column; gap: 12px;"></div>
      <div class="card">
        <div style="font-weight: 700; margin-bottom: 10px;">📋 Verified Recovery Audit Log</div>
        <div id="recovery-audit-log" style="font-size: 0.82rem; color: var(--text-secondary); line-height: 1.6;">No actions executed in this session.</div>
      </div>
    </div>

    <!-- PAGE 7: ASK OSD -->
    <div id="page-assistant" class="page">
      <div class="header">
        <div>
          <h1>💬 Ask OSD Assistant</h1>
          <p>Conversational performance analyst grounded in live telemetry and SQLite history (100% Offline)</p>
        </div>
      </div>
      <div class="card" style="min-height: 380px; display: flex; flex-direction: column;">
        <div id="chat-messages" style="flex: 1; overflow-y: auto; display: flex; flex-direction: column; margin-bottom: 14px; max-height: 400px;">
          <div class="chat-bubble chat-assistant">
            <b>OSD Assistant:</b> Hello! I am your offline system performance assistant. Ask me anything about your current hardware usage, bottlenecks, or past recovery results.
          </div>
        </div>
        <div style="margin-bottom: 10px;">
          <span class="prompt-pill" onclick="sendPrompt('Why is my PC slow?')">Why is my PC slow?</span>
          <span class="prompt-pill" onclick="sendPrompt('Which process uses the most memory?')">Most memory hog?</span>
          <span class="prompt-pill" onclick="sendPrompt('Which process uses the most CPU?')">Most CPU consumer?</span>
          <span class="prompt-pill" onclick="sendPrompt('What has changed recently?')">What changed recently?</span>
          <span class="prompt-pill" onclick="sendPrompt('Which recommendation is safest?')">Safest recommendation?</span>
          <span class="prompt-pill" onclick="sendPrompt('Is the memory usage increasing?')">Is RAM increasing?</span>
          <span class="prompt-pill" onclick="sendPrompt('Did the last recovery action improve performance?')">Did last recovery help?</span>
        </div>
        <div style="display: flex; gap: 8px;">
          <input type="text" id="chat-input" placeholder="Type a question about your system..." onkeydown="if(event.key==='Enter') sendChatMessage()" style="flex: 1; background: var(--bg-secondary); border: 1px solid var(--border); color: white; padding: 10px 14px; border-radius: 8px; font-size: 0.88rem;">
          <button class="btn-action" onclick="sendChatMessage()">Send</button>
        </div>
      </div>
    </div>

    <!-- PAGE 8: SYSTEM HISTORY (TIME MACHINE) -->
    <div id="page-history" class="page">
      <div class="header">
        <div>
          <h1>⏳ System Time Machine</h1>
          <p>Reconstruct telemetry trends, session comparisons, and verified action history</p>
        </div>
        <button class="btn-secondary" onclick="loadHistory()">🔄 Refresh History</button>
      </div>
      <div class="card" style="padding: 0; overflow: hidden;">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Health</th>
              <th>CPU %</th>
              <th>RAM %</th>
              <th>Swap %</th>
              <th>Disk %</th>
              <th>Processes</th>
            </tr>
          </thead>
          <tbody id="history-tbody"></tbody>
        </table>
      </div>
    </div>

    <!-- PAGE 9: WHAT-IF SIMULATOR -->
    <div id="page-simulator" class="page">
      <div class="header">
        <div>
          <h1>🧪 What-If Resource Simulator</h1>
          <p>Sandboxed resource impact estimation — select processes below to simulate gains safely</p>
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <button class="btn-secondary" onclick="simulateSelectTop3()">⚡ Select Top 3 Hogs</button>
          <button class="btn-secondary" onclick="simulateSelectBrowsers()">🌐 Select Browsers</button>
          <button class="btn-secondary" onclick="simulateClearAll()">🧹 Clear Selection</button>
          <button class="btn-action" onclick="recalculateSimulation()">🔄 Re-Simulate</button>
        </div>
      </div>

      <div style="background: rgba(130, 185, 177, 0.08); border: 1px solid var(--accent-cyan); border-radius: 8px; padding: 10px 16px; font-size: 0.82rem; color: var(--accent-cyan); display: flex; align-items: center; justify-content: space-between;">
        <span>🛡️ <b>SANDBOX MODE ACTIVE:</b> No running processes are altered. Projections simulate what system relief occurs if selected applications are terminated.</span>
        <span id="sim-status-pill" style="font-weight: 700; color: var(--text-primary);">0 apps selected</span>
      </div>

      <div class="grid-4">
        <div class="metric-card">
          <div class="metric-title">Simulated CPU</div>
          <div class="metric-value" id="sim-cpu">--%</div>
          <div class="metric-sub" id="sim-cpu-sub">Current Baseline: --%</div>
        </div>
        <div class="metric-card">
          <div class="metric-title">Simulated RAM</div>
          <div class="metric-value" id="sim-ram">--%</div>
          <div class="metric-sub" id="sim-ram-sub">Current Baseline: --%</div>
        </div>
        <div class="metric-card">
          <div class="metric-title">Reclaimed RAM</div>
          <div class="metric-value" id="sim-freed">0 MB</div>
          <div class="metric-sub" id="sim-freed-sub">0 application(s) selected</div>
        </div>
        <div class="metric-card">
          <div class="metric-title">Simulated Health Score</div>
          <div class="metric-value" id="sim-health">--/100</div>
          <div class="metric-sub" id="sim-health-sub">Baseline: --/100</div>
        </div>
      </div>
      <div class="card" style="padding: 0; overflow: hidden;">
        <table>
          <thead>
            <tr>
              <th style="width: 50px;">Select</th>
              <th>PID</th>
              <th>Process Name</th>
              <th>CPU %</th>
              <th>RAM (MB)</th>
            </tr>
          </thead>
          <tbody id="simulator-tbody"></tbody>
        </table>
      </div>
    </div>

    <!-- PAGE 10: WORKLOAD PROFILES -->
    <div id="page-profiles" class="page">
      <div class="header">
        <div>
          <h1>🎯 Workload Profiles</h1>
          <p>Customize diagnostic sensitivity, monitoring cadence, and alert thresholds based on your current task</p>
        </div>
      </div>
      <div id="profiles-grid" class="grid-2"></div>
    </div>

    <!-- PAGE 11: SETTINGS -->
    <div id="page-settings" class="page">
      <div class="header">
        <div>
          <h1>Application Settings</h1>
          <p>Engine configuration and local preferences</p>
        </div>
      </div>
      <div class="card" style="display: flex; flex-direction: column; gap: 14px;">
        <div style="font-weight: 700;">Local Environment Status</div>
        <div style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.6;">
          • Telemetry Engine: <b>psutil + Windows PSAPI Native</b><br>
          • Database: <b>SQLite WAL Mode (%LOCALAPPDATA%/OSD/osd.db)</b><br>
          • AI/Assistant Mode: <b>100% Offline Rule-Based NLP (Zero External Telemetry)</b><br>
          • Desktop GUI: <b>PySide6-Essentials (Qt 6.8)</b>
        </div>
      </div>
    </div>

  </div>

  <script>
    let currentTab = 'overview';
    let allProcesses = [];
    const cpuHistory = [];
    const memHistory = [];

    function switchPage(pageId, btn) {
      document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
      const target = document.getElementById('page-' + pageId);
      if (target) target.classList.add('active');
      if (btn) btn.classList.add('active');
      currentTab = pageId;

      if (pageId === 'predictive') loadPredictiveAlerts();
      if (pageId === 'recovery') loadRecoveryPlans();
      if (pageId === 'history') loadHistory();
      if (pageId === 'simulator') loadSimulatorTable();
      if (pageId === 'profiles') loadProfiles();
    }

    async function fetchMetrics() {
      try {
        const res = await fetch('/api/metrics');
        const data = await res.json();
        renderOverview(data);
        renderCharts(data);
      } catch (e) {
        console.error(e);
      }
    }

    function renderOverview(data) {
      const snap = data.snapshot;
      const hs = data.health;
      
      document.getElementById('live-status').innerText = 'Live telemetry updated: ' + new Date().toLocaleTimeString() + ' • ' + snap.platform;
      
      const scoreNum = document.getElementById('health-score');
      scoreNum.innerText = Math.round(hs.total_score);
      scoreNum.style.color = hs.total_score >= 80 ? 'var(--green)' : (hs.total_score >= 60 ? 'var(--amber)' : 'var(--red)');
      
      document.getElementById('health-label').innerText = hs.total_score >= 80 ? 'Optimal' : (hs.total_score >= 60 ? 'Moderate Pressure' : 'High Contention');
      
      document.getElementById('bar-cpu').style.width = hs.cpu_score + '%';
      document.getElementById('val-cpu').innerText = Math.round(hs.cpu_score);
      document.getElementById('bar-mem').style.width = hs.memory_score + '%';
      document.getElementById('val-mem').innerText = Math.round(hs.memory_score);
      document.getElementById('bar-swap').style.width = hs.swap_score + '%';
      document.getElementById('val-swap').innerText = Math.round(hs.swap_score);
      document.getElementById('bar-disk').style.width = hs.disk_score + '%';
      document.getElementById('val-disk').innerText = Math.round(hs.disk_score);
      
      document.getElementById('factors-list').innerHTML = hs.factors.map(f => '• ' + f).join('<br>') || '• All components operating within normal ranges.';
      
      document.getElementById('card-cpu').innerText = snap.cpu_percent.toFixed(1) + '%';
      document.getElementById('card-cpu-sub').innerText = snap.logical_cores + ' logical cores • ' + Math.round(snap.frequency_mhz) + ' MHz';
      
      document.getElementById('card-mem').innerText = snap.memory_percent.toFixed(1) + '%';
      document.getElementById('card-mem-sub').innerText = (snap.memory_used_gb).toFixed(1) + ' / ' + (snap.memory_total_gb).toFixed(1) + ' GB';
      
      document.getElementById('card-disk').innerText = snap.disk_percent.toFixed(1) + '%';
      document.getElementById('card-disk-sub').innerText = snap.disk_free_gb.toFixed(1) + ' GB free space';
      
      document.getElementById('card-net').innerText = snap.net_down_speed;
      document.getElementById('card-net-sub').innerText = '↑ ' + snap.net_up_speed + '   ↓ ' + snap.net_down_speed;

      // Top Processes
      const procsList = document.getElementById('top-procs-list');
      procsList.innerHTML = (data.top_processes || []).slice(0, 5).map(p => `
        <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 4px;">
          <span style="font-weight: 600;">${p.name} (PID ${p.pid})</span>
          <span style="color: var(--accent-cyan);">${p.cpu.toFixed(1)}% CPU</span>
          <span style="color: var(--accent-violet);">${Math.round(p.memory_mb)} MB</span>
        </div>
      `).join('');

      // Alerts
      const alerts = data.diagnoses.filter(d => d.severity !== 'Healthy');
      const alertsList = document.getElementById('alerts-list');
      if (alerts.length === 0) {
        alertsList.innerHTML = '<div style="color: var(--green);">✅ No active bottlenecks detected.</div>';
      } else {
        alertsList.innerHTML = alerts.map(a => `
          <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
            <span>${a.title}</span>
            <span class="badge badge-${a.severity.toLowerCase()}">${a.severity}</span>
          </div>
        `).join('');
      }

      renderDiagnosis(data.diagnoses);
    }

    function renderDiagnosis(diags) {
      const container = document.getElementById('diag-results');
      if (!diags || diags.length === 0) {
        container.innerHTML = '<div class="card" style="color: var(--green); text-align: center; padding: 24px;">✅ No diagnostic bottlenecks found.</div>';
        return;
      }
      container.innerHTML = diags.map(d => `
        <div class="card" style="display: flex; flex-direction: column; gap: 6px; border-left: 4px solid ${d.severity === 'Critical' ? 'var(--red)' : (d.severity === 'Warning' ? 'var(--amber)' : 'var(--green)')};">
          <div style="display: flex; align-items: center; justify-content: space-between;">
            <div style="font-weight: 700; font-size: 1rem;">${d.title}</div>
            <div>
              <span style="font-size: 0.72rem; color: var(--text-muted); margin-right: 8px;">Strength: ${d.evidence_strength ? (d.evidence_strength*100).toFixed(0)+'%' : '80%'}</span>
              <span class="badge badge-${d.severity.toLowerCase()}">${d.severity}</span>
            </div>
          </div>
          <div style="font-size: 0.8rem; color: var(--text-secondary);"><b>Evidence:</b> ${d.evidence}</div>
          <div style="font-size: 0.8rem; color: var(--accent-cyan);"><b>Probable Cause:</b> ${d.probable_cause}</div>
          <div style="font-size: 0.8rem; color: var(--green);"><b>Recommended Action:</b> ${d.recommendation}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">${d.explanation}</div>
        </div>
      `).join('');
    }

    async function loadPredictiveAlerts() {
      try {
        const res = await fetch('/api/predictive');
        const data = await res.json();
        const container = document.getElementById('predictive-alerts-container');
        const alerts = data.predictions || [];
        if (alerts.length === 0) {
          container.innerHTML = '<div class="card" style="color: var(--green); text-align: center; padding: 28px;">✅ Trend projections stable. No impending resource exhaustion detected across recent metric samples.</div>';
          return;
        }
        container.innerHTML = alerts.map(a => `
          <div class="card" style="border-left: 4px solid ${a.severity==='Critical'?'var(--red)':'var(--amber)'};">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
              <span style="font-weight: 700; font-size: 1rem;">🔮 ${a.headline}</span>
              <span class="badge badge-${a.severity.toLowerCase()}">Confidence: ${a.confidence}</span>
            </div>
            <div style="font-size: 0.82rem; color: var(--text-secondary); margin-bottom: 6px;"><b>Evidence:</b> ${a.evidence}</div>
            <div style="font-size: 0.82rem; color: var(--accent-cyan); margin-bottom: 6px;"><b>Projected Exhaustion:</b> ${a.projected_minutes ? a.projected_minutes.toFixed(1) + ' minutes' : 'Continuous Pressure'}</div>
            <div style="font-size: 0.82rem; color: var(--green); margin-bottom: 6px;"><b>Prevention Action:</b> ${a.prevention_action}</div>
            <div style="font-size: 0.72rem; color: var(--text-muted); font-style: italic;">Assumptions: ${a.assumptions} | Limitations: ${a.limitations}</div>
          </div>
        `).join('');
      } catch (e) { console.error(e); }
    }

    async function loadRecoveryPlans() {
      try {
        const res = await fetch('/api/recovery');
        const data = await res.json();
        const container = document.getElementById('recovery-plans-container');
        const plans = data.plans || [];
        if (plans.length === 0) {
          container.innerHTML = '<div class="card" style="color: var(--green); text-align: center; padding: 24px;">✅ No corrective actions required. All hardware components are within safe thresholds.</div>';
        } else {
          container.innerHTML = plans.map(p => `
            <div class="card" style="display: flex; justify-content: space-between; align-items: center; border-left: 4px solid ${p.risk_level==='Low'?'var(--green)':'var(--amber)'};">
              <div>
                <div style="font-weight: 700; font-size: 0.95rem; margin-bottom: 4px;">${p.issue_title}</div>
                <div style="font-size: 0.8rem; color: var(--accent-cyan); margin-bottom: 2px;">Proposed: ${p.proposed_fix}</div>
                <div style="font-size: 0.8rem; color: var(--green); margin-bottom: 2px;">Expected Benefit: ${p.expected_benefit}</div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">Target: ${p.target_process} (PID ${p.target_pid}) | Risk: ${p.risk_level}</div>
              </div>
              <button class="btn-action" style="font-size: 0.8rem; padding: 8px 14px;" onclick="executeRecovery('${p.plan_id}', '${p.action_type}', ${p.target_pid}, '${p.target_process}')">🛡️ Approve & Execute</button>
            </div>
          `).join('');
        }

        // Render audit log
        const audit = data.audit_log || [];
        if (audit.length > 0) {
          document.getElementById('recovery-audit-log').innerHTML = audit.map(a => `
            • [${a.action_name}] on <b>${a.target_process}</b> (PID ${a.target_pid}) — Freed RAM: +${Math.round(a.freed_memory_mb)} MB | CPU Drop: -${a.cpu_drop.toFixed(1)}% | Health: ${Math.round(a.before_health)} ➔ ${Math.round(a.after_health)} (${a.verified ? '✅ Verified' : 'Logged'})
          `).join('<br>');
        }
      } catch (e) { console.error(e); }
    }

    async function executeRecovery(planId, actionType, pid, procName) {
      if (!confirm(`Confirm execution of recovery action: "${actionType}" on ${procName} (PID ${pid})?\\n\\nIdentity revalidation and outcome auditing will run automatically.`)) return;
      try {
        const res = await fetch('/api/execute_recovery', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ plan_id: planId, action_type: actionType, target_pid: pid, target_process: procName })
        });
        const result = await res.json();
        alert(result.message || 'Action executed successfully.');
        loadRecoveryPlans();
        fetchMetrics();
      } catch (e) { alert('Error: ' + e); }
    }

    async function sendChatMessage() {
      const input = document.getElementById('chat-input');
      const text = input.value.trim();
      if (!text) return;
      input.value = '';
      sendPrompt(text);
    }

    async function sendPrompt(text) {
      const box = document.getElementById('chat-messages');
      box.innerHTML += `<div class="chat-bubble chat-user"><b>You:</b> ${text}</div>`;
      box.scrollTop = box.scrollHeight;
      try {
        const res = await fetch('/api/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: text })
        });
        const data = await res.json();
        const formatted = (data.answer || '').replace(/\\n/g, '<br>');
        box.innerHTML += `<div class="chat-bubble chat-assistant"><b>OSD Assistant:</b><br>${formatted}</div>`;
        box.scrollTop = box.scrollHeight;
      } catch (e) {
        box.innerHTML += `<div class="chat-bubble chat-assistant"><b>Error:</b> Could not reach local assistant engine.</div>`;
      }
    }

    async function fetchProcesses() {
      try {
        const res = await fetch('/api/processes');
        allProcesses = await res.json();
        renderProcessTable(allProcesses);
      } catch (e) { console.error(e); }
    }

    function renderProcessTable(procs) {
      const tbody = document.getElementById('processes-tbody');
      tbody.innerHTML = procs.slice(0, 100).map(p => `
        <tr>
          <td style="color: var(--text-muted); font-family: monospace;">${p.pid}</td>
          <td style="font-weight: 600;">${p.name}</td>
          <td style="color: ${p.cpu > 20 ? 'var(--red)' : 'var(--text-primary)'};">${p.cpu.toFixed(1)}%</td>
          <td>${p.memory_percent.toFixed(1)}%</td>
          <td>${Math.round(p.memory_mb)} MB</td>
          <td><span style="color: var(--text-muted); font-size: 0.75rem;">${p.status}</span></td>
          <td>${p.threads}</td>
        </tr>
      `).join('');
    }

    function filterProcesses() {
      const q = document.getElementById('proc-search').value.toLowerCase();
      const filtered = allProcesses.filter(p => p.name.toLowerCase().includes(q) || String(p.pid).includes(q));
      renderProcessTable(filtered);
    }

    async function loadSimulatorTable() {
      await fetchProcesses();
      const tbody = document.getElementById('simulator-tbody');
      tbody.innerHTML = allProcesses.slice(0, 50).map(p => `
        <tr id="sim-row-${p.pid}">
          <td><input type="checkbox" class="sim-chk" value="${p.pid}" data-name="${p.name}" onchange="onSimulatorCheckChange(${p.pid})"></td>
          <td style="color: var(--text-muted); font-family: monospace;">${p.pid}</td>
          <td style="font-weight: 600;">${p.name}</td>
          <td style="color: ${p.cpu > 5 ? 'var(--red)' : 'var(--text-primary)'}; font-weight: ${p.cpu > 5 ? '700' : 'normal'};">${p.cpu.toFixed(1)}%</td>
          <td style="color: ${p.memory_mb > 500 ? 'var(--amber)' : 'var(--text-primary)'}; font-weight: ${p.memory_mb > 500 ? '700' : 'normal'};">${Math.round(p.memory_mb)} MB</td>
        </tr>
      `).join('');
      recalculateSimulation();
    }

    function onSimulatorCheckChange(pid) {
      const chk = document.querySelector(`.sim-chk[value="${pid}"]`);
      const row = document.getElementById('sim-row-' + pid);
      if (chk && row) {
        row.style.background = chk.checked ? 'rgba(130, 185, 177, 0.12)' : '';
      }
      recalculateSimulation();
    }

    function simulateSelectTop3() {
      simulateClearAll();
      const chks = document.querySelectorAll('.sim-chk');
      for (let i = 0; i < Math.min(3, chks.length); i++) {
        chks[i].checked = true;
        const row = document.getElementById('sim-row-' + chks[i].value);
        if (row) row.style.background = 'rgba(130, 185, 177, 0.12)';
      }
      recalculateSimulation();
    }

    function simulateSelectBrowsers() {
      simulateClearAll();
      const browserKeywords = ['chrome', 'msedge', 'edge', 'firefox', 'brave', 'opera'];
      document.querySelectorAll('.sim-chk').forEach(chk => {
        const name = (chk.getAttribute('data-name') || '').toLowerCase();
        if (browserKeywords.some(b => name.includes(b))) {
          chk.checked = true;
          const row = document.getElementById('sim-row-' + chk.value);
          if (row) row.style.background = 'rgba(130, 185, 177, 0.12)';
        }
      });
      recalculateSimulation();
    }

    function simulateClearAll() {
      document.querySelectorAll('.sim-chk').forEach(chk => {
        chk.checked = false;
        const row = document.getElementById('sim-row-' + chk.value);
        if (row) row.style.background = '';
      });
      recalculateSimulation();
    }

    async function recalculateSimulation() {
      const checkedPids = Array.from(document.querySelectorAll('.sim-chk:checked')).map(el => parseInt(el.value));
      const pill = document.getElementById('sim-status-pill');
      if (pill) {
        pill.innerText = checkedPids.length === 0 ? '0 apps selected (Showing current baseline)' : `${checkedPids.length} app(s) selected for simulated relief`;
      }
      try {
        const res = await fetch('/api/simulate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pids: checkedPids })
        });
        const r = await res.json();
        document.getElementById('sim-cpu').innerText = r.simulated_cpu.toFixed(1) + '%';
        document.getElementById('sim-cpu-sub').innerText = checkedPids.length > 0 ?
          `Original: ${r.original_cpu.toFixed(1)}% (-${r.cpu_reduction.toFixed(1)}% drop)` :
          `Current Baseline: ${r.original_cpu.toFixed(1)}%`;

        document.getElementById('sim-ram').innerText = r.simulated_mem_percent.toFixed(1) + '%';
        document.getElementById('sim-ram-sub').innerText = checkedPids.length > 0 ?
          `Original: ${r.original_mem_percent.toFixed(1)}% (-${r.mem_percent_reduction.toFixed(1)}% drop)` :
          `Current Baseline: ${r.original_mem_percent.toFixed(1)}%`;

        document.getElementById('sim-freed').innerText = '+' + Math.round(r.freed_memory_mb) + ' MB';
        document.getElementById('sim-freed-sub').innerText = `${checkedPids.length} application(s) selected`;

        document.getElementById('sim-health').innerText = Math.round(r.simulated_health_score) + '/100';
        document.getElementById('sim-health-sub').innerText = checkedPids.length > 0 ?
          `Gain: +${r.health_score_gain.toFixed(1)} pts (Swap: ${r.swap_relief_level})` :
          `Baseline: ${Math.round(r.original_health_score)}/100 (No change)`;
      } catch (e) { console.error(e); }
    }

    async function loadProfiles() {
      try {
        const res = await fetch('/api/profiles');
        const data = await res.json();
        const active = data.active;
        const profs = data.profiles || [];
        const container = document.getElementById('profiles-grid');
        container.innerHTML = profs.map(p => `
          <div class="card" style="border: ${p.name===active?'2px solid var(--accent-cyan)':'1px solid var(--border)'};">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <span style="font-weight: 700; font-size: 1.05rem;">${p.icon} ${p.display_title}</span>
              ${p.name===active?'<span class="badge badge-healthy">ACTIVE</span>':`<button class="btn-secondary" style="font-size: 0.75rem; padding: 4px 10px;" onclick="activateProfile('${p.name}')">Activate</button>`}
            </div>
            <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 8px; line-height: 1.4;">${p.description}</div>
            <div style="font-size: 0.72rem; color: var(--text-muted);">
              • Thresholds: CPU Warn ${p.cpu_warning}%, RAM Warn ${p.memory_warning}%<br>
              • Monitoring Cadence: ${p.refresh_interval_sec}s interval
            </div>
          </div>
        `).join('');
      } catch (e) { console.error(e); }
    }

    async function activateProfile(name) {
      try {
        await fetch('/api/set_profile', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ profile: name })
        });
        loadProfiles();
        fetchMetrics();
      } catch (e) { alert('Error: ' + e); }
    }

    async function loadHistory() {
      try {
        const res = await fetch('/api/history');
        const rows = await res.json();
        const tbody = document.getElementById('history-tbody');
        tbody.innerHTML = rows.map(r => `
          <tr>
            <td style="color: var(--text-muted);">${r.time}</td>
            <td style="color: ${r.health_score>=80?'var(--green)':'var(--amber)'}; font-weight: 600;">${Math.round(r.health_score)}</td>
            <td>${r.cpu_percent.toFixed(1)}%</td>
            <td>${r.memory_percent.toFixed(1)}%</td>
            <td>${r.swap_percent.toFixed(1)}%</td>
            <td>${r.disk_percent.toFixed(1)}%</td>
            <td>${r.process_count}</td>
          </tr>
        `).join('');
      } catch (e) { console.error(e); }
    }

    function renderCharts(data) {
      const snap = data.snapshot;
      cpuHistory.push(snap.cpu_percent);
      if (cpuHistory.length > 30) cpuHistory.shift();
      memHistory.push(snap.memory_percent);
      if (memHistory.length > 30) memHistory.shift();

      drawSparkline('chart-cpu', cpuHistory, '#22d3ee');
      drawSparkline('chart-mem', memHistory, '#8b5cf6');
    }

    function drawSparkline(canvasId, values, color) {
      const c = document.getElementById(canvasId);
      if (!c) return;
      const ctx = c.getContext('2d');
      const w = c.width;
      const h = c.height;
      ctx.clearRect(0, 0, w, h);
      if (values.length < 2) return;

      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      const step = w / (values.length - 1);
      values.forEach((v, i) => {
        const y = h - (v / 100) * h;
        if (i === 0) ctx.moveTo(0, y);
        else ctx.lineTo(i * step, y);
      });
      ctx.stroke();

      ctx.lineTo(w, h);
      ctx.lineTo(0, h);
      ctx.closePath();
      ctx.fillStyle = color + '22';
      ctx.fill();
    }

    async function triggerDiagnosis() {
      const btn = document.querySelector('.btn-action');
      if (btn) btn.innerText = '⏳ Scanning...';
      try {
        const res = await fetch('/api/diagnose', { method: 'POST' });
        const data = await res.json();
        renderOverview(data);
        switchPage('diagnosis', document.querySelectorAll('.nav-btn')[3]);
      } finally {
        if (btn) btn.innerText = '🔍 Diagnose My PC';
      }
    }

    // Refresh cycles
    fetchMetrics();
    fetchProcesses();
    setInterval(fetchMetrics, 2000);
    setInterval(fetchProcesses, 4000);
  </script>
</body>
</html>
"""


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(ROOT_DIR, "web")
PREVIEWS_DIR = os.path.join(ROOT_DIR, "app_previews")
ASSETS_DIR = os.path.join(ROOT_DIR, "assets")


class OSDRequestHandler(BaseHTTPRequestHandler):
    pass


class OSenseRequestHandler(OSDRequestHandler):
    """Backward-compatible alias for OSenseRequestHandler."""
    pass


# Rebind implementation onto OSDRequestHandler
class OSDRequestHandler(BaseHTTPRequestHandler):
    def _serve_file(self, filepath, content_type=None):
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
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(data)
        except Exception:
            self.send_response(500)
            self.end_headers()

    def _serve_from_dir(self, base_dir, rel_path):
        norm_base = os.path.abspath(base_dir)
        full_path = os.path.abspath(os.path.join(norm_base, rel_path.lstrip("/\\")))
        if not full_path.startswith(norm_base):
            self.send_response(403)
            self.end_headers()
            return
        self._serve_file(full_path)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/" or url.path == "/index.html":
            index_path = os.path.join(WEB_DIR, "index.html")
            if os.path.exists(index_path):
                self._serve_file(index_path, "text/html; charset=utf-8")
            else:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(HTML_PAGE.encode("utf-8"))

        elif url.path.startswith("/app_previews/"):
            rel_path = url.path[len("/app_previews/"):]
            self._serve_from_dir(PREVIEWS_DIR, rel_path)

        elif url.path.startswith("/assets/"):
            rel_path = url.path[len("/assets/"):]
            self._serve_from_dir(ASSETS_DIR, rel_path)

        elif url.path.startswith("/web/"):
            rel_path = url.path[len("/web/"):]
            self._serve_from_dir(WEB_DIR, rel_path)

        elif url.path == "/api/metrics":
            with telemetry_worker.lock:
                snap = telemetry_worker.latest_snapshot
                health = telemetry_worker.latest_health
                diags = telemetry_worker.latest_diagnoses
                recs = telemetry_worker.latest_recommendations
                procs = telemetry_worker.latest_processes

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
                'recommendations': [r.to_dict() for r in recs],
                'top_processes': [
                    {'name': p.name, 'pid': p.pid, 'cpu': p.cpu_percent, 'memory_mb': p.memory_mb}
                    for p in procs[:5]
                ],
            }
            self._send_json(payload)

        elif url.path == "/api/processes":
            with telemetry_worker.lock:
                procs = list(telemetry_worker.latest_processes)
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

        elif url.path == "/api/predictive":
            with telemetry_worker.lock:
                preds = list(telemetry_worker.latest_predictions)
            payload = {'predictions': [a.to_dict() for a in preds]}
            self._send_json(payload)

        elif url.path == "/api/recovery":
            with telemetry_worker.lock:
                snap = telemetry_worker.latest_snapshot
                procs = telemetry_worker.latest_processes
                diags = telemetry_worker.latest_diagnoses
            plans = advisor.generate_plans(diags, snap, procs)
            audit = db.get_recovery_actions(limit=10)
            payload = {
                'plans': [p.to_dict() for p in plans],
                'audit_log': audit
            }
            self._send_json(payload)

        elif url.path == "/api/profiles":
            active = profile_mgr.get_active_profile_name()
            profs = [p.to_dict() for p in profile_mgr.profiles.values()]
            self._send_json({'active': active, 'profiles': profs})

        elif url.path == "/api/history":
            history = db.get_resource_history(hours=24.0, limit=50)
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
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8') if length > 0 else ""
        data = json.loads(body) if body else {}

        if url.path == "/api/diagnose":
            with telemetry_worker.lock:
                snap = telemetry_worker.latest_snapshot
                procs = telemetry_worker.latest_processes
                health = telemetry_worker.latest_health
                diags = telemetry_worker.latest_diagnoses
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

        elif url.path == "/api/ask":
            question = data.get('question', '')
            answer = chat_engine.ask(question)
            self._send_json({'question': question, 'answer': answer})

        elif url.path == "/api/simulate":
            pids = set(data.get('pids', []))
            with telemetry_worker.lock:
                snap = telemetry_worker.latest_snapshot
                procs = telemetry_worker.latest_processes
            selected = [p for p in procs if p.pid in pids]
            res = simulator.simulate_closing_processes(snap, selected)
            self._send_json(res.to_dict())

        elif url.path == "/api/set_profile":
            name = data.get('profile', '')
            ok = profile_mgr.set_active_profile(name)
            if ok:
                prof = profile_mgr.get_active_profile()
                analysis.thresholds.cpu_warning = prof.cpu_warning
                analysis.thresholds.cpu_critical = prof.cpu_critical
                analysis.thresholds.memory_warning = prof.memory_warning
                analysis.thresholds.memory_critical = prof.memory_critical
            self._send_json({'success': ok, 'active': profile_mgr.get_active_profile_name()})

        elif url.path == "/api/execute_recovery":
            from app.recommendations.recovery_advisor import RecoveryPlan
            plan = RecoveryPlan(
                plan_id=data.get('plan_id', 'manual'),
                issue_title=f"Manual execution on {data.get('target_process')}",
                action_type=data.get('action_type', 'trim_memory'),
                target_process=data.get('target_process', ''),
                target_pid=int(data.get('target_pid', 0)),
                proposed_fix="User-approved manual action",
                expected_benefit="Free resources",
                risk_level="Medium",
                evidence="Executed from dashboard",
                probable_cause="User approval"
            )
            ver = advisor.execute_approved_action(plan)
            self._send_json({
                'success': ver.success,
                'message': ver.message,
                'freed_memory_mb': ver.freed_memory_mb,
                'cpu_drop': ver.cpu_drop,
                'health_gain': ver.health_gain
            })

        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, data):
        blob = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(blob)))
        self.end_headers()
        self.wfile.write(blob)

    def log_message(self, format, *args):
        pass  # Quiet server logs


def run_server(port=8080):
    from osd_core.agent.server import OSDAgent
    agent = OSDAgent(project_root=os.path.dirname(os.path.abspath(__file__)), host="127.0.0.1", port=port)
    agent.serve()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
