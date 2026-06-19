from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QFont, QTextCursor


class LogWidget(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 9))
        self.setMinimumHeight(160)

    def append_message(self, message: str) -> None:
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.insertPlainText(message + "\n")
        self.ensureCursorVisible()

    def clear_log(self) -> None:
        self.clear()
