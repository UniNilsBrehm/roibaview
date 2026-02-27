import os
import numpy as np
import pandas as pd
import configparser
from PyQt6.QtWidgets import QMessageBox, QListWidgetItem, QDialog
from PyQt6.QtCore import pyqtSignal, QObject, Qt
from roibaview.data_handler import DataHandler
from roibaview.gui_utils import SimpleInputDialog, BrowseFileDialog, InputDialog, ChangeStyle, MessageBox
from roibaview.data_plotter import DataPlotter, PyqtgraphSettings
from roibaview.video_viewer import VideoViewer
from roibaview.plugins.loader import load_plugins


class Controller(QObject):
    # ==================================================================================================================
    # SIGNALS
    # ------------------------------------------------------------------------------------------------------------------
    signal_import_traces = pyqtSignal()
    signal_roi_idx_changed = pyqtSignal()
    signal_closing = pyqtSignal()

    # ==================================================================================================================
    # INITIALIZING
    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self, gui):
        QObject.__init__(self)
        # Create GUI
        self.gui = gui
        self.gui.controller = self  # Expose controller to plugins via GUI
        self.gui.closeEvent = self.closeEvent
        self.mouse_x_pos = 0

        # Get a DataHandler
        self.data_handler = DataHandler()
        self.selected_data_sets = []
        self.selected_data_sets_type = []
        self.selected_data_sets_rows = []
        self.selected_data_sets_items = []
        self.current_roi_idx = 0

        # View Box Right Click Context Menu
        # Hide "Plot Options"
        self.gui.trace_plot_item.ctrlMenu.menuAction().setVisible(False)

        # Get a Video Viewer
        self.video_viewer = VideoViewer()
        self.video_viewers = []

        # Get DataPlotter
        self.data_plotter = DataPlotter(self.gui.trace_plot_item)

        # Get a File Browser
        self.file_browser = BrowseFileDialog(self.gui)

        # Get a VR Detector
        self.vr_detection = None

        # Set Selection Mode
        self.signal_selection_status = False
        self.cut_out_region = None

        # Establish Connections to Buttons and Menus
        self.connections()

        # KeyBoard Bindings
        self.gui.trace_plot_item.scene().sigMouseMoved.connect(self.mouse_moved)

        self.pyqtgraph_settings = PyqtgraphSettings()

        # Check Config File
        package_dir = os.path.dirname(__file__)
        config_path = os.path.join(package_dir, 'config.ini')
        self.config_name = config_path

        if not os.path.exists(self.config_name):
            self._create_config_file()
        else:
            self.config = configparser.ConfigParser()
            self.config.read(self.config_name)

        # Load plugins with context (pass config and GUI as needed)
        self.plugins = load_plugins(context={
            'config': self.config,  # or other settings object
            'parent': self.gui  # used for dialog-based plugins
        })

        # Categorize them for use
        self.tool_plugins = [p for p in self.plugins if p.category == "tool"]
        self.utils_plugins = [p for p in self.plugins if p.category == "utils"]

        # Context Menu
        self.filter_plugins = [p for p in self.plugins if p.category == "filter"]
        self.transformation_plugins = [p for p in self.plugins if p.category == "transformation"]

        # Register tools in Tools menu
        self.gui.add_tools_menu_plugins(self.tool_plugins)

        # Register utils in Utils menu
        self.gui.add_utils_menu_plugins(self.utils_plugins)

        # Populate Context Menu Filter Plugins
        self.gui.populate_filter_plugins_menu(self.filter_plugins, self.apply_filter_plugin)
        self.gui.populate_transformation_plugins_menu(self.transformation_plugins, self.apply_filter_plugin)

    def apply_filter_plugin(self, plugin):
        if not self.selected_data_sets:
            return

        for name, kind in zip(self.selected_data_sets, self.selected_data_sets_type):
            data = self.data_handler.get_data_set(kind, name)
            meta = self.data_handler.get_data_set_meta_data(kind, name)
            result = plugin.apply(data, meta['sampling_rate'])
            if type(result) is tuple:  # function returns two values, the second is the new sampling rate (down sampling)
                fr = result[1]
                result = result[0]
            else:
                fr = meta['sampling_rate']
            new_name = f"{name}_{plugin.name.replace(' ', '_')}"
            already_exists = self.data_handler.add_new_data_set(
                data_set_type=kind,
                data_set_name=new_name,
                data=result,
                sampling_rate=fr,
                time_offset=0,
                y_offset=0,
                header=meta.get("roi_names", list(range(result.shape[1])))
            )
            if already_exists:
                data_set_name = new_name + '_new'
                self.add_data_set_to_list(kind, data_set_name)
            else:
                self.add_data_set_to_list(kind, new_name)

    def _create_config_file(self):
        self.config = configparser.ConfigParser()
        self.config['FFMPEG'] = {'dir': 'NaN'}
        with open(self.config_name, 'w') as configfile:
            self.config.write(configfile)

    def connections(self):
        # File Menu
        self.gui.file_menu_import_csv.triggered.connect(self.import_csv_file)
        self.gui.file_menu_new_viewer_file.triggered.connect(self.new_file)
        self.gui.file_menu_save_viewer_file.triggered.connect(self.save_file)
        self.gui.file_men_open_viewer_file.triggered.connect(self.open_file)
        self.gui.file_menu_action_exit.triggered.connect(self.gui.close)

        # DataSets List
        # Connect item selection changed signal
        self.gui.data_sets_list.itemSelectionChanged.connect(self.data_set_selection_changed)

        # Arrow Buttons
        # self.gui.next_button.clicked.connect(self.next_roi)
        # self.gui.prev_button.clicked.connect(self.prev_roi)

        # ROI changed
        self.signal_roi_idx_changed.connect(lambda: self.update_plots(change_global=False))

        # Context Menu
        self.gui.data_sets_list_rename.triggered.connect(self.rename_data_set)
        self.gui.data_sets_list_delete.triggered.connect(self.delete_data_set)
        self.gui.data_sets_list_delete_col.triggered.connect(self.delete_column)

        self.gui.data_sets_list_export.triggered.connect(self.export_to_csv)
        self.gui.data_sets_list_time_offset.triggered.connect(self.time_offset)
        self.gui.data_sets_list_y_offset.triggered.connect(self.y_offset)

        # Style Submenu
        self.gui.style_color.triggered.connect(self.pick_color)
        self.gui.style_lw.triggered.connect(self.pick_lw)

        # Tools
        # Video Viewer
        self.gui.tools_menu_open_video_viewer.triggered.connect(self.open_video_viewer)
        self.video_viewer.TimePoint.connect(self.connect_video_to_plot)

        # Convert Ventral Root
        self.gui.tools_menu_convert_ventral_root.triggered.connect(self.convert_ventral_root)

        # Create Stimulus from File
        self.gui.tools_menu_create_stimulus.triggered.connect(self.create_stimulus_from_file)

        # KeyBoard Bindings
        self.gui.key_pressed.connect(self.on_key_press)
        self.data_plotter.master_plot.scene().sigMouseClicked.connect(self.on_mouse_click)

    def delete_column(self):
        if len(self.selected_data_sets) > 1:
            dlg = QMessageBox()
            dlg.setWindowTitle('ERROR')
            dlg.setText(f'You cannot rename multiple data sets at once!')
            button = dlg.exec()
            if button == QMessageBox.StandardButton.Ok:
                return None
        if len(self.selected_data_sets) == 0:
            return None

        # Get Column Nr
        dialog = SimpleInputDialog(title='Settings', text='Please enter some stuff: ')
        if dialog.exec() == QDialog.DialogCode.Accepted:
            received = dialog.get_input()
        else:
            return None

        col_nr = int(received)
        data_set_name, data_set_type, data_set_item = self.get_selected_data_sets(0)

        # Remove the column
        self.data_handler.delete_column(data_set_type, data_set_name, col_nr)

    def export_to_csv(self):
        file_dir = self.file_browser.save_file_name('csv file, (*.csv *.txt)')
        if file_dir:
            if len(self.selected_data_sets) > 1:
                dlg = QMessageBox()
                dlg.setWindowTitle('ERROR')
                dlg.setText(f'You cannot export multiple data sets at once!')
                button = dlg.exec()
                if button == QMessageBox.StandardButton.Ok:
                    return None
            if len(self.selected_data_sets) == 0:
                return None

            # Export selected data set to csv
            data_set_name, data_set_type, data_set_item = self.get_selected_data_sets(0)
            df = pd.DataFrame(self.data_handler.get_data_set(data_set_type=data_set_type, data_set_name=data_set_name))
            df.to_csv(file_dir, index=False, header=False)

    def create_stimulus_from_file(self):
        file_dir = self.file_browser.browse_file('csv file, (*.csv *.txt)')
        if file_dir:
            dialog = InputDialog(dialog_type='stimulus')
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # name
                received = dialog.get_input()
                data_set_name = received['name']
            else:
                return None

            protocol = pd.read_csv(file_dir)
            t_max = max(protocol.max())
            # t0 = 0
            fr = 100
            stimulus = np.zeros(int(fr * t_max))
            for on, off in zip(protocol.iloc[:, 0], protocol.iloc[:, 1]):
                start = int(on * fr)
                end = int(off * fr)
                stimulus[start:end] = 1

            # Prepare it for hdf5 matrix form
            stimulus = list(stimulus[:, np.newaxis])
            data_set_type = 'global_data_sets'
            # Add stimulus to data sets
            self.data_handler.add_new_data_set(
                data_set_type=data_set_type,
                data_set_name=data_set_name,
                data=stimulus,
                sampling_rate=fr,
                time_offset=0,
                y_offset=0,
                header='Stimulus')

            # Add new data set to the list in the GUI
            self.add_data_set_to_list(data_set_type, data_set_name)

    def convert_ventral_root(self):
        """
        Expects following file structure:
        └── vr_data
            ├── sweep_01
            │   ├── sw_01_01.txt
            │   ├── sw_01_02.txt
            │   :
            │   └── sw_01_n.txt
            ├── sweep_02
            :
            └── sweep_n

        All vr text files from one sweep will then be combined into one meaningful and solid data file (csv)
        :return:
        """
        from joblib import Parallel, delayed
        from roibaview.ventral_root import transform_ventral_root_parallel, pickle_stuff
        file_structure = '''
        Expects following file structure:
        └── vr_data
            ├── sweep_01
            │   ├── sw_01_01.txt
            │   ├── sw_01_02.txt
            │   :
            │   └── sw_01_n.txt
            ├── sweep_02
            :
            └── sweep_n
            
        All vr text files from one sweep will then be combined into one meaningful and solid data file (csv)
        '''

        store_to_dict = False
        vr_rec_dur = 60  # in secs
        vr_fr = 10000  # in Hz

        # Get directory
        file_dir = self.file_browser.browse_directory()
        save_dir = file_dir
        if file_dir:
            print('========== VENTRAL ROOT ==========')
            print('')
            print(file_structure)
            print('')
            print(f'Ventral Root Recording Files in: {file_dir}')
            print(f'Store result to: {save_dir}')
            print('++++ START PROCESSING +++')
            print('This can take some time ...')
            print( 'This relies heavily on CPU, RAM and HDD. HDD is normally the bottleneck, so make sure to use a fast one!')
            print('... Please Wait ...')
            print('')
            # Process all sweeps in parallel
            sweep_numbers = os.listdir(file_dir)
            results = Parallel(n_jobs=-2)(delayed(
                transform_ventral_root_parallel)(save_dir, file_dir, vr_rec_dur, vr_fr, i) for i in
                                          sweep_numbers)
            if store_to_dict:
                print('STORING DICT TO HDD')
                vr_recordings = dict()
                for res in results:
                    sw = list(res.keys())[0]
                    vr_recordings[sw] = res[sw]
                pickle_stuff(f'{save_dir}/all_ventral_root.pickle', data=vr_recordings)

            print('++++ FINISHED PROCESSING ++++')

    def pick_lw(self):
        if len(self.selected_data_sets) > 1:
            dlg = QMessageBox()
            dlg.setWindowTitle('ERROR')
            dlg.setText(f'You cannot change color of multiple data sets at once!')
            button = dlg.exec()
            if button == QMessageBox.StandardButton.Ok:
                return None

        if len(self.selected_data_sets) == 0:
            return None

        lw = ChangeStyle().get_lw()
        data_set_name, data_set_type, data_set_item = self.get_selected_data_sets(0)
        self.data_handler.add_meta_data(data_set_type=data_set_type, data_set_name=data_set_name, metadata_dict={'lw': lw})
        self.update_plots(change_global=True)

    def pick_color(self):
        if len(self.selected_data_sets) > 1:
            dlg = QMessageBox()
            dlg.setWindowTitle('ERROR')
            dlg.setText(f'You cannot change color of multiple data sets at once!')
            button = dlg.exec()
            if button == QMessageBox.StandardButton.Ok:
                return None

        if len(self.selected_data_sets) == 0:
            return None

        color = ChangeStyle().get_color()
        data_set_name, data_set_type, data_set_item = self.get_selected_data_sets(0)
        self.data_handler.add_meta_data(data_set_type=data_set_type, data_set_name=data_set_name, metadata_dict={'color': color})
        self.update_plots(change_global=True)

    def connect_video_to_plot(self, time_point):
        for v in self.video_viewers:
            if v.connected_to_data_trace:
                if len(self.selected_data_sets) > 0:
                    y_min = []
                    y_max = []
                    for data_set_name, data_set_type in zip(self.selected_data_sets, self.selected_data_sets_type):
                        if data_set_type == 'data_sets':
                            data = self.data_handler.get_roi_data(data_set_name, roi_idx=self.current_roi_idx)
                        else:
                            data = self.data_handler.get_data_set('global_data_sets', data_set_name)
                        y_min.append(np.min(data))
                        y_max.append(np.max(data))
                    y_range = [np.min(y_min), np.max(y_max)]
                    self.data_plotter.update_video_plot(time_point, y_range)
                else:
                    self.data_plotter.clear_plot_data(name='video')
            else:
                self.data_plotter.clear_plot_data(name='video')

    def open_video_viewer(self):
        self.video_viewers.append(VideoViewer())
        self.video_viewers[-1].show()
        self.video_viewers[-1].TimePoint.connect(self.connect_video_to_plot)

    def y_offset(self):
        if len(self.selected_data_sets) > 0:
            for k, _ in enumerate(self.selected_data_sets):
                data_set_name = self.selected_data_sets[k]
                data_set_type = self.selected_data_sets_type[k]
                meta_data = self.data_handler.get_data_set_meta_data(
                    data_set_type=data_set_type,
                    data_set_name=data_set_name
                )

                # Get settings by user input
                dialog = SimpleInputDialog('Settings', 'Please enter Y Offset: ', default_value=meta_data['y_offset'])
                if dialog.exec() == dialog.DialogCode.Accepted:
                    y_offset = {'y_offset': float(dialog.get_input())}
                    self.data_handler.add_meta_data(data_set_type, data_set_name, y_offset)
                    self.update_plots(change_global=True)
                else:
                    return None

    def time_offset(self):
        if len(self.selected_data_sets) > 0:
            for k, _ in enumerate(self.selected_data_sets):
                data_set_name = self.selected_data_sets[k]
                data_set_type = self.selected_data_sets_type[k]
                meta_data = self.data_handler.get_data_set_meta_data(
                    data_set_type=data_set_type,
                    data_set_name=data_set_name
                )

                # Get settings by user input
                dialog = SimpleInputDialog('Settings', 'Please enter Time Offset [s]: ', default_value=meta_data['time_offset'])
                if dialog.exec() == dialog.DialogCode.Accepted:
                    time_offset = {'time_offset': float(dialog.get_input())}
                    self.data_handler.add_meta_data(data_set_type, data_set_name, time_offset)
                    self.update_plots(change_global=True)
                else:
                    return None

    def rename_data_set(self):
        if len(self.selected_data_sets) > 1:
            dlg = QMessageBox()
            dlg.setWindowTitle('ERROR')
            dlg.setText(f'You cannot rename multiple data sets at once!')
            button = dlg.exec()
            if button == QMessageBox.StandardButton.Ok:
                return None
        if len(self.selected_data_sets) == 0:
            return None

        data_set_name, data_set_type, data_set_item = self.get_selected_data_sets(0)
        # Get settings by user input
        dialog = InputDialog(dialog_type='rename')
        if dialog.exec() == QDialog.DialogCode.Accepted:
            received = dialog.get_input()
            new_name = received['data_set_name']
            if new_name != '':
                self.data_handler.rename_data_set(data_set_type=data_set_type, data_set_name=data_set_name, new_name=new_name)
                self.rename_item_from_list(data_set_item=data_set_item, new_name=new_name)
            else:
                dlg = QMessageBox()
                dlg.setWindowTitle('ERROR')
                dlg.setText(f'Please enter a valid name!')
                button = dlg.exec()
                if button == QMessageBox.StandardButton.Ok:
                    return None
        else:
            return None

    def delete_data_set(self):
        if len(self.selected_data_sets) > 0:
            dlg = QMessageBox(self.gui)
            dlg.setWindowTitle('Delete Data Set')
            dlg.setText(f'Are You Sure You Want To Delete The Selected Data Sets" ?')
            dlg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            dlg.setIcon(QMessageBox.Icon.Question)
            button = dlg.exec()
            if button == QMessageBox.StandardButton.Yes:
                for dt, ds, item in zip(self.selected_data_sets_type, self.selected_data_sets, self.selected_data_sets_items):
                    self.data_handler.delete_data_set(dt, ds)
                    self.remove_selected_data_set_from_list(ds, item)

    def get_selected_data_sets(self, k):
        data_set_name = self.selected_data_sets[k]
        data_set_type = self.selected_data_sets_type[k]
        data_set_item = self.selected_data_sets_items[k]
        return data_set_name, data_set_type, data_set_item

    def context_menu(self, mode):
        result = None
        if len(self.selected_data_sets) > 0:
            for k, _ in enumerate(self.selected_data_sets):
                data_set_name = self.selected_data_sets[k]
                data_set_type = self.selected_data_sets_type[k]
                data = self.data_handler.get_data_set(data_set_type=data_set_type, data_set_name=data_set_name)
                meta_data = self.data_handler.get_data_set_meta_data(data_set_type=data_set_type, data_set_name=data_set_name)
                if mode == 'df_f':
                    # Get settings by user input
                    dialog = InputDialog(dialog_type='df_over_f')
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        received = dialog.get_input()
                        fbs_per = float(received['fbs_per'])
                        fbs_win = float(received['fbs_window'])
                    else:
                        return None

                    result = self.data_transformer.to_delta_f_over_f(data, fbs_per=fbs_per, fr=meta_data['sampling_rate'], window=fbs_win)

                if mode == 'z':
                    result = self.data_transformer.to_z_score(data)

                if mode == 'min_max':
                    result = self.data_transformer.to_min_max(data)

                # Create a new data set from this
                if result is not None:
                    check = self.data_handler.add_new_data_set(
                        data_set_type=data_set_type,
                        data_set_name=f'{data_set_name}_{mode}',
                        data=result,
                        sampling_rate=meta_data['sampling_rate'],
                        time_offset=meta_data['time_offset'],
                        y_offset=meta_data['y_offset'],
                        header=f'{data_set_name}_{mode}'
                    )
                    # Add new data set to the list in the GUI
                    if check:
                        # data set name already exists, so whe have to change it
                        data_set_name = f'{data_set_name}_{mode}' + '_new'
                    else:
                        data_set_name = f'{data_set_name}_{mode}'
                    self.add_data_set_to_list(data_set_type, data_set_name)

    def next_roi(self):
        # Note: Future Update:
        # - check all selected data sets and take the largest number of rois
        # - if the smaller data sets runs out of rois, just plot nothing
        # First check if there are active data sets
        if 'data_sets' in self.selected_data_sets_type:
            self.current_roi_idx = (self.current_roi_idx + 1) % self.data_handler.roi_count
            self.signal_roi_idx_changed.emit()

    def prev_roi(self):
        # First check if there are active data sets
        if 'data_sets' in self.selected_data_sets_type:
            self.current_roi_idx = (self.current_roi_idx - 1) % self.data_handler.roi_count
            self.signal_roi_idx_changed.emit()

    def update_plots(self, change_global=True):
        # get new roi data
        roi_data = []
        time_points = []
        global_data = []
        global_time_points = []
        meta_data_list = list()
        global_meta_data_list = list()

        for data_set_name, data_set_type in zip(self.selected_data_sets, self.selected_data_sets_type):
            if data_set_type == 'data_sets':
                # Get the data trace
                r = self.data_handler.get_roi_data(data_set_name, roi_idx=self.current_roi_idx)

                # Get the metadata
                meta_data = self.data_handler.get_data_set_meta_data('data_sets', data_set_name)

                fr = meta_data['sampling_rate']
                time_offset = meta_data['time_offset']
                y_offset = meta_data['y_offset']

                # Add time axis
                try:
                    time_points.append(self.data_handler.compute_time_axis(r.shape[0], fr) + time_offset)
                except AttributeError:
                    return

                # Test for error:
                print('')
                print('Data types:')
                print("type(r):", type(r))
                print("r dtype:", getattr(r, "dtype", None))
                print("y_offset:", y_offset, "type:", type(y_offset))
                print('')

                # Here some TypeError can happen:
                roi_data.append(r + y_offset)
                meta_data_list.append(meta_data)
            if data_set_type == 'global_data_sets' and change_global:
                r = self.data_handler.get_data_set('global_data_sets', data_set_name)
                meta_data = self.data_handler.get_data_set_meta_data('global_data_sets', data_set_name)
                fr = meta_data['sampling_rate']
                time_offset = meta_data['time_offset']
                y_offset = meta_data['y_offset']
                global_time_points.append(self.data_handler.compute_time_axis(r.shape[0], fr) + time_offset)
                global_data.append(r + y_offset)
                global_meta_data_list.append(meta_data)

        # Update Plot
        if len(roi_data) > 0:
            self.data_plotter.update(time_points, roi_data, meta_data_list)
            # Future Update:
            # - Take the column headers as ROI names
            if data_set_type == 'data_sets':
                roi_name = f"ROI: {meta_data['roi_names'][self.current_roi_idx]} ({meta_data['name']})"
                self.data_plotter.master_plot.setTitle(roi_name)
            # self.data_plotter.master_plot.setTitle(f'ROI: {self.current_roi_idx+1}')
        else:
            self.data_plotter.clear_plot_data(name='data')

        # Update Global Plot
        if change_global:
            if len(global_data) > 0:
                self.data_plotter.update_global(global_time_points, global_data, global_meta_data_list)
            else:
                self.data_plotter.clear_plot_data(name='global')

    def data_set_selection_changed(self):
        # Get selected data sets
        self.selected_data_sets = [item.text() for item in self.gui.sender().selectedItems()]
        self.selected_data_sets_type = [item.data(1) for item in self.gui.sender().selectedItems()]
        self.selected_data_sets_items = [k for k in self.gui.sender().selectedItems()]

        # Update Plots
        self.update_plots()

    def import_csv_file(self):
        # Get file dir
        file_dir = self.file_browser.browse_file('csv file, (*.csv *.txt)')
        if file_dir:
            # Get data set name by user
            dialog = InputDialog(dialog_type='import_csv')
            if dialog.exec() == QDialog.DialogCode.Accepted:
                received = dialog.get_input()
                data_set_name = received['data_set_name']
                fr = float(received['fr'])
                is_global = received['is_global']
                single_column = received['select_column']
            else:
                return None

            if is_global:
                data_set_type = 'global_data_sets'
            else:
                data_set_type = 'data_sets'

            # check if the data set name already exists
            check_if_exists = self.data_handler.check_if_exists(data_set_type, data_set_name)
            if check_if_exists:
                MessageBox(title='ERROR', text='Data set with this name already exists! Will rename it.')
                data_set_name = data_set_name + '_new'

            # Import csv file
            status = self.data_handler.import_csv(
                file_dir=file_dir,
                data_name=data_set_name,
                sampling_rate=fr,
                data_set_type=data_set_type,
                column=single_column
            )

            # Add new data set to the list in the GUI
            if status:
                self.add_data_set_to_list(data_set_type, data_set_name)

    def add_data_set_to_list(self, data_set_type, data_set_name):
        # row = self.gui.data_sets_list.count()
        # Add new data set to the list in the GUI
        new_list_item = QListWidgetItem()
        new_list_item.setText(data_set_name)
        new_list_item.setData(1, data_set_type)
        # new_list_item.setData(3, row)
        self.gui.data_sets_list.addItem(new_list_item)

    def rename_item_from_list(self, data_set_item, new_name):
        item = self.gui.data_sets_list.item(self.gui.data_sets_list.row(data_set_item))
        item.setText(new_name)

    def remove_selected_data_set_from_list(self, data_set_name, data_set_item):
        if not data_set_name:
            return
        else:
            self.gui.data_sets_list.takeItem(self.gui.data_sets_list.row(data_set_item))

    def save_file(self):
        file_dir = self.file_browser.save_file_name('hdf5 file, (*.hdf5)')
        if file_dir:
            self.data_handler.save_file(file_dir)

    def open_file(self):
        file_dir = self.file_browser.browse_file('hdf5 file, (*.hdf5)')
        if file_dir:
            self.data_handler.open_file(file_dir)
            data_structure = self.data_handler.get_info()
            # Add new data set to the list in the GUI
            for data_set_type in data_structure:
                for ds in data_structure[data_set_type]:
                    self.add_data_set_to_list(data_set_type, ds)

            # Get the ROI count (from the first data set)
            if 'data_sets' in data_structure:
                ds = data_structure['data_sets'][0]
                self.data_handler.roi_count = self.data_handler.get_roi_count(ds)

    def new_file(self):
        dlg = QMessageBox(self.gui)
        dlg.setWindowTitle('New Session')
        dlg.setText(f'Are you sure you want start a new session. All unsaved data will be lost!')
        dlg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        dlg.setIcon(QMessageBox.Icon.Question)
        button = dlg.exec()
        if button == QMessageBox.StandardButton.Yes:
            self.data_handler.new_file()
            self.gui.data_sets_list.clear()

    def _create_short_cuts(self):
        pass

    def _connect_short_cuts(self, connect=True):
        pass

    # ==================================================================================================================
    # MOUSE AND KEY PRESS HANDLING
    # ------------------------------------------------------------------------------------------------------------------
    def on_mouse_click(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.scenePos()
            mouse_point = self.data_plotter.master_plot.vb.mapSceneToView(pos)
            # Get x value (corresponding to time axis)
            self.mouse_x_pos = mouse_point.x()

    def on_key_press(self, event):
        if event.key() == Qt.Key.Key_Left:
            # left arrow key
            self.prev_roi()
        elif event.key() == Qt.Key.Key_Right:
            # right arrow key
            self.next_roi()

    def closeEvent(self, event):
        retval = self.gui.exit_dialog()

        if retval == QMessageBox.StandardButton.Save:
            # Save before exit
            self.save_file()
            event.accept()
            self.data_handler.create_new_temp_hdf5_file()
        elif retval == QMessageBox.StandardButton.Discard:
            # Do not save before exit
            event.accept()
            self.data_handler.create_new_temp_hdf5_file()
        else:
            # Do not exit
            event.ignore()

    def mouse_moved(self, event):
        vb = self.gui.trace_plot_item.vb
        if self.gui.trace_plot_item.sceneBoundingRect().contains(event):
            mouse_point = vb.mapSceneToView(event)
            self.gui.mouse_label.setText(f"<p style='color:black'>X： {mouse_point.x():.4f} <br> Y: {mouse_point.y():.4f}</p>")
