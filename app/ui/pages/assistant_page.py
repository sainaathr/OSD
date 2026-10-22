"""
Ask OSD Assistant Page — Interactive conversational assistant view.
Provides instant answers grounded in live metrics, active bottlenecks, and SQLite history.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from app.ui.styles import COLORS, card_style
from app.assistant.chat_engine import AskOSDEngine, AskOSenseEngine


class ChatMessageBubble(QFrame):
    """Chat message bubble."""

    def __init__(self, sender: str, text: str, is_user: bool = False, parent=None):
        super().__init__(parent)
        self.is_user = is_user

        if is_user:
            self.setStyleSheet(
                f"background-color: {COLORS['accent_violet_dim']}; border-radius: 10px; padding: 12px 16px; max-width: 700px;"
            )
        else:
            self.setStyleSheet(
                f"background-color: {COLORS['bg_card']}; border: 1px solid {COLORS['border']}; border-radius: 10px; padding: 14px 18px;"
            )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        sender_lbl = QLabel(f"<b>{sender}</b>")
        sender_lbl.setStyleSheet(f"color: {COLORS['accent_cyan'] if not is_user else 'white'}; font-size: 11px;")
        layout.addWidget(sender_lbl)

        msg_lbl = QLabel(text)
        msg_lbl.setWordWrap(True)
        msg_lbl.setTextFormat(Qt.TextFormat.MarkdownText)
        msg_lbl.setStyleSheet("color: #e8eaf0; font-size: 12px; line-height: 1.5;")
        layout.addWidget(msg_lbl)


class AssistantPage(QWidget):
    """Conversational performance assistant interface."""

    def __init__(self, engine: AskOSDEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # Header
        title_box = QVBoxLayout()
        title = QLabel("💬 Ask OSD Assistant")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        title_box.addWidget(title)

        desc = QLabel(
            "Ask questions about computer responsiveness, resource hogs, recent changes, "
            "and recovery effectiveness. Responses are computed locally from real telemetry."
        )
        desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        title_box.addWidget(desc)
        main_layout.addLayout(title_box)

        # Quick Question Buttons
        quick_box = QHBoxLayout()
        quick_box.setSpacing(8)

        prompts = [
            "Why is my PC slow?",
            "Which process uses the most memory?",
            "What has changed recently?",
            "Which recommendation is safest?",
            "Is the memory usage increasing?",
            "Did the last recovery action improve performance?",
        ]
        for p in prompts[:4]:
            btn = QPushButton(p)
            btn.setFixedHeight(28)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {COLORS['bg_card']}; color: {COLORS['accent_cyan']}; "
                f"border: 1px solid {COLORS['border']}; border-radius: 14px; padding: 2px 12px; font-size: 11px; }}"
                f"QPushButton:hover {{ background-color: {COLORS['bg_card_hover']}; }}"
            )
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, text=p: self._send_prompt(text))
            quick_box.addWidget(btn)
        quick_box.addStretch()
        main_layout.addLayout(quick_box)

        # Chat Messages Scroll Area
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet("QScrollArea { border: 1px solid #2a3a5c; border-radius: 8px; background-color: #16213e; }")

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(16, 16, 16, 16)
        self.chat_layout.setSpacing(12)
        self.chat_layout.addStretch()

        self.chat_scroll.setWidget(self.chat_container)
        main_layout.addWidget(self.chat_scroll, 1)

        # Input Bar
        input_bar = QHBoxLayout()
        input_bar.setSpacing(8)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask a question about your system performance...")
        self.input_field.setFixedHeight(40)
        self.input_field.returnPressed.connect(self._on_send)
        input_bar.addWidget(self.input_field, 1)

        send_btn = QPushButton("Send")
        send_btn.setFixedHeight(40)
        send_btn.setFixedWidth(80)
        send_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['accent_violet']}; color: white; border-radius: 6px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: {COLORS['accent_violet_dim']}; }}"
        )
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.clicked.connect(self._on_send)
        input_bar.addWidget(send_btn)

        main_layout.addLayout(input_bar)

        # Initial Welcome Message
        self._add_message("OSD Assistant", (
            "Hello! I am your **OSD Assistant**. I can inspect your live system hardware metrics, "
            "explain probable causes for sluggish performance, identify resource-heavy applications, "
            "and verify the results of recovery actions.\n\n"
            "Try clicking one of the suggested prompts above or type your question below."
        ), is_user=False)

    def _send_prompt(self, text: str):
        self.input_field.setText(text)
        self._on_send()

    def _on_send(self):
        text = self.input_field.text().strip()
        if not text:
            return

        self.input_field.clear()
        self._add_message("You", text, is_user=True)

        # Generate answer from engine
        answer = self.engine.ask(text)
        QTimer.singleShot(150, lambda: self._add_message("OSD Assistant", answer, is_user=False))

    def _add_message(self, sender: str, text: str, is_user: bool = False):
        bubble = ChatMessageBubble(sender, text, is_user=is_user)
        # Insert before stretch
        count = self.chat_layout.count()
        self.chat_layout.insertWidget(count - 1, bubble)

        # Scroll to bottom
        QTimer.singleShot(50, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))
