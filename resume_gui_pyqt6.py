import sys
import traceback
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

# Change this import to match your actual file name.
# Example: if your main logic file is resume_customizer.py, this is correct.
from Resume_Customizer import generate_resume_from_url


DEFAULT_MODEL = "gemma3:12b"


class ResumeWorker(QObject):
    log_message = pyqtSignal(str)
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(
        self,
        job_url: str,
        master_resume_path: str,
        output_filename: str,
        model: str,
    ):
        super().__init__()
        self.job_url = job_url
        self.master_resume_path = master_resume_path
        self.output_filename = output_filename
        self.model = model

    def run(self) -> None:
        try:
            output_path = generate_resume_from_url(
                job_url=self.job_url,
                master_resume_path=self.master_resume_path,
                output_filename=self.output_filename,
                model=self.model,
                log_callback=self.log_message.emit,
            )

            self.finished.emit(str(output_path))

        except Exception:
            self.failed.emit(traceback.format_exc())


class ResumeCustomizerWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.thread = None
        self.worker = None

        self.setWindowTitle("AI Resume Customizer")
        self.resize(950, 700)

        self.build_ui()

    def build_ui(self) -> None:
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        title_label = QLabel("AI Resume Customizer")
        title_label.setStyleSheet(
            "font-size: 24px; font-weight: bold;"
        )
        main_layout.addWidget(title_label)

        url_label = QLabel("Job Posting URL:")
        main_layout.addWidget(url_label)

        self.url_input = QPlainTextEdit()
        self.url_input.setPlaceholderText(
            "Paste the specific job posting URL here..."
        )
        self.url_input.setFixedHeight(90)
        main_layout.addWidget(self.url_input)

        resume_layout = QHBoxLayout()

        resume_label = QLabel("Master Resume PDF:")
        self.resume_path_input = QLineEdit()
        self.resume_path_input.setText("Max_Gao_Master_Resume.pdf")

        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_master_resume)

        resume_layout.addWidget(resume_label)
        resume_layout.addWidget(self.resume_path_input)
        resume_layout.addWidget(browse_button)

        main_layout.addLayout(resume_layout)

        settings_layout = QHBoxLayout()

        output_label = QLabel("Output PDF:")
        self.output_input = QLineEdit()
        self.output_input.setText("customized_resume.pdf")

        model_label = QLabel("Model:")
        self.model_input = QLineEdit()
        self.model_input.setText(DEFAULT_MODEL)

        settings_layout.addWidget(output_label)
        settings_layout.addWidget(self.output_input)
        settings_layout.addWidget(model_label)
        settings_layout.addWidget(self.model_input)

        main_layout.addLayout(settings_layout)

        self.generate_button = QPushButton("Generate Resume")
        self.generate_button.setFixedHeight(45)
        self.generate_button.setStyleSheet(
            "font-size: 16px; font-weight: bold;"
        )
        self.generate_button.clicked.connect(self.start_generation)

        main_layout.addWidget(self.generate_button)

        log_label = QLabel("Log:")
        main_layout.addWidget(log_label)

        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText(
            "Progress and errors will appear here..."
        )

        main_layout.addWidget(self.log_box)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def browse_master_resume(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Master Resume PDF",
            "",
            "PDF Files (*.pdf);;All Files (*)",
        )

        if file_path:
            self.resume_path_input.setText(file_path)

    def append_log(self, message: str) -> None:
        self.log_box.appendPlainText(str(message))

    def start_generation(self) -> None:
        job_url = self.url_input.toPlainText().strip()
        master_resume_path = self.resume_path_input.text().strip()
        output_filename = self.output_input.text().strip()
        model = self.model_input.text().strip()

        if not job_url:
            QMessageBox.warning(
                self,
                "Missing Job URL",
                "Please paste a job posting URL.",
            )
            return

        if not master_resume_path:
            QMessageBox.warning(
                self,
                "Missing Resume PDF",
                "Please select your master resume PDF.",
            )
            return

        if not Path(master_resume_path).exists():
            QMessageBox.warning(
                self,
                "Resume File Not Found",
                f"Could not find this file:\n{master_resume_path}",
            )
            return

        if not output_filename:
            QMessageBox.warning(
                self,
                "Missing Output Filename",
                "Please enter an output PDF filename.",
            )
            return

        if not output_filename.lower().endswith(".pdf"):
            output_filename += ".pdf"
            self.output_input.setText(output_filename)

        if not model:
            QMessageBox.warning(
                self,
                "Missing Model",
                "Please enter an Ollama model name.",
            )
            return

        self.log_box.clear()
        self.generate_button.setEnabled(False)
        self.generate_button.setText("Generating...")

        self.thread = QThread()

        self.worker = ResumeWorker(
            job_url=job_url,
            master_resume_path=master_resume_path,
            output_filename=output_filename,
            model=model,
        )

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)

        self.worker.log_message.connect(self.append_log)
        self.worker.finished.connect(self.on_generation_finished)
        self.worker.failed.connect(self.on_generation_failed)

        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)

        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.failed.connect(self.worker.deleteLater)

        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def on_generation_finished(self, output_path: str) -> None:
        self.generate_button.setEnabled(True)
        self.generate_button.setText("Generate Resume")

        self.append_log("")
        self.append_log("DONE")
        self.append_log(f"Output PDF: {output_path}")

        QMessageBox.information(
            self,
            "Success",
            f"Resume PDF created successfully:\n{output_path}",
        )

    def on_generation_failed(self, error_text: str) -> None:
        self.generate_button.setEnabled(True)
        self.generate_button.setText("Generate Resume")

        self.append_log("")
        self.append_log("ERROR:")
        self.append_log(error_text)

        QMessageBox.critical(
            self,
            "Resume Generation Failed",
            "Resume generation failed. Check the log box for details.",
        )


def main() -> None:
    app = QApplication(sys.argv)
    window = ResumeCustomizerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()