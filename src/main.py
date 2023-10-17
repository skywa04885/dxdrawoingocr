import logging
import sys
import time
from pathlib import Path
from PySide6 import QtCore, QtWidgets, QtGui
from stuff import Converter, ConverterUpdateEvent, ConverterLogEvent
from time import time


class MyStatusWindow(QtWidgets.QDialog):
    def __init__(self, converter: Converter) -> None:
        super().__init__()

        # Creates the converter.
        self.converter = converter
        self.converter.status_signal.connect(self.on_status)
        self.converter.log_signal.connect(self.on_log)
        self.converter.start()

        # Sets the window title.
        self.setWindowTitle('Processing')

        # Creates the basic grid.
        self.grid = QtWidgets.QGridLayout()

        # Creates the progress bar.
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)
        self.progress_bar.setFixedWidth(600)
        self.grid.addWidget(self.progress_bar)

        # Creates the elapsed time label.
        self.elapsed_time_label = QtWidgets.QLabel()
        self.elapsed_time_label.setText('Verlopen tijd: -')
        self.grid.addWidget(self.elapsed_time_label, 2, 0)

        # Creates the button box.
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.button_box.accepted.connect(self.accept)
        self.button_box.setDisabled(True)
        self.grid.addWidget(self.button_box, 3, 0)

        # Creates the list widget for the log.
        self.log_list = QtWidgets.QListWidget()
        self.grid.addWidget(self.log_list, 1, 0)

        # Sets the layout.
        self.setLayout(self.grid)

        # Sets the start time.
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.on_timer_timeout)
        self.timer.setInterval(50)
        self.timer.start()

        # Sets the start time.
        self.start_time = time()

    @QtCore.Slot()
    def on_timer_timeout(self):
        current_time = time()
        elapsed_time = int(round((current_time - self.start_time) * 100.0) * 10.0)
        self.elapsed_time_label.setText(f'Verlopen tijd: {elapsed_time}ms')

    @QtCore.Slot()
    def on_log(self, log: ConverterLogEvent) -> None:
        # Adds the message to the log and scrolls to the bottom.
        self.log_list.addItem(str(log))
        self.log_list.scrollToBottom()

    @QtCore.Slot()
    def on_status(self, status: ConverterUpdateEvent) -> None:
        # Enables the buttons if finished.
        if status.progress == 100:
            self.button_box.setDisabled(False)
            self.timer.stop()

        # Updates the progress bar
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setFormat(status.message if len(status.message) < 60 else f'{status.message[:60]}...')
        self.progress_bar.setValue(status.progress)


class MyWindowWidget(QtWidgets.QWidget):
    def __init__(self, settings: QtCore.QSettings) -> None:
        super().__init__()

        self.settings = settings

        # Gets the paths where the files will be located.

        self.default_drawings_path = Path.home() / 'Werktekeningen'
        self.in_dir_path = Path(str(self.settings.value('folders/in', str(self.default_drawings_path / 'Import'))))
        self.out_dir_path = Path(str(self.settings.value('folders/out', str(self.default_drawings_path / 'Archief'))))
        self.fail_dir_path = Path(str(self.settings.value('folders/fail', str(self.default_drawings_path / 'Handmatig'))))
        self.finished_dir_path = Path(str(self.settings.value('folders/finished', str(self.default_drawings_path / 'Verwerkt'))))
        self.temp_dir_path = Path(str(self.settings.value('folders/temp', str(self.default_drawings_path / 'Temp'))))

        # Ensures the paths where the files will be located exist.

        self.in_dir_path.mkdir(parents=True, exist_ok=True)
        self.out_dir_path.mkdir(parents=True, exist_ok=True)
        self.fail_dir_path.mkdir(parents=True, exist_ok=True)
        self.finished_dir_path.mkdir(parents=True, exist_ok=True)
        self.temp_dir_path.mkdir(parents=True, exist_ok=True)

        # Creates the grid.

        self.grid = QtWidgets.QGridLayout(self)

        # Title

        self.title_label = QtWidgets.QLabel()
        self.title_label.setText('DX Drawing OCR')
        self.grid.addWidget(self.title_label, 0, 0)

        # Group box

        self.dirs_group_box = QtWidgets.QGroupBox()
        self.dirs_group_box.setTitle('Mappen')

        # Directories layout

        self.dirs_layout = QtWidgets.QGridLayout()
        self.dirs_group_box.setLayout(self.dirs_layout)
        self.grid.addWidget(self.dirs_group_box, 1, 0)

        # Input directory

        self.select_in_dir_btn = QtWidgets.QPushButton('Kies nieuwe map')
        self.select_in_dir_btn.clicked.connect(self.on_select_in_dir_btn_clicked)
        self.dirs_layout.addWidget(self.select_in_dir_btn, 0, 0)

        self.view_in_dir_btn = QtWidgets.QPushButton('Bekijk map')
        self.view_in_dir_btn.clicked.connect(self.on_view_in_dir_btn_clicked)
        self.dirs_layout.addWidget(self.view_in_dir_btn, 0, 2)

        self.in_dir_txt_ln_edit = QtWidgets.QLineEdit()
        self.in_dir_txt_ln_edit.setReadOnly(True)
        self.in_dir_txt_ln_edit.setFixedWidth(300)
        self.in_dir_txt_ln_edit.setText(str(self.in_dir_path))
        self.dirs_layout.addWidget(self.in_dir_txt_ln_edit, 0, 1)

        # Output directory

        self.select_out_dir_btn = QtWidgets.QPushButton('Kies nieuwe map')
        self.select_out_dir_btn.clicked.connect(self.on_select_out_dir_btn_clicked)
        self.dirs_layout.addWidget(self.select_out_dir_btn, 1, 0)

        self.view_out_dir_btn = QtWidgets.QPushButton('Bekijk map')
        self.view_out_dir_btn.clicked.connect(self.on_view_out_dir_btn_clicked)
        self.dirs_layout.addWidget(self.view_out_dir_btn, 1, 2)

        self.out_dir_txt_ln_edit = QtWidgets.QLineEdit()
        self.out_dir_txt_ln_edit.setReadOnly(True)
        self.out_dir_txt_ln_edit.setFixedWidth(300)
        self.out_dir_txt_ln_edit.setText(str(self.out_dir_path))
        self.dirs_layout.addWidget(self.out_dir_txt_ln_edit, 1, 1)

        # Failure directory

        self.select_fail_dir_btn = QtWidgets.QPushButton('Kies nieuwe map')
        self.select_fail_dir_btn.clicked.connect(self.on_select_fail_dir_btn_clicked)
        self.dirs_layout.addWidget(self.select_fail_dir_btn, 2, 0)

        self.view_fail_dir_btn = QtWidgets.QPushButton('Bekijk map')
        self.view_fail_dir_btn.clicked.connect(self.on_view_fail_dir_btn_clicked)
        self.dirs_layout.addWidget(self.view_fail_dir_btn, 2, 2)

        self.fail_dir_txt_ln_edit = QtWidgets.QLineEdit()
        self.fail_dir_txt_ln_edit.setReadOnly(True)
        self.fail_dir_txt_ln_edit.setFixedWidth(300)
        self.fail_dir_txt_ln_edit.setText(str(self.fail_dir_path))
        self.dirs_layout.addWidget(self.fail_dir_txt_ln_edit, 2, 1)

        # Finished directory

        self.select_finished_dir_btn = QtWidgets.QPushButton('Kies nieuwe map')
        self.select_finished_dir_btn.clicked.connect(self.on_select_finished_dir_btn_clicked)
        self.dirs_layout.addWidget(self.select_finished_dir_btn, 3, 0)

        self.view_finished_dir_btn = QtWidgets.QPushButton('Bekijk map')
        self.view_finished_dir_btn.clicked.connect(self.on_view_finished_dir_btn_clicked)
        self.dirs_layout.addWidget(self.view_finished_dir_btn, 3, 3)

        self.finished_dir_txt_ln_edit = QtWidgets.QLineEdit()
        self.finished_dir_txt_ln_edit.setReadOnly(True)
        self.finished_dir_txt_ln_edit.setFixedWidth(300)
        self.finished_dir_txt_ln_edit.setText(str(self.finished_dir_path))
        self.dirs_layout.addWidget(self.finished_dir_txt_ln_edit, 3, 1)

        self.clear_finished_dir_btn = QtWidgets.QPushButton('Wis')
        self.clear_finished_dir_btn.clicked.connect(self.on_clear_finished_folder_btn_clicked)
        self.dirs_layout.addWidget(self.clear_finished_dir_btn, 3, 2)

        # Process button

        self.process_btn = QtWidgets.QPushButton('Verwerk')
        self.process_btn.clicked.connect(self.on_process_btn_clicked)
        self.grid.addWidget(self.process_btn, 2, 0)

    @QtCore.Slot()
    def on_view_out_dir_btn_clicked(self) -> None:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(self.out_dir_path)))

    @QtCore.Slot()
    def on_view_in_dir_btn_clicked(self) -> None:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(self.in_dir_path)))

    @QtCore.Slot()
    def on_view_fail_dir_btn_clicked(self) -> None:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(self.fail_dir_path)))

    @QtCore.Slot()
    def on_view_finished_dir_btn_clicked(self) -> None:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(self.finished_dir_path)))

    @QtCore.Slot()
    def on_process_btn_clicked(self) -> None:
        converter = Converter.build(self.in_dir_path, self.out_dir_path, self.fail_dir_path, self.temp_dir_path,
                                    self.finished_dir_path)
        my_status_window = MyStatusWindow(converter)
        my_status_window.exec()

    @QtCore.Slot()
    def on_select_in_dir_btn_clicked(self) -> None:
        new_in_dir_path = QtWidgets.QFileDialog.getExistingDirectory(self, dir=str(self.in_dir_path))
        if len(new_in_dir_path) == 0:
            return

        self.in_dir_path = Path(new_in_dir_path)
        self.in_dir_txt_ln_edit.setText(str(self.in_dir_path))
        self.settings.setValue('folders/in', str(new_in_dir_path))

    @QtCore.Slot()
    def on_select_out_dir_btn_clicked(self) -> None:
        new_out_dir_path = QtWidgets.QFileDialog.getExistingDirectory(self, dir=str(self.out_dir_path))
        if len(new_out_dir_path) == 0:
            return

        self.out_dir_path = Path(new_out_dir_path)
        self.out_dir_txt_ln_edit.setText(str(self.out_dir_path))
        self.settings.setValue('folders/out', str(new_out_dir_path))

    @QtCore.Slot()
    def on_select_fail_dir_btn_clicked(self) -> None:
        new_fail_dir_path = QtWidgets.QFileDialog.getExistingDirectory(self, dir=str(self.fail_dir_path))
        if len(new_fail_dir_path) == 0:
            return

        self.fail_dir_path = Path(new_fail_dir_path)
        self.fail_dir_txt_ln_edit.setText(str(self.fail_dir_path))
        self.settings.setValue('folders/fail', str(new_fail_dir_path))

    @QtCore.Slot()
    def on_select_finished_dir_btn_clicked(self) -> None:
        new_finished_dir_path = QtWidgets.QFileDialog.getExistingDirectory(self, dir=str(self.finished_dir_path))
        if len(new_finished_dir_path) == 0:
            return

        self.finished_dir_path = Path(new_finished_dir_path)
        self.finished_dir_txt_ln_edit.setText(str(self.finished_dir_path))
        self.settings.setValue('folders/finished', str(new_finished_dir_path))

    @QtCore.Slot()
    def on_clear_finished_folder_btn_clicked(self) -> None:
        for finished_file_path in self.finished_dir_path.iterdir():
            finished_file_path.unlink()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    settings = QtCore.QSettings("DuflexMechatronics", "DrawingOCR")

    app = QtWidgets.QApplication()

    my_window_widget = MyWindowWidget(settings)
    my_window_widget.show()

    sys.exit(app.exec())
