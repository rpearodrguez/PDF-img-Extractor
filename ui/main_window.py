from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QPushButton, QButtonGroup, QLabel,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.panels.pdf_panel import PdfPanel


_SIDEBAR_STYLE = """
QWidget#Sidebar {
    background-color: #1e1e2e;
    border-right: 1px solid #2a2a3e;
}
QPushButton {
    background: transparent;
    color: #9999bb;
    border: none;
    padding: 10px 8px;
    text-align: left;
    font-size: 13px;
    border-radius: 6px;
    margin: 2px 8px;
}
QPushButton:checked {
    background: #3b82f6;
    color: white;
}
QPushButton:hover:!checked:enabled {
    background: #2a2a3e;
    color: #ddddee;
}
QPushButton:disabled {
    color: #44445a;
}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Media Center")
        self.setMinimumSize(860, 640)
        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stack = QStackedWidget()
        self._stack.addWidget(PdfPanel())

        layout.addWidget(self._make_sidebar())
        layout.addWidget(self._stack, 1)

    def _make_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(140)
        sidebar.setStyleSheet(_SIDEBAR_STYLE)

        vbox = QVBoxLayout(sidebar)
        vbox.setContentsMargins(0, 16, 0, 16)
        vbox.setSpacing(2)

        title = QLabel("Media\nCenter")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet("color: #eeeeff; padding: 10px 0 22px 0;")
        vbox.addWidget(title)

        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)

        modules = [
            ("PDF",    0, True),
            ("Imagen", 1, False),
            ("Audio",  2, False),
            ("Video",  3, False),
        ]

        for label, idx, enabled in modules:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setEnabled(enabled)
            if idx == 0:
                btn.setChecked(True)
            self._btn_group.addButton(btn, idx)
            vbox.addWidget(btn)

        self._btn_group.idClicked.connect(self._stack.setCurrentIndex)

        vbox.addStretch()
        return sidebar
