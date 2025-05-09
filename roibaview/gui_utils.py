from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox,
    QDialogButtonBox, QFileDialog, QHBoxLayout, QCheckBox, QWidget, QColorDialog
)
from PyQt6.QtGui import QIntValidator, QDoubleValidator
import os


class DynamicInputDialog(QDialog):
    def __init__(self, title='Input Dialog', fields=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.fields = fields or {}
        self.inputs = {}  # key -> (widget, type_str)

        layout = QVBoxLayout()

        for label, (default, type_str) in self.fields.items():
            if type_str == 'bool':
                # Checkbox for boolean input
                checkbox = QCheckBox(label)
                checkbox.setChecked(bool(default))
                layout.addWidget(checkbox)
                self.inputs[label] = (checkbox, type_str)

            elif type_str in ('file', 'dir'):
                # File or directory picker
                layout.addWidget(QLabel(label))
                container = QHBoxLayout()
                line_edit = QLineEdit(str(default))
                button = QPushButton("Browse...")
                container.addWidget(line_edit)
                container.addWidget(button)
                layout.addLayout(container)

                def open_dialog(_, le=line_edit, t=type_str):
                    if t == 'file':
                        file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
                        if file_path:
                            le.setText(file_path)
                    else:
                        dir_path, _ = QFileDialog.getSaveFileName(self, "Select Directory", filter="CSV Files (*.csv)")
                        if dir_path:
                            if not dir_path.endswith('.csv'):
                                dir_path += '.csv'
                            le.setText(dir_path)

                button.clicked.connect(open_dialog)
                self.inputs[label] = (line_edit, type_str)

            else:
                # Regular text/numeric input
                layout.addWidget(QLabel(label))
                line_edit = QLineEdit(str(default))
                if type_str == 'int':
                    line_edit.setValidator(QIntValidator())
                elif type_str == 'float':
                    line_edit.setValidator(QDoubleValidator())
                layout.addWidget(line_edit)
                self.inputs[label] = (line_edit, type_str)

        self.add_ok_cancel_buttons(layout)
        self.setLayout(layout)

    def add_ok_cancel_buttons(self, layout):
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        buttonBox = QDialogButtonBox(QBtn)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)

    def get_inputs(self):
        result = {}
        for label, (widget, type_str) in self.inputs.items():
            if type_str == 'bool':
                result[label] = widget.isChecked()
            else:
                value = widget.text()
                try:
                    if type_str == 'int':
                        result[label] = int(value)
                    elif type_str == 'float':
                        result[label] = float(value)
                    else:
                        result[label] = value
                except ValueError:
                    result[label] = None
        return result


class SimpleInputDialog(QDialog):
    """
    That's how you call it:
        dialog = SimpleInputDialog(title='Settings', text='Please enter some stuff: ')
        if dialog.exec() == QDialog.DialogCode.Accepted:
            received = dialog.get_input()
        else:
            return None
    """
    def __init__(self, title, text, default_value=0,  parent=None):
        super().__init__(parent)
        self.title = title
        self.text = text
        self.default_value = default_value

        self.setWindowTitle(self.title)
        layout = QVBoxLayout()

        # Create input fields
        self.user_input = QLineEdit()
        self.user_input.setText(str(self.default_value))

        # Add labels
        layout.addWidget(QLabel(self.text))
        layout.addWidget(self.user_input)

        # Add OK and Cancel buttons
        self.add_ok_cancel_buttons(layout)
        self.setLayout(layout)

    def get_input(self):
        # Return the entered settings
        output = self.user_input.text()
        return output

    def add_ok_cancel_buttons(self, layout):
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        buttonBox = QDialogButtonBox(QBtn)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)


class BrowseFileDialog(QFileDialog):

    def __init__(self, main_gui):
        QFileDialog.__init__(self)
        self.master = main_gui
        self.default_dir = 'C:/'
        # self.file_format = 'csv file, (*.csv)'

    def browse_file(self, file_format):
        file_dir = self.getOpenFileName(self.master, 'Open File', self.default_dir, file_format)[0]
        # change default dir to current dir
        self.default_dir = os.path.split(file_dir)[0]
        return file_dir

    def save_file_name(self, file_format):
        file_dir = self.getSaveFileName(self.master, 'Open File', self.default_dir, file_format)[0]
        # change default dir to current dir
        self.default_dir = os.path.split(file_dir)[0]
        return file_dir

    def browse_directory(self):
        return self.getExistingDirectory()


class InputDialog(QDialog):
    def __init__(self, dialog_type,  parent=None):
        super().__init__(parent)
        self.dialog_type = dialog_type
        self.fields = dict()
        if self.dialog_type == 'import_csv':
            self._set_gui_import_csv_dialog()
        elif self.dialog_type == 'rename':
            self._set_gui_rename_data_set()
        elif self.dialog_type == 'stimulus':
            self._set_gui_stimulus_dialog()

    def get_input(self):
        # Return the entered settings
        output = dict()
        for k in self.fields:
            if k == 'is_global':
                output[k] = self.fields[k].isChecked()
            else:
                output[k] = self.fields[k].text()
        return output

    def _set_gui_stimulus_dialog(self):
        self.setWindowTitle("Settings")

        layout = QVBoxLayout()

        # Create input fields
        self.fields['name'] = QLineEdit()

        # Add labels
        layout.addWidget(QLabel("Name: "))
        layout.addWidget(self.fields['name'])

        # Add OK and Cancel buttons
        self.add_ok_cancel_buttons(layout)
        self.setLayout(layout)

    def _set_gui_import_csv_dialog(self):
        self.setWindowTitle("Settings")

        layout = QVBoxLayout()

        # Create input fields
        self.fields['data_set_name'] = QLineEdit()
        self.fields['fr'] = QLineEdit()
        self.fields['is_global'] = QCheckBox()
        self.fields['select_column'] = QLineEdit()

        # Add labels
        layout.addWidget(QLabel("Data Name:"))
        layout.addWidget(self.fields['data_set_name'])
        layout.addWidget(QLabel("Sampling Rate:"))
        layout.addWidget(self.fields['fr'])
        layout.addWidget(QLabel("Global Data Set:"))
        layout.addWidget(self.fields['is_global'])
        layout.addWidget(QLabel("Select single column only:"))
        layout.addWidget(self.fields['select_column'])

        # Add OK and Cancel buttons
        self.add_ok_cancel_buttons(layout)
        self.setLayout(layout)

    def _set_gui_rename_data_set(self):
        self.setWindowTitle("Rename Data Set")

        layout = QVBoxLayout()

        # Create input fields
        self.fields['data_set_name'] = QLineEdit()

        # Add labels
        layout.addWidget(QLabel("Data Name:"))
        layout.addWidget(self.fields['data_set_name'])

        # Add OK and Cancel buttons
        self.add_ok_cancel_buttons(layout)
        self.setLayout(layout)

    def add_ok_cancel_buttons(self, layout):
        QBtn = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        buttonBox = QDialogButtonBox(QBtn)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)


class ChangeStyle(QWidget):
    def __init__(self):
        super().__init__()

    def get_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            # print(f"Selected color: {color.name()}")
            pass
        return color.name()

    def get_lw(self):
        dialog = SimpleInputDialog(title='Settings', text='Line Width: ')
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return float(dialog.get_input())
        else:
            return None


class MessageBox:
    def __init__(self, title, text):
        dlg = QMessageBox()
        dlg.setWindowTitle(title)
        dlg.setText(text)
        dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
        button = dlg.exec()
        if button == QMessageBox.StandardButton.Ok:
            return

