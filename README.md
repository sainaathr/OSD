# ⚡ OSD — Know Your Machine
### PC Health & Performance Intelligence

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PySide6--Essentials%20(Qt6)-41CD52?logo=qt&logoColor=white)](https://wiki.qt.io/Qt_for_Python)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11%20%7C%20Linux%20%7C%20macOS-0078D6?logo=windows11&logoColor=white)](https://microsoft.com)
[![Testing](https://img.shields.io/badge/pytest-80%20passed%20(100%25)-success?logo=pytest)](https://pytest.org/)
[![Privacy](https://img.shields.io/badge/Privacy-100%25%20Local%20%7C%20Zero%20External%20Telemetry-purple)](https://github.com)

**OSD** helps people understand their PC's health, discover performance bottlenecks, monitor system resources in real-time, and find sensible, verified ways to improve performance. Evolving far beyond a traditional Task Manager, OSD translates raw operating system telemetry into understandable diagnostic narratives, resource exhaustion runways, and safe recovery paths.

> *"Your PC has a story. Read the signals. Know your machine."*

---

## 🌟 OSD Core Features

### 🔮 1. Predictive Performance Engine (`app/analysis/predictive_engine.py`)
- **Time-Series Slope Estimation:** Computes rate of change ($\Delta y / \Delta t$) and Pearson correlation coefficients ($R^2$) across rolling metric samples.
- **Time-to-Exhaustion Projections:** Predicts when physical RAM or page file swap will be saturated based on steady consumption trajectories.
- **Early Warnings Without False Alarms:** Requires sustained multi-sample momentum ($R^2 \ge 0.55$) before triggering warnings, preventing alarms on transient spikes.
- **Confidence & Limitations Transparency:** Every early alert displays confidence level (`Low`, `Medium`, `High`), evidence metrics, underlying assumptions, and operating system intervention limitations.

### 🔍 2. Advanced Root-Cause Investigation (`app/analysis/engine.py`)
- **Multi-Resource Bottleneck Correlation:** Identifies complex scenarios such as *Virtual Memory Thrashing* (high RAM + high swap + disk paging) and *Compute + Disk Saturation*.
- **Process Grouping & Trees:** Groups parent-child process trees (e.g. Chrome, IDEs, build workers) by executable name to show collective resource consumption.
- **Evidence Strength Ranking:** Diagnoses include a normalized `evidence_strength` (0.0 to 1.0) and category classification.
- **Clear English Explanations:** Explains every bottleneck clearly without technical jargon.

### 🛡️ 3. Autonomous Recovery Advisor (`app/recommendations/recovery_advisor.py`)
- **6-Step Verified Lifecycle:**
  $$\text{Detect} \longrightarrow \text{Investigate} \longrightarrow \text{Recommend} \longrightarrow \text{Consent} \longrightarrow \text{Execute} \longrightarrow \text{Verify}$$
- **Disruption & Risk Ranking:**
  - **Low Risk:** Windows working set memory trimming (`ctypes.windll.psapi.EmptyWorkingSet`) or background thread priority reduction (`psutil.BELOW_NORMAL_PRIORITY_CLASS`) without closing apps.
  - **Medium Risk:** Graceful termination of non-essential processes with user confirmation.
- **Zero Accidental Kills (Identity Revalidation):** Revalidates that the target PID matches the expected executable name immediately before execution to prevent PID-reuse accidents.
- **Protected OS Whitelist:** Strictly refuses actions against Windows critical processes (`csrss.exe`, `explorer.exe`, `svchost.exe`, `services.exe`, `dwm.exe`, `lsass.exe`, `windowsdefender`).
- **Before-and-After Verification Auditing:** Samples telemetry immediately before and after execution to calculate freed RAM, CPU drop, and Health Score gains, saving verified records to SQLite.

### 💬 4. Ask OSD Assistant (`app/assistant/chat_engine.py`)
- **Offline Natural Language Query Engine:** Answers questions using actual system state, live metrics, and SQLite history without sending telemetry to external clouds.
- **Supported Query Categories:**
  - *"Why is my PC slow?"* — Explains primary bottleneck, evidence, and active hogs.
  - *"Which process uses the most memory?"* — Returns top consumer, memory footprint, and system availability.
  - *"Which process uses the most CPU?"* — Identifies top compute-bound process and threads.
  - *"What has changed recently?"* — Compares live telemetry against historical averages.
  - *"Which recommendation is safest?"* — Identifies low-disruption options.
  - *"Is the memory usage increasing?"* — Evaluates rolling memory slopes and leak alerts.
  - *"Did the last recovery action improve performance?"* — Pulls verified audit records of freed RAM and CPU drops.

### ⏳ 5. System Time Machine (`app/ui/pages/timeline_page.py`)
- **Historical Reconstruction:** Explore CPU, RAM, swap, disk I/O, and network trends across 1 hour, 6 hours, 24 hours, or 7 days.
- **Session Analytics:** Computes average CPU, peak CPU, average RAM, peak RAM, average Health Score, and verified action count.
- **Track 1:** 🛡️ Verified Action Outcomes table (freed RAM, CPU drop, before/after health, status).
- **Track 2:** 📈 Resource Metric History table.
- **Track 3:** 🔍 Historical Diagnoses and Behavior Alerts.

### 🎯 6. Workload Profiles (`app/profiles/profile_manager.py`)
- **Adaptive Sensitivity Profiles:**
  - **📚 Study / Quiet:** Low CPU threshold (60%), warns early on background CPU hogs to minimize fan noise.
  - **💻 Coding & Development:** Tolerates high CPU compilation bursts (85% warn, 95% crit), suppresses transient CPU alerts, focuses on runaway memory leaks.
  - **🎮 Gaming & High Performance:** High CPU/RAM tolerance (90% CPU warn), prioritizes background disk I/O and network saturation that cause game stutter.
  - **🔋 Battery Saver:** Throttles monitoring cadence (4.0s interval) to save power, alerts on high battery-drain background services.
  - **⚙️ Custom Profile:** Fully user-configurable warning and critical limits.
- **Persistent SQLite Storage:** Workload profile selection persists across restarts.

### 🧪 7. What-If Resource Simulator (`app/analysis/simulator.py`)
- **Sandboxed Estimation:** Select any combination of running processes to hypothetically estimate RAM recovery, CPU reduction, and Health Score gains.
- **Zero Side-Effects:** Never touches, suspends, or terminates running processes during simulation.
- **Transparent Calculations:** Displays baseline vs. simulated metrics side-by-side with clear assumptions.

### 👁️ 8. Process Behavior Monitor (`app/monitoring/behavior_monitor.py`)
- **Non-Invasive Anomaly Detection:**
  - Sudden CPU surges (>45% jump in a single interval).
  - Monotonic memory growth (uninterrupted growth across consecutive samples).
  - Rapid thread expansion (>40 new threads in a single step).
- **Responsible Labeling:** Clearly identifies behavioral anomalies as requiring investigation without making false malware claims from resource metrics alone.

### 🖥️ 9. Premium Desktop UI (`app/ui`)
- **11 Modular Navigation Views:** Overview, Processes, Performance, Diagnosis, Predictive Alerts, Recovery Advisor, Ask OSD, System History, What-If Simulator, Workload Profiles, Settings.
- **Sleek Dark Theme:** Curated deep charcoal palette with restrained cyan (`#22d3ee`) and violet (`#8b5cf6`) accents, clean typography, and responsive layouts.

---

## 🏗️ Architecture & Component Separation

```
os project/
├── main.py                     # Desktop application launcher (PySide6)
├── web_dashboard.py            # Local HTTP companion dashboard (port 8080)
├── run.bat                     # Windows one-click launcher
├── requirements.txt            # Project dependencies
├── app/
│   ├── monitoring/             # Telemetry collection & safe process control
│   │   ├── system_monitor.py   # psutil metrics, process groups, working set trim
│   │   └── behavior_monitor.py # Anomaly detection (surges, leaks, thread explosion)
│   ├── analysis/               # Diagnostic & predictive intelligence
│   │   ├── engine.py           # Health scoring (0-100), root-cause analysis
│   │   ├── predictive_engine.py# Linear regression slopes & time-to-exhaustion
│   │   └── simulator.py        # What-If sandboxed resource calculations
│   ├── recommendations/        # Safe corrective guidance & execution
│   │   ├── engine.py           # Static rule-based recommendations
│   │   └── recovery_advisor.py # 6-step recovery lifecycle & verification audit
│   ├── assistant/              # Conversational natural language assistant
│   │   └── chat_engine.py      # Offline query engine grounded in live telemetry
│   ├── profiles/               # Adaptive workload configurations
│   │   └── profile_manager.py  # Study, Coding, Gaming, Battery Saver, Custom
│   ├── database/               # Local persistent storage
│   │   └── db_manager.py       # SQLite WAL mode, samples, actions, alerts
│   ├── ui/                     # PySide6 desktop views
│   │   ├── main_window.py      # 11-view sidebar window & worker wiring
│   │   ├── styles.py           # Modern dark theme styles
│   │   └── pages/              # 11 dedicated functional page widgets
│   ├── utils/                  # Unit conversions, timestamp & color formatters
│   │   └── formatting.py
│   └── workers/                # Non-blocking QThread background monitoring
│       └── monitor_worker.py
└── tests/                      # Automated test suite (52 unit tests)
    ├── test_analysis_engine.py
    ├── test_assistant_engine.py
    ├── test_behavior_monitor.py
    ├── test_database.py
    ├── test_diagnosis_worker.py
    ├── test_monitoring.py
    ├── test_predictive_engine.py
    ├── test_profiles.py
    ├── test_recommendations.py
    ├── test_recovery_advisor.py
    └── test_simulator.py
```

---

## 🚀 Launch Instructions

### Option A: Windows One-Click Batch Script
Double-click `run.bat` or run:
```cmd
run.bat
```
This automatically verifies Python 3.11+, activates the virtual environment, verifies dependencies, and starts OSD.

### Option B: Manual Launch from Shell
```powershell
# 1. Activate the virtual environment
.\.venv\Scripts\activate

# 2. Launch the desktop GUI
python main.py
```

### Option C: Optional Web Companion Dashboard
```powershell
.\.venv\Scripts\python.exe web_dashboard.py 8080
```
Then open `http://localhost:8080/` in any modern web browser.

---

## 🧪 Automated Test Verification

OSD includes a comprehensive 80-test automated suite covering cross-platform adapters, local agent security, predictive forecasting, recovery auditing, process safety, natural language queries, and database persistence:

```powershell
.\.venv\Scripts\pytest.exe -v
```

### Verified Test Results:
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
collected 80 items

tests/test_agent_security.py ................................... [  8%]
tests/test_analysis_engine.py .................................. [ 18%]
tests/test_assistant_engine.py ................................ [ 27%]
tests/test_behavior_monitor.py ................................. [ 31%]
tests/test_cross_platform_paths.py ............................ [ 41%]
tests/test_database.py ........................................ [ 52%]
tests/test_diagnosis_worker.py ................................. [ 53%]
tests/test_monitoring.py ....................................... [ 60%]
tests/test_osd_core_models.py ................................. [ 66%]
tests/test_platform_adapters.py ............................... [ 76%]
tests/test_predictive_engine.py ................................ [ 81%]
tests/test_profiles.py ......................................... [ 87%]
tests/test_recommendations.py .................................. [ 93%]
tests/test_recovery_advisor.py ................................. [ 97%]
tests/test_simulator.py ........................................ [100%]

============================= 80 passed in 24.35s =============================
```

---

## 📦 Standalone Packaging & Distribution

OSD provides standalone PyInstaller packaging with zero Python installation required for end users:

### Windows 10/11:
```cmd
scripts\build_windows.bat
# Output: dist\OSD\OSD.exe
```

### Linux (Ubuntu, Debian, Fedora, Arch):
```bash
chmod +x scripts/build_linux.sh
./scripts/build_linux.sh
# Output: dist/OSD/OSD
```

### macOS (Apple Silicon & Intel):
```bash
chmod +x scripts/build_macos.sh
./scripts/build_macos.sh
# Output: dist/OSD
```

Detailed signing, notarization, and distribution workflows are available in [docs/PACKAGING.md](file:///c:/Users/Administrator/Desktop/Projects/os%20project/docs/PACKAGING.md).

---

## 🛡️ Safety Guarantees & Known Limitations

1. **Read-Only by Default:** OSD never terminates processes or modifies system priorities without explicit user review and confirmation.
2. **Revalidation Guarantee:** Process identity is strictly verified by PID and executable name immediately before executing any approved action to prevent PID reuse errors.
3. **Protected Process Safeguards:** Core operating system components (`csrss.exe`, `explorer.exe`, `svchost.exe`, `systemd`, `launchd`, etc.) can never be targeted for termination.
4. **Platform Scope:** Advanced working set memory page trimming uses the Windows PSAPI (`ctypes.windll.psapi.EmptyWorkingSet`). On non-Windows platforms (Linux/macOS), graceful termination and POSIX nice priority adjustment remain fully functional while unsupported memory trimming gracefully degrades without crashing.
5. **Privacy Guarantee:** Zero cloud telemetry is transmitted. All diagnostic calculations, forecasts, and conversational queries execute locally on your machine.
6. **Agent Security:** The optional local monitoring agent strictly binds to loopback (`127.0.0.1`), enforces origin validation, supports Private Network Access preflights, requires pairing tokens, and disallows dangerous remote execution.
