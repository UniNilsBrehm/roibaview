from roibaview.plugins.base import BasePlugin
from roibaview.gui_utils import DynamicInputDialog
from PyQt6.QtWidgets import QDialog, QMessageBox
import pandas as pd
import os


class ConvertCSVFile(BasePlugin):
    name = "Convert CSV file"
    category = 'utils'

    def __init__(self, **kwargs):
        pass

    def apply(self):
        fields = {
            'input_file': ('', 'file'),
            'save_dir': ('', 'dir'),
            'input_delimiter': ('tab', 'string'),
            'output_delimiter': (',', 'string')
        }

        dialog = DynamicInputDialog(title="Convert CSV File", fields=fields)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_inputs()

            # Validate input file
            if not os.path.isfile(params['input_file']):
                QMessageBox.critical(None, "File Error", "The selected input file is not valid.")
                return

            # Handle delimiters
            sep_input = '\t' if params['input_delimiter'] == 'tab' else params['input_delimiter']
            sep_output = '\t' if params['output_delimiter'] == 'tab' else params['output_delimiter']

            try:
                # Read the file
                input_file = pd.read_csv(params['input_file'], sep=sep_input, engine='python')

                # Save the file
                output_path = params['save_dir']
                # output_path = os.path.join(params['save_dir'], "converted.csv")
                input_file.to_csv(output_path, sep=sep_output, index=False)
                QMessageBox.information(None, "Success", f"File saved to:\n{output_path}")

            except Exception as e:
                QMessageBox.critical(None, "Conversion Error", f"An error occurred:\n{str(e)}")


class RemoveColFromCSV(BasePlugin):
    name = "Remove Column from CSV"
    category = 'utils'

    def __init__(self, **kwargs):
        pass

    def apply(self):
        fields = {
            'input_file': ('', 'file'),
            'save_dir': ('', 'dir'),
            'column': (0, 'int'),
            'headers': (True, 'bool')
        }

        dialog = DynamicInputDialog(title="Remove Column", fields=fields)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_inputs()

            # Validate input file
            if not os.path.isfile(params['input_file']):
                QMessageBox.critical(None, "File Error", "The selected input file is not valid.")
                return

            # Read the file
            input_file = pd.read_csv(params['input_file'])
            col_nr = params['column']

            # Remove the column
            df = input_file.drop(input_file.columns[col_nr], axis=1)

            # Save to HDD
            save_dir = params['save_dir']
            if params['headers']:
                df.to_csv(save_dir, index=False)
            else:
                df.to_csv(save_dir, index=False, header=None)
