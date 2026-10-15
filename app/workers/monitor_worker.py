"""
Background Workers — QThread-based workers for non-blocking monitoring.
"""
import time
import traceback
from PySide6.QtCore import QThread, Signal, QMutex
from app.monitoring.system_monitor import SystemMonitor, SystemSnapshot, ProcessInfo
from app.analysis.engine import AnalysisEngine, HealthScoreBreakdown, Diagnosis
from app.recommendations.engine import RecommendationEngine, Recommendation
from app.database.db_manager import DatabaseManager
from app.analysis.predictive_engine import PredictiveEngine, PredictiveAlert
from app.monitoring.behavior_monitor import ProcessBehaviorMonitor, BehaviorAlert
from app.recommendations.recovery_advisor import RecoveryAdvisor, RecoveryPlan


class MonitorWorker(QThread):
    """Background worker for continuous system monitoring."""
    
    snapshot_ready = Signal(object)        # SystemSnapshot
    processes_ready = Signal(object)       # list[ProcessInfo]
    health_ready = Signal(object)          # HealthScoreBreakdown
    diagnoses_ready = Signal(object)       # list[Diagnosis]
    recommendations_ready = Signal(object) # list[Recommendation]
    predictions_ready = Signal(object)     # list[PredictiveAlert]
    behavior_alerts_ready = Signal(object) # list[BehaviorAlert]
    recovery_plans_ready = Signal(object)  # list[RecoveryPlan]
    error_occurred = Signal(str)
    
    def __init__(self, monitor: SystemMonitor, analysis: AnalysisEngine,
                 recommender: RecommendationEngine, db: DatabaseManager,
                 predictive: PredictiveEngine, behavior: ProcessBehaviorMonitor,
                 advisor: RecoveryAdvisor, parent=None):
        super().__init__(parent)
        self.monitor = monitor
        self.analysis = analysis
        self.recommender = recommender
        self.db = db
        self.predictive = predictive
        self.behavior = behavior
        self.advisor = advisor
        self._running = True
        self._interval = 2.0  # seconds
        self._mutex = QMutex()
        self._sample_counter = 0
        self._db_save_interval = 5  # save to DB every N samples
    
    def set_interval(self, seconds: float):
        self._mutex.lock()
        self._interval = max(1.0, min(10.0, seconds))
        self._mutex.unlock()
    
    def stop(self):
        self._mutex.lock()
        self._running = False
        self._mutex.unlock()
    
    def run(self):
        while True:
            self._mutex.lock()
            running = self._running
            interval = self._interval
            self._mutex.unlock()
            
            if not running:
                break
            
            try:
                # Collect snapshot
                snapshot = self.monitor.collect_snapshot()
                self.snapshot_ready.emit(snapshot)
                
                # Collect processes
                processes = self.monitor.get_processes(sort_by="cpu", limit=200)
                self.processes_ready.emit(processes)
                
                # Add to analysis history and calculate health
                self.analysis.add_snapshot(snapshot)
                self.predictive.add_snapshot(snapshot)
                health = self.analysis.calculate_health_score(snapshot)
                self.health_ready.emit(health)
                
                # Run diagnosis
                diagnoses_obj = self.analysis.diagnose(snapshot, processes)
                self.diagnoses_ready.emit(diagnoses_obj)
                
                # Generate recommendations & recovery plans
                recommendations = self.recommender.generate(diagnoses_obj, snapshot, processes)
                self.recommendations_ready.emit(recommendations)
                
                # Predictive Early Warnings
                pred_alerts = self.predictive.analyze_predictions(snapshot, processes)
                self.predictions_ready.emit(pred_alerts)

                # Process Behavior Anomalies
                beh_alerts = self.behavior.analyze_processes(processes)
                self.behavior_alerts_ready.emit(beh_alerts)

                # Autonomous Recovery Plans
                recovery_plans = self.advisor.generate_plans(diagnoses_obj, snapshot, processes)
                self.recovery_plans_ready.emit(recovery_plans)
                
                # Save to database periodically
                self._sample_counter += 1
                if self._sample_counter >= self._db_save_interval:
                    self._sample_counter = 0
                    try:
                        self.db.save_resource_sample(
                            timestamp=snapshot.timestamp,
                            cpu=snapshot.cpu.overall_percent,
                            memory=snapshot.memory.percent,
                            swap=snapshot.memory.swap_percent,
                            disk=snapshot.disk.percent,
                            disk_read=snapshot.disk.read_bytes_per_sec,
                            disk_write=snapshot.disk.write_bytes_per_sec,
                            net_up=snapshot.network.upload_speed,
                            net_down=snapshot.network.download_speed,
                            proc_count=snapshot.process_count,
                            health_score=health.total_score,
                        )
                    except Exception:
                        pass
                
            except Exception as e:
                self.error_occurred.emit(f"Monitoring error: {str(e)}")
            
            # Sleep in small increments to allow stopping
            elapsed = 0.0
            while elapsed < interval:
                self._mutex.lock()
                still_running = self._running
                self._mutex.unlock()
                if not still_running:
                    return
                time.sleep(0.2)
                elapsed += 0.2


class DiagnosisWorker(QThread):
    """Worker for running a full system diagnosis (Diagnose My PC)."""
    
    diagnosis_complete = Signal(object)  # full report dict
    progress_update = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self, monitor: SystemMonitor, analysis: AnalysisEngine,
                 recommender: RecommendationEngine, db: DatabaseManager,
                 parent=None):
        super().__init__(parent)
        self.monitor = monitor
        self.analysis = analysis
        self.recommender = recommender
        self.db = db
    
    def run(self):
        try:
            self.progress_update.emit("Collecting system metrics...")
            snapshots = []
            
            # Collect multiple samples
            for i in range(3):
                self.progress_update.emit(f"Collecting sample {i+1}/3...")
                snap = self.monitor.collect_snapshot()
                snapshots.append(snap)
                self.analysis.add_snapshot(snap)
                if i < 2:
                    time.sleep(1.5)
            
            self.progress_update.emit("Analyzing processes...")
            processes = self.monitor.get_processes(sort_by="cpu", limit=200)
            
            self.progress_update.emit("Running analysis engine...")
            latest = snapshots[-1]
            health = self.analysis.calculate_health_score(latest)
            diagnoses = self.analysis.diagnose(latest, processes)
            
            self.progress_update.emit("Generating recommendations...")
            recommendations = self.recommender.generate(diagnoses, latest, processes)
            
            # Build full report
            report = {
                'timestamp': time.time(),
                'health_score': health.to_dict(),
                'diagnoses': [d.to_dict() for d in diagnoses],
                'recommendations': [r.to_dict() for r in recommendations],
                'snapshot': {
                    'cpu_percent': latest.cpu.overall_percent,
                    'per_core': latest.cpu.per_core_percent,
                    'memory_percent': latest.memory.percent,
                    'memory_available_gb': latest.memory.available / (1024**3),
                    'memory_total_gb': latest.memory.total / (1024**3),
                    'swap_percent': latest.memory.swap_percent,
                    'disk_percent': latest.disk.percent,
                    'disk_free_gb': latest.disk.free / (1024**3),
                    'disk_read_mbps': latest.disk.read_bytes_per_sec / (1024*1024),
                    'disk_write_mbps': latest.disk.write_bytes_per_sec / (1024*1024),
                    'net_upload_kbps': latest.network.upload_speed / 1024,
                    'net_download_kbps': latest.network.download_speed / 1024,
                    'process_count': latest.process_count,
                    'uptime_hours': latest.uptime_seconds / 3600,
                    'platform': latest.platform_info,
                },
                'top_processes': [
                    {'name': p.name, 'pid': p.pid, 'cpu': p.cpu_percent, 'memory_mb': p.memory_mb}
                    for p in sorted(processes, key=lambda x: x.cpu_percent, reverse=True)[:10]
                ],
                'samples_collected': len(snapshots),
            }
            
            # Save to database
            self.progress_update.emit("Saving results...")
            for diag in diagnoses:
                try:
                    import json
                    self.db.save_diagnosis(
                        timestamp=report['timestamp'],
                        title=diag.title,
                        severity=diag.severity,
                        evidence=diag.evidence,
                        probable_cause=diag.probable_cause,
                        confidence=diag.confidence,
                        recommendation=diag.recommendation,
                        explanation=diag.explanation,
                        report_json=json.dumps(report),
                    )
                except Exception:
                    pass
            
            self.progress_update.emit("Diagnosis complete!")
            self.diagnosis_complete.emit(report)
            
        except Exception as e:
            self.error_occurred.emit(f"Diagnosis failed: {str(e)}\n{traceback.format_exc()}")
