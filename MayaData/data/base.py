from MayaData.lib.pyside import QtWidgets, maya_window
import json


file_filter = 'Json (*.json)'
dialog = QtWidgets.QDialog(maya_window())


class BaseData(dict):
    def __init__(self, *args, **kwargs):
        super(BaseData, self).__init__(*args, **kwargs)
        
    def save(self):
        file_path, selected_filter = QtWidgets.QFileDialog.getSaveFileName(dialog, 'Select File', '', file_filter)
        if not file_path:
            return
        with open(file_path, 'w') as f:
            f.write(json.dumps(self, indent=4))

    def load(self):
        file_path, selected_filter = QtWidgets.QFileDialog.getOpenFileName(dialog, 'Select File', '', file_filter)
        if not file_path:
            return
        with open(file_path, 'r') as f:
            self.update(json.loads(f.read()))
