from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QDialogButtonBox, QFileDialog, QHBoxLayout, QCheckBox
)
from PyQt6.QtGui import QIntValidator, QDoubleValidator


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
