import os
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

import extract
import parse
import query
import report
import verify


# Upload widget
class MainWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.file_path = ""

        # Vars
        self.settings = {
            "api": {"local": True, "sem": True, "cross": True},
            "report": {"gui": True, "pdf": True, "html": True, "csv": True},
        }

        # Widgets
        self.filename_lbl = QLabel("Selected: None")
        self.select_btn = QPushButton("Select File")
        self.paste_btn = QPushButton("Paste References")
        self.status_lbl = QLabel("")
        self.process_btn = QPushButton("Process File")
        self.settings_btn = QPushButton("Settings")
        self.help_btn = QPushButton("Open Help")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)

        # Setting widget font
        font = QFont("Sans-Serif", 16)
        for w in (
            self.filename_lbl,
            self.select_btn,
            self.paste_btn,
            self.status_lbl,
            self.process_btn,
            self.settings_btn,
            self.help_btn,
        ):
            w.setFont(font)

        self.progress.setValue(0)

        # Setting up layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.filename_lbl)
        layout.addWidget(self.select_btn)
        layout.addWidget(self.paste_btn)
        layout.addWidget(self.status_lbl)
        layout.addWidget(self.process_btn)
        layout.addWidget(self.settings_btn)
        layout.addWidget(self.help_btn)
        layout.addWidget(self.progress)

        # Connecting button and methods
        self.select_btn.clicked.connect(self.select_file)
        self.paste_btn.clicked.connect(self.paste_refs)
        self.process_btn.clicked.connect(self.check_file)
        self.settings_btn.clicked.connect(self.open_settings_dialog)
        self.help_btn.clicked.connect(self.open_help_dialog)

    # Setup worker thread and connect it to Runner class
    def process_refs(self, raw_refs):
        # Setup
        self.worker_thread = QThread()
        self.runner = Runner(self.settings, raw_refs, self.file_path)
        self.runner.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.runner.run_process)
        # Monitor widget updates
        self.runner.progress_updated.connect(self.progress.setValue)
        self.runner.status_updated.connect(self.status_lbl.setText)
        # Runs after worker thread finishes
        self.runner.finished.connect(self.gen_report)
        self.runner.finished.connect(self.worker_thread.quit)
        self.runner.finished.connect(self.runner.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def gen_report(self, refs, targets, score, file_name):
        self.toggle_buttons(True)
        msg = report.create_report(
            refs, targets, score, self.settings.get("report"), file_name
        )
        if msg:
            ReportDialog(msg, self).exec()

    # Open file dialog
    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select a File",
            os.path.expanduser("~"),
            "PDF files (*.pdf);;All files (*.*)",
        )
        if path:
            self.file_path = path
            self.filename_lbl.setText(f"Selected: {Path(path).name}")

    # Extract refs from a pdf and check program can run
    def check_file(self):
        self.progress.setValue(0)
        if not self.check_path() or not self.check_settings():
            return

        raw_refs = self.extraction()
        if not self.check_refs(raw_refs):
            return

        self.toggle_buttons(False)
        self.process_refs(raw_refs)

    def extraction(self):
        self.reset_progress()
        raw = extract.extract_all(self.file_path)
        msg = f"{len(raw)} references found from {Path(self.file_path).name}"
        return self.open_ref_edit_dialog(msg, "\n\n".join(raw))

    # Open text edit dialog for manually entering references
    def paste_refs(self):
        self.reset_progress()
        raw_refs = self.open_ref_edit_dialog("Paste your references below", "")
        if not self.check_settings() or not self.check_refs(raw_refs):
            return

        self.toggle_buttons(False)
        self.process_refs(raw_refs)

    # Prompts user with dialog box for ammending references
    def open_ref_edit_dialog(self, msg, initial_text):
        dialog = ReferenceEditorDialog(
            "Reference Editor",
            msg,
            initial_text,
            self,
        )
        # Confirm
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return [line for line in dialog.get_text().splitlines() if line]

        # Cancel
        else:
            return

    def open_settings_dialog(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.settings = dialog.get_results()

    def open_help_dialog(self):
        dialog = HelpDialog(self)
        dialog.exec()

    # Helper method for checking if a valid file is uploaded
    def check_path(self):
        if not self.file_path:
            QMessageBox.warning(self, "Warning", "No file selected.")
            return False
        elif Path(self.file_path).suffix != ".pdf":
            QMessageBox.warning(self, "Warning", "Invalid file type selected.")
            return False

        return True

    # Helper method for checking if atleast one API service is on
    def check_settings(self):
        if True not in self.settings.get("api", {}).values():
            QMessageBox.warning(self, "Warning", "No API services are enabled.")
            return False

        if True not in self.settings.get("report", {}).values():
            QMessageBox.warning(self, "Warning", "No report type is enabled.")
            return False

        return True

    # Helper method for checking if any references exist
    def check_refs(self, refs):
        if not refs or any(not ref.strip() for ref in refs):
            msg = "No valid references found"
            self.status_lbl.setText(msg)
            QMessageBox.warning(self, "Warning", msg + ".")
            return False

        return True

    def reset_progress(self):
        self.status_lbl.setText("Extracting...")
        self.progress.setValue(0)

    def toggle_buttons(self, b):
        self.select_btn.setEnabled(b)
        self.paste_btn.setEnabled(b)
        self.process_btn.setEnabled(b)
        self.settings_btn.setEnabled(b)


# Settings dialog box
class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(400, 300)

        # Widgets
        self.local_check = QCheckBox("Local Database")
        self.sem_check = QCheckBox("Semantic Scholar")
        self.cross_check = QCheckBox("Crossref")
        self.gui_check = QCheckBox("GUI Report")
        self.pdf_check = QCheckBox("PDF Report")
        self.html_check = QCheckBox("HTML Report")
        self.csv_check = QCheckBox("CSV Report")
        self.btn = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.btn.accepted.connect(self.accept)
        self.btn.rejected.connect(self.reject)

        # Set checkbox state
        self.local_check.setChecked(settings.get("api")["local"])
        self.sem_check.setChecked(settings.get("api")["sem"])
        self.cross_check.setChecked(settings.get("api")["cross"])
        self.gui_check.setChecked(settings.get("report")["gui"])
        self.pdf_check.setChecked(settings.get("report")["pdf"])
        self.html_check.setChecked(settings.get("report")["html"])
        self.csv_check.setChecked(settings.get("report")["csv"])

        # Layout
        main_layout = QVBoxLayout(self)
        h_layout = QHBoxLayout()

        l_group = QGroupBox("API Settings")
        l_layout = QVBoxLayout()
        l_layout.addWidget(self.local_check)
        l_layout.addWidget(self.sem_check)
        l_layout.addWidget(self.cross_check)
        l_group.setLayout(l_layout)

        r_group = QGroupBox("Report Settings")
        r_layout = QVBoxLayout()
        r_layout.addWidget(self.gui_check)
        r_layout.addWidget(self.pdf_check)
        r_layout.addWidget(self.html_check)
        r_layout.addWidget(self.csv_check)
        r_group.setLayout(r_layout)

        h_layout.addWidget(l_group)
        h_layout.addWidget(r_group)

        main_layout.addLayout(h_layout)
        main_layout.addWidget(self.btn)

    def get_results(self):
        return {
            "api": {
                "local": self.local_check.isChecked(),
                "sem": self.sem_check.isChecked(),
                "cross": self.cross_check.isChecked(),
            },
            "report": {
                "gui": self.gui_check.isChecked(),
                "pdf": self.pdf_check.isChecked(),
                "html": self.html_check.isChecked(),
                "csv": self.csv_check.isChecked(),
            },
        }


# Reference editor dialog box
class ReferenceEditorDialog(QDialog):
    def __init__(self, title, msg, raw, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(800, 600)

        # Widgets
        self.found = QLabel(msg + ", please verify.")
        self.instr = QLabel("Every reference should be seperated by a new line:")
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlainText(raw)
        self.btn = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.btn.accepted.connect(self.accept)
        self.btn.rejected.connect(self.reject)

        # Setting widget font
        font = QFont("Sans-Serif", 12)
        for w in (self.found, self.instr):
            w.setFont(font)

        # Layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.found)
        layout.addWidget(self.instr)
        layout.addWidget(self.text_edit)
        layout.addWidget(self.btn)

    def get_text(self):
        return self.text_edit.toPlainText()


# Help dialog box
class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Help")
        self.setMinimumSize(800, 600)

        # Widgets
        self.help = QTextBrowser()
        self.btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)

        help_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "assets", "help.html"
        )

        with open(help_path, "r", encoding="utf-8") as f:
            self.help.setHtml(f.read())

        self.btn.accepted.connect(self.accept)

        # Layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.help)
        layout.addWidget(self.btn)


class ReportDialog(QDialog):
    def __init__(self, msg, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Report")
        self.setMinimumSize(800, 600)

        # Widgets
        self.report = QTextBrowser()
        self.btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)

        self.report.setHtml(msg)

        self.btn.accepted.connect(self.accept)

        # Layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.report)
        layout.addWidget(self.btn)


# Main window
class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Reference Checker")
        self.resize(500, 400)
        self.setMinimumSize(500, 400)

        container = QWidget()
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)

        title = QLabel("Upload Document")
        title.setFont(QFont("Sans-Serif", 24))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.main = MainWidget()
        layout.addWidget(title)
        layout.addWidget(self.main, stretch=1)


# Core functionality runs in a different thread as to not interfere with the interface
class Runner(QObject):
    # Signals to send back to interface
    finished = Signal(list, list, list, object)
    status_updated = Signal(str)
    progress_updated = Signal(int)

    def __init__(self, settings, raw_refs, file_path):
        super().__init__()
        self.settings = settings
        self.raw_refs = raw_refs
        self.file_path = file_path

    # Runner for background functionality
    def run_process(self):
        refs = self.parsing(self.raw_refs)
        targets = self.querying(refs)
        score = self.comparing(refs, targets)
        file_name = Path(self.file_path).name if self.file_path else None
        self.progress_updated.emit(100)
        self.status_updated.emit("Reports saved to ~/Documents/refreport/")
        self.finished.emit(refs, targets, score, file_name)

    def parsing(self, refs):
        self.progress_updated.emit(5)
        self.status_updated.emit("Parsing...")
        return parse.parse_all_refs(refs)

    def querying(self, refs):
        self.status_updated.emit("Querying...")
        return query.query_all(
            refs, self.settings.get("api"), callback=self.progress_updated.emit
        )

    def comparing(self, refs, targets):
        self.progress_updated.emit(9522)
        self.status_updated.emit("Verifying...")
        return verify.verify_all(refs, targets, self.settings.get("api"))


def run():
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())
