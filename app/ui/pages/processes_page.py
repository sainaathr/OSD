"""
Processes Page — Precision Process Explorer & Inspector
Clean, information-dense process table with contextual details inspector and safety checks.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QMessageBox, QAbstractItemView, QFrame, QMenu
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont, QAction, QColor

from app.ui.styles import COLORS, card_style, panel_alt_style
from app.ui.components import PageHeader, ConfirmationModal
from app.monitoring.system_monitor import SystemMonitor, ProcessInfo


class ProcessesPage(QWidget):
    """Refined Process Explorer with contextual inspector drawer."""

    def __init__(self, monitor: SystemMonitor, parent=None):
        super().__init__(parent)
        self.monitor = monitor
        self._all_processes: list[ProcessInfo] = []
        self._sort_by = "cpu"
        self._search_text = ""
        self._filter_mode = "all"  # 'all', 'high_cpu', 'high_ram'
        self._selected_proc: ProcessInfo = None
        self._dirty = True
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Header
        header = PageHeader(
            eyebrow="SYSTEM SUBPROCESSES",
            title="Process Explorer",
            description="Live task scheduler telemetry, thread hierarchy, memory footprint auditing, and safe process termination."
        )
        layout.addWidget(header)

        # Controls & Filter Bar
        controls = QHBoxLayout()
        controls.setSpacing(10)

        # Search field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter processes by name or PID...")
        self.search_input.setFixedHeight(34)
        self.search_input.setMinimumWidth(320)
        self.search_input.textChanged.connect(self._on_search)
        controls.addWidget(self.search_input)

        # Quick filters
        self.filter_all_btn = QPushButton("All")
        self.filter_all_btn.setFixedHeight(34)
        self.filter_all_btn.setCheckable(True)
        self.filter_all_btn.setChecked(True)
        self.filter_all_btn.clicked.connect(lambda: self._set_filter("all"))
        controls.addWidget(self.filter_all_btn)

        self.filter_cpu_btn = QPushButton("High CPU (>15%)")
        self.filter_cpu_btn.setFixedHeight(34)
        self.filter_cpu_btn.setCheckable(True)
        self.filter_cpu_btn.clicked.connect(lambda: self._set_filter("high_cpu"))
        controls.addWidget(self.filter_cpu_btn)

        self.filter_ram_btn = QPushButton("High RAM (>500MB)")
        self.filter_ram_btn.setFixedHeight(34)
        self.filter_ram_btn.setCheckable(True)
        self.filter_ram_btn.clicked.connect(lambda: self._set_filter("high_ram"))
        controls.addWidget(self.filter_ram_btn)

        controls.addSpacing(10)

        # Sort Dropdown
        sort_lbl = QLabel("SORT:")
        sort_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px; font-weight: 700; font-family: 'Consolas', monospace;")
        controls.addWidget(sort_lbl)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["CPU Usage (%)", "Memory (MB)", "Process Name (A-Z)", "PID"])
        self.sort_combo.setFixedHeight(34)
        self.sort_combo.setFixedWidth(160)
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        controls.addWidget(self.sort_combo)

        controls.addStretch()

        # Count badge
        self.count_badge = QLabel("0 TASKS")
        self.count_badge.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 11px; font-weight: 600; "
            f"font-family: 'Consolas', monospace; padding: 4px 8px; "
            f"background-color: {COLORS['bg_panel_alt']}; border: 1px solid {COLORS['border_subtle']}; border-radius: 4px;"
        )
        controls.addWidget(self.count_badge)

        layout.addLayout(controls)

        # Main Split Content: Table on Left + Contextual Inspector Panel on Right
        body_row = QHBoxLayout()
        body_row.setSpacing(14)

        # --- Process Table ---
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "PID", "NAME", "CPU %", "RAM %", "MEMORY (MB)", "STATUS", "THREADS"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

        body_row.addWidget(self.table, 1)

        # --- Contextual Process Inspector Panel ---
        self.inspector = QFrame()
        self.inspector.setFixedWidth(290)
        self.inspector.setStyleSheet(card_style())
        insp_layout = QVBoxLayout(self.inspector)
        insp_layout.setContentsMargins(18, 16, 18, 16)
        insp_layout.setSpacing(12)

        insp_header = QHBoxLayout()
        insp_title = QLabel("PROCESS INSPECTOR")
        insp_title.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 10px; font-weight: 700; "
            f"letter-spacing: 0.8px; font-family: 'Consolas', monospace;"
        )
        insp_header.addWidget(insp_title)
        insp_header.addStretch()
        insp_layout.addLayout(insp_header)

        # Process identity block
        self.insp_name_lbl = QLabel("No Selection")
        self.insp_name_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.insp_name_lbl.setStyleSheet(f"color: {COLORS['text_primary']};")
        self.insp_name_lbl.setWordWrap(True)
        insp_layout.addWidget(self.insp_name_lbl)

        self.insp_pid_lbl = QLabel("Select a process to inspect technical metrics.")
        self.insp_pid_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        insp_layout.addWidget(self.insp_pid_lbl)

        # Safety badge
        self.safety_badge = QLabel("")
        self.safety_badge.hide()
        insp_layout.addWidget(self.safety_badge)

        # Inset stats box
        self.stats_box = QFrame()
        self.stats_box.setStyleSheet(panel_alt_style())
        sbl = QVBoxLayout(self.stats_box)
        sbl.setContentsMargins(12, 10, 12, 10)
        sbl.setSpacing(8)

        self.stat_cpu = QLabel("CPU: --")
        self.stat_ram_mb = QLabel("RAM: --")
        self.stat_ram_pct = QLabel("RAM Share: --")
        self.stat_threads = QLabel("Threads: --")
        self.stat_status = QLabel("State: --")

        for lbl in [self.stat_cpu, self.stat_ram_mb, self.stat_ram_pct, self.stat_threads, self.stat_status]:
            lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 11px; font-family: 'Consolas', monospace;")
            sbl.addWidget(lbl)

        insp_layout.addWidget(self.stats_box)

        insp_layout.addStretch()

        # Action button
        self.terminate_btn = QPushButton("End Process")
        self.terminate_btn.setFixedHeight(34)
        self.terminate_btn.setEnabled(False)
        self.terminate_btn.setProperty("danger", "true")
        self.terminate_btn.setStyleSheet(
            f"QPushButton {{ background-color: #261617; color: {COLORS['red']}; "
            f"border: 1px solid #4D2628; border-radius: 6px; font-weight: 600; font-size: 12px; }}"
            f"QPushButton:hover {{ background-color: #381A1D; border-color: {COLORS['red']}; }}"
            f"QPushButton:disabled {{ background-color: transparent; border-color: {COLORS['border_subtle']}; color: {COLORS['text_muted']}; }}"
        )
        self.terminate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.terminate_btn.clicked.connect(self._on_terminate_clicked)
        insp_layout.addWidget(self.terminate_btn)

        body_row.addWidget(self.inspector)

        layout.addLayout(body_row)

    def _set_filter(self, mode: str):
        self._filter_mode = mode
        self.filter_all_btn.setChecked(mode == "all")
        self.filter_cpu_btn.setChecked(mode == "high_cpu")
        self.filter_ram_btn.setChecked(mode == "high_ram")

        for btn in [self.filter_all_btn, self.filter_cpu_btn, self.filter_ram_btn]:
            if btn.isChecked():
                btn.setStyleSheet(
                    f"background-color: {COLORS['bg_card']}; color: {COLORS['accent_lime']}; "
                    f"border: 1px solid {COLORS['border']}; border-radius: 6px; font-weight: 700; font-size: 11px; padding: 4px 12px;"
                )
            else:
                btn.setStyleSheet(
                    f"background-color: {COLORS['bg_panel_alt']}; color: {COLORS['text_secondary']}; "
                    f"border: 1px solid {COLORS['border_subtle']}; border-radius: 6px; font-size: 11px; padding: 4px 12px;"
                )
        self._refresh_table()

    def update_processes(self, processes: list[ProcessInfo]):
        """Receive updated processes snapshot."""
        self._all_processes = processes
        if self.isVisible():
            self._refresh_table()
            self._dirty = False
        else:
            self._dirty = True

    def showEvent(self, event):
        super().showEvent(event)
        if self._dirty:
            self._refresh_table()
            self._dirty = False

    def _on_search(self, text: str):
        self._search_text = text.strip().lower()
        self._refresh_table()

    def _on_sort_changed(self, index: int):
        sort_map = {0: "cpu", 1: "memory", 2: "name", 3: "pid"}
        self._sort_by = sort_map.get(index, "cpu")
        self._refresh_table()

    def _refresh_table(self):
        procs = list(self._all_processes)

        # Text search filter
        if self._search_text:
            procs = [p for p in procs if (
                self._search_text in p.name.lower() or
                self._search_text in str(p.pid)
            )]

        # Mode filter
        if self._filter_mode == "high_cpu":
            procs = [p for p in procs if p.cpu_percent >= 15.0]
        elif self._filter_mode == "high_ram":
            procs = [p for p in procs if p.memory_mb >= 500.0]

        # Sorting
        if self._sort_by == "cpu":
            procs.sort(key=lambda p: (0.0 if p.pid == 0 else p.cpu_percent), reverse=True)
        elif self._sort_by == "memory":
            procs.sort(key=lambda p: p.memory_mb, reverse=True)
        elif self._sort_by == "name":
            procs.sort(key=lambda p: p.name.lower())
        elif self._sort_by == "pid":
            procs.sort(key=lambda p: p.pid)

        self.count_badge.setText(f"{len(procs)} TASKS")

        # Remember selected PID if any
        prev_pid = self._selected_proc.pid if self._selected_proc else None
        selected_row_to_restore = -1

        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        try:
            self.table.setRowCount(len(procs))
            for row, proc in enumerate(procs):
                if prev_pid and proc.pid == prev_pid:
                    selected_row_to_restore = row
                    self._selected_proc = proc

                # PID
                pid_item = self.table.item(row, 0)
                if not pid_item:
                    pid_item = QTableWidgetItem()
                    pid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    pid_item.setFont(QFont("Consolas", 10))
                    pid_item.setForeground(QColor(COLORS['text_muted']))
                    self.table.setItem(row, 0, pid_item)
                pid_item.setText(str(proc.pid))
                pid_item.setData(Qt.ItemDataRole.UserRole, proc)

                # Name
                name_item = self.table.item(row, 1)
                if not name_item:
                    name_item = QTableWidgetItem()
                    name_item.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
                    self.table.setItem(row, 1, name_item)
                name_item.setText(proc.name)

                # CPU %
                cpu_item = self.table.item(row, 2)
                if not cpu_item:
                    cpu_item = QTableWidgetItem()
                    cpu_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    cpu_item.setFont(QFont("Consolas", 10))
                    self.table.setItem(row, 2, cpu_item)
                if proc.pid == 0:
                    cpu_item.setText("Idle")
                    cpu_item.setForeground(QColor(COLORS['text_muted']))
                else:
                    cpu_item.setText(f"{proc.cpu_percent:.1f}%")
                    if proc.cpu_percent >= 50:
                        cpu_item.setForeground(QColor(COLORS['red']))
                    elif proc.cpu_percent >= 20:
                        cpu_item.setForeground(QColor(COLORS['amber']))
                    else:
                        cpu_item.setForeground(QColor(COLORS['text_primary']))

                # RAM %
                ram_pct_item = self.table.item(row, 3)
                if not ram_pct_item:
                    ram_pct_item = QTableWidgetItem()
                    ram_pct_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    ram_pct_item.setFont(QFont("Consolas", 10))
                    self.table.setItem(row, 3, ram_pct_item)
                ram_pct_item.setText(f"{proc.memory_percent:.1f}%")

                # Memory MB
                mem_mb_item = self.table.item(row, 4)
                if not mem_mb_item:
                    mem_mb_item = QTableWidgetItem()
                    mem_mb_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    mem_mb_item.setFont(QFont("Consolas", 10))
                    self.table.setItem(row, 4, mem_mb_item)
                mem_mb_item.setText(f"{proc.memory_mb:.1f} MB")
                if proc.memory_mb >= 1024:
                    mem_mb_item.setForeground(QColor(COLORS['accent_teal']))
                else:
                    mem_mb_item.setForeground(QColor(COLORS['text_primary']))

                # Status
                st_item = self.table.item(row, 5)
                if not st_item:
                    st_item = QTableWidgetItem()
                    st_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    st_item.setFont(QFont("Segoe UI", 9))
                    st_item.setForeground(QColor(COLORS['text_secondary']))
                    self.table.setItem(row, 5, st_item)
                st_item.setText(proc.status.capitalize())

                # Threads
                th_item = self.table.item(row, 6)
                if not th_item:
                    th_item = QTableWidgetItem()
                    th_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    th_item.setFont(QFont("Consolas", 10))
                    self.table.setItem(row, 6, th_item)
                th_item.setText(str(proc.num_threads))
        finally:
            self.table.blockSignals(False)
            self.table.setUpdatesEnabled(True)

        if selected_row_to_restore >= 0:
            self.table.selectRow(selected_row_to_restore)
            self._update_inspector(self._selected_proc)
        elif self._selected_proc is None and len(procs) > 0:
            self.table.selectRow(0)
            self._selected_proc = procs[0]
            self._update_inspector(self._selected_proc)

    def _on_selection_changed(self):
        selected = self.table.selectedItems()
        if not selected:
            self._selected_proc = None
            self.insp_name_lbl.setText("No Selection")
            self.insp_pid_lbl.setText("Select a process to inspect technical metrics.")
            self.safety_badge.hide()
            self.stat_cpu.setText("CPU: --")
            self.stat_ram_mb.setText("RAM: --")
            self.stat_ram_pct.setText("RAM Share: --")
            self.stat_threads.setText("Threads: --")
            self.stat_status.setText("State: --")
            self.terminate_btn.setEnabled(False)
            return

        row = selected[0].row()
        pid_item = self.table.item(row, 0)
        if not pid_item:
            return
        proc: ProcessInfo = pid_item.data(Qt.ItemDataRole.UserRole)
        if proc:
            self._selected_proc = proc
            self._update_inspector(proc)

    def _update_inspector(self, proc: ProcessInfo):
        if not proc:
            return

        self.insp_name_lbl.setText(proc.name)
        self.insp_pid_lbl.setText(f"PID: {proc.pid}  •  Status: {proc.status.upper()}")

        # Protected core system check
        critical_sys_names = {
            'system', 'system idle process', 'smss.exe', 'csrss.exe', 'wininit.exe', 'services.exe',
            'lsass.exe', 'svchost.exe', 'winlogon.exe', 'dwm.exe', 'explorer.exe'
        }
        is_sys = (proc.pid in (0, 4)) or (proc.name.lower() in critical_sys_names) or ('idle' in proc.name.lower())

        self.safety_badge.show()
        if is_sys:
            self.safety_badge.setText("PROTECTED SYSTEM SUBSYSTEM")
            self.safety_badge.setStyleSheet(
                f"color: {COLORS['amber']}; background-color: {COLORS['amber_subtle']}; "
                f"border: 1px solid {COLORS['amber']}40; border-radius: 4px; padding: 2px 6px; "
                f"font-size: 9px; font-weight: 700; font-family: 'Consolas', monospace;"
            )
            self.terminate_btn.setEnabled(False)
            self.terminate_btn.setToolTip("Core operating system process cannot be terminated.")
        else:
            self.safety_badge.setText("USER APPLICATION PROCESS")
            self.safety_badge.setStyleSheet(
                f"color: {COLORS['accent_teal']}; background-color: {COLORS['accent_teal_subtle']}; "
                f"border: 1px solid {COLORS['accent_teal']}40; border-radius: 4px; padding: 2px 6px; "
                f"font-size: 9px; font-weight: 700; font-family: 'Consolas', monospace;"
            )
            self.terminate_btn.setEnabled(True)
            self.terminate_btn.setToolTip("")

        cpu_str = f"{proc.cpu_percent:.1f}%" if proc.pid != 0 else "Idle Thread"
        self.stat_cpu.setText(f"CPU Load:    {cpu_str}")
        self.stat_ram_mb.setText(f"Memory:      {proc.memory_mb:.1f} MB")
        self.stat_ram_pct.setText(f"RAM Share:   {proc.memory_percent:.2f}%")
        self.stat_threads.setText(f"Threads:     {proc.num_threads}")
        self.stat_status.setText(f"State:       {proc.status.capitalize()}")

    def _show_context_menu(self, pos: QPoint):
        item = self.table.itemAt(pos)
        if not item:
            return

        row = item.row()
        pid_item = self.table.item(row, 0)
        proc: ProcessInfo = pid_item.data(Qt.ItemDataRole.UserRole)
        if not proc:
            return

        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ background-color: {COLORS['bg_panel']}; color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 4px; }}"
            f"QMenu::item {{ padding: 6px 18px; border-radius: 4px; font-size: 11px; }}"
            f"QMenu::item:selected {{ background-color: {COLORS['bg_card_hover']}; color: {COLORS['accent_lime']}; }}"
        )

        inspect_act = QAction(f"Inspect '{proc.name}'", self)
        inspect_act.triggered.connect(lambda: self.table.selectRow(row))
        menu.addAction(inspect_act)

        menu.addSeparator()

        term_act = QAction(f"Terminate Process (PID {proc.pid})...", self)
        term_act.triggered.connect(self._on_terminate_clicked)
        menu.addAction(term_act)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _on_terminate_clicked(self):
        """Prompt confirmation modal and execute termination safely."""
        if not self._selected_proc:
            return

        proc = self._selected_proc
        critical_sys_names = {
            'system', 'smss.exe', 'csrss.exe', 'wininit.exe', 'services.exe',
            'lsass.exe', 'svchost.exe', 'winlogon.exe', 'dwm.exe', 'explorer.exe'
        }
        is_sys = proc.name.lower() in critical_sys_names

        modal = ConfirmationModal(
            self,
            title="Terminate Process Confirmation",
            action_name=f"End Process: {proc.name}",
            target_desc=f"{proc.name} (PID: {proc.pid}) — Using {proc.memory_mb:.0f} MB RAM",
            impact_desc="This will immediately kill the target process tree. Any unsaved document state will be lost." + (
                " WARNING: This is an operating system core component; terminating it will cause system instability!" if is_sys else ""
            ),
            is_destructive=True
        )

        if modal.exec() == ConfirmationModal.DialogCode.Accepted:
            success, message = self.monitor.terminate_process(proc.pid, proc.name)
            if success:
                QMessageBox.information(self, "Process Terminated", message)
            else:
                QMessageBox.warning(self, "Termination Error", message)
