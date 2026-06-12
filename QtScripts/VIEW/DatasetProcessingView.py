from PyQt6.QtCore import QSize
from PyQt6.QtGui import QIcon, QPixmap, QTransform, QIntValidator, QDoubleValidator
from PyQt6.QtWidgets import QApplication, QFrame, QVBoxLayout, QTabWidget, QHBoxLayout, \
    QGridLayout, QCheckBox, QLabel, QPushButton, QLineEdit, QComboBox

from QtScripts.WIDGETS.CustomProgressBar import CustomProgressBar
from QtScripts.WIDGETS.TableEditor import TableEditor
from QtScripts.params import resource_path


class DatasetProcessingView(QFrame):
    def __init__(self, app: QApplication, parent:QFrame=None, controller=None):
        super().__init__(parent=parent)
        self.app = app
        self.controller = controller
        self.parent = parent
        self.viewlayout = QVBoxLayout()
        self.parent.setLayout(self.viewlayout)
        
        
        self.widgets = {}
        
        self.processing_steps_tabs = QTabWidget()
        self.processing_steps_tabs.setTabPosition(QTabWidget.TabPosition.West)
        self.processing_steps_tabs.setIconSize(QSize(160, 160))
        self.processing_steps_tabs.currentChanged.connect(self.on_tab_changed)
        # self.summary = QFrame()
        
        self.filesorter_tab = QFrame()
        self.signal_tab = QFrame()
        self.filename_tab = QFrame()
        # keys : 0 = filesorter, 1 = signal, 2 = filename
        self.tab_states = {0: 2, 1: 2, 2: 2} # value = 0: good, 1: errors, 2: grey
        
        self.progress_bar = CustomProgressBar()
        self.progress_bar.set_task("No task running.")
        
        self.viewlayout.addWidget(self.processing_steps_tabs, stretch=20)
        self.viewlayout.addWidget(self.progress_bar, stretch=1)
        
        
        self.manage_filesorter_tab()
        self.manage_signal_processing_tab()
        self.manage_filename_tab()
        self.manage_summary()
        
        
    def manage_filesorter_tab(self):
        filesorter_icon = QIcon(
            QPixmap(resource_path("data/firelearn_img/filesorter_grey.png")).transformed(QTransform().rotate(90))
        )
        self.processing_steps_tabs.addTab(self.filesorter_tab, filesorter_icon, "")
        grid = QGridLayout()
        n_rows = 10
        for i in range(n_rows):
            grid.setRowStretch(i, 1)
        
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(3, 20)
        # ------------- WIDGETS
        
        multiple_files_ckbox = QCheckBox(parent=self.filesorter_tab, text="Sorting multiple files")
        path_to_parent_label = QLabel(parent=self.filesorter_tab, text="Path to parent directory:")
        path_to_parent_btn = QPushButton(parent=self.filesorter_tab, text="Open")
        path_to_parent_edit = QLineEdit(parent=self.filesorter_tab, )
        path_to_parent_edit.setEnabled(False)
        
        to_include_label = QLabel(parent=self.filesorter_tab, text="To include:")
        to_include_tableedit = TableEditor(parent=self.filesorter_tab, headers=["Key",])
        
        to_exclude_label = QLabel(parent=self.filesorter_tab, text="To exclude:")
        to_exclude_tableedit = TableEditor(parent=self.filesorter_tab, headers=["Key",])
        
        target_key_label = QLabel(parent=self.filesorter_tab, text="Targets :")
        target_tableedit = TableEditor(parent=self.filesorter_tab, headers=["Target key", "Target value"])
        
        single_file_ckbox = QCheckBox(parent=self.filesorter_tab, text="Single file processing")
        path_to_file_label = QLabel(parent=self.filesorter_tab, text="Path to file:")
        path_to_file_btn = QPushButton(parent=self.filesorter_tab, text="Open")
        path_to_file_edit = QLineEdit(parent=self.filesorter_tab, )
        path_to_file_edit.setEnabled(False)
        
        # ------------ LAYOUT
        grid.addWidget(multiple_files_ckbox, 0, 0)
        grid.addWidget(path_to_parent_label, 1, 0)
        grid.addWidget(path_to_parent_btn, 1, 1, 1, 2)
        grid.addWidget(path_to_parent_edit, 1, 3)
        
        grid.addWidget(to_include_label, 2, 0,)
        grid.addWidget(to_include_tableedit, 3, 1, 1, 4)
        grid.addWidget(to_exclude_label, 4, 0,)
        grid.addWidget(to_exclude_tableedit, 5, 1, 1, 4)
        grid.addWidget(target_key_label, 6, 0,)
        
        grid.addWidget(target_tableedit, 7, 1, 1, 4)
        
        grid.addWidget(single_file_ckbox, 8, 0)
        grid.addWidget(path_to_file_label, 9, 0)
        grid.addWidget(path_to_file_btn, 9, 1, 1, 2)
        grid.addWidget(path_to_file_edit, 9, 3)
        
        self.filesorter_tab.setLayout(grid)
        
        # ------ SAVE WIDGETS
        names = [(multiple_files_ckbox, "multiple_files_ckbox"), (path_to_parent_edit, "path_to_parent_edit"),
                 (to_include_tableedit, "to_include_tableedit"), (to_exclude_tableedit, "to_exclude_tableedit"),
                 (target_tableedit, "target_tableedit"), (single_file_ckbox, "single_file_ckbox"),
                 (path_to_file_edit, "path_to_file_edit")]
        for widget, name in names:
            self.widgets[name] = widget
            
        # ------ SIGNALS
        path_to_parent_btn.clicked.connect(self.controller.select_parent_directory)
        path_to_file_btn.clicked.connect(self.controller.select_single_file_processing)
        
        
     
     
    def check_tab_state(self):
        pass
    
    def on_tab_changed(self, selected_index:int):
        name_index = {0: "filesorter", 1:"signal", 2:"filename"}
        color_index = {0: "green", 1: "red", 2: "grey"}
        
        for tab_index, tab_state in self.tab_states.items():
            if tab_index == selected_index:
                new_icon = QIcon(
                    QPixmap(
                        resource_path(
                            f"data/firelearn_img/{name_index[tab_index]}_blue.png")).transformed(
                        QTransform().rotate(90)))
            
                self.processing_steps_tabs.setTabIcon(tab_index, new_icon)
            else:
                new_icon = QIcon(
                    QPixmap(
                        resource_path(f"data/firelearn_img/{name_index[tab_index]}_{color_index[self.tab_states[tab_index]]}.png")).transformed(QTransform().rotate(90)))
                
                self.processing_steps_tabs.setTabIcon(tab_index, new_icon)
            
            
        

    def manage_signal_processing_tab(self):
        signal_icon = QIcon(
            QPixmap(resource_path("data/firelearn_img/signal_grey.png")).transformed(QTransform().rotate(90))
        )
        self.processing_steps_tabs.addTab(self.signal_tab, signal_icon, "")
        
        grid = QGridLayout()
        # n_rows = 20
        # for i in range(n_rows):
        #     grid.setRowStretch(i, 1)
        
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 20)
        
        # --------------- WIDGETS
        behead_ckbox = QCheckBox(parent=self.signal_tab, text="Behead top-file metadata:")
        behead_edit = QLineEdit(parent=self.signal_tab, )
        
        select_column_ckbox = QCheckBox(parent=self.signal_tab, text="Select column:")
        select_column_edit = QLineEdit(parent=self.signal_tab, )
        select_column_mode_label = QLabel(parent=self.signal_tab, text="mode:")
        select_column_mode_cbbox = QComboBox(parent=self.signal_tab, )
        select_column_mode_cbbox.addItems(["None", "Maximum"])
        select_column_metric_label = QLabel(parent=self.signal_tab, text="metric:")
        select_column_metric_cbbox = QComboBox(parent=self.signal_tab, )
        select_column_metric_cbbox.addItems(["None", "Standard deviation"])
        
        subsample_ckbox = QCheckBox(parent=self.signal_tab, text="Subsample file:")
        subsample_edit = QLineEdit(parent=self.signal_tab, )
        
        fft_ckbox = QCheckBox(parent=self.signal_tab, text="FFT. Sampling frequency (Hz):")
        fft_edit = QLineEdit(parent=self.signal_tab, )
        
        average_ckbox = QCheckBox(parent=self.signal_tab, text="Average column signal")
        
        lin_interp_ckbox = QCheckBox(parent=self.signal_tab, text="Linear interpolation (values):")
        lin_interp_edit = QLineEdit(parent=self.signal_tab, )
        
        filter_ckbox = QCheckBox(parent=self.signal_tab, text="Filtering:")
        filter_order_label = QLabel(parent=self.signal_tab, text="Order:")
        filter_sampling_frequency_label = QLabel(parent=self.signal_tab, text="Sampling frequency (Hz):")
        filter_type_label = QLabel(parent=self.signal_tab, text="Type:")
        filter_first_cut_label = QLabel(parent=self.signal_tab, text="First cut frequency (Hz):")
        filter_second_cut_label = QLabel(parent=self.signal_tab, text="Second cut frequency (Hz):")
        filter_order_edit = QLineEdit(parent=self.signal_tab, )
        filter_sampling_frequency_edit = QLineEdit(parent=self.signal_tab, )
        filter_first_cut_edit = QLineEdit(parent=self.signal_tab, )
        filter_second_cut_edit = QLineEdit(parent=self.signal_tab, )
        filter_type_cbbox = QComboBox(parent=self.signal_tab, )
        filter_type_cbbox.addItems(["None", "Highpass", "Lowpass", "Bandpass", "Bandstop"])
        
        harmonics_ckbox = QCheckBox(parent=self.signal_tab, text="Harmonics filtering:")
        harmonics_type_label = QLabel(parent=self.signal_tab, text="Type:")
        harmonics_frequency_label = QLabel(parent=self.signal_tab, text="Harmonic frequency (Hz):")
        harmonics_nth_label = QLabel(parent=self.signal_tab, text="Up to nth harmonic:")
        harmonics_nth_edit = QLineEdit(parent=self.signal_tab, )
        harmonics_frequency_edit = QLineEdit(parent=self.signal_tab, )
        harmonics_type_cbbox = QComboBox(parent=self.signal_tab, )
        harmonics_type_cbbox.addItems(["None", "All", "Even", "Odd"])
        
        exception_column_label = QLabel(parent=self.signal_tab, text="Exception column:")
        exception_column_edit = QLineEdit(parent=self.signal_tab,)
        exception_column_edit.setText("Time")
        
        # ------------ LAYOUT
        grid.addWidget(behead_ckbox, 0, 0)
        grid.addWidget(behead_edit, 0, 2)
        grid.addWidget(select_column_ckbox, 1, 0)
        grid.addWidget(select_column_edit, 1, 2)
        grid.addWidget(select_column_mode_label, 2, 1)
        grid.addWidget(select_column_mode_cbbox, 2, 2)
        grid.addWidget(select_column_metric_label, 3, 1)
        grid.addWidget(select_column_metric_cbbox, 3, 2)
        grid.addWidget(subsample_ckbox, 4, 0)
        grid.addWidget(subsample_edit, 4, 2)
        grid.addWidget(fft_ckbox, 5, 0)
        grid.addWidget(fft_edit, 5, 2)
        grid.addWidget(average_ckbox, 6, 0)
        grid.addWidget(lin_interp_ckbox, 7, 0)
        grid.addWidget(lin_interp_edit, 7, 2)
        grid.addWidget(filter_ckbox, 8, 0)
        grid.addWidget(filter_order_label, 9, 1)
        grid.addWidget(filter_order_edit, 9, 2)
        grid.addWidget(filter_sampling_frequency_label, 10, 1)
        grid.addWidget(filter_sampling_frequency_edit, 10, 2)
        grid.addWidget(filter_type_label, 11, 1)
        grid.addWidget(filter_type_cbbox, 11, 2)
        grid.addWidget(filter_first_cut_label, 12, 1)
        grid.addWidget(filter_first_cut_edit, 12, 2)
        grid.addWidget(filter_second_cut_label, 13, 1)
        grid.addWidget(filter_second_cut_edit, 13, 2)
        grid.addWidget(harmonics_ckbox, 14, 0)
        grid.addWidget(harmonics_type_label, 15, 1)
        grid.addWidget(harmonics_type_cbbox, 15, 2)
        grid.addWidget(harmonics_frequency_label, 16, 1)
        grid.addWidget(harmonics_frequency_edit, 16, 2)
        grid.addWidget(harmonics_nth_label, 17, 1)
        grid.addWidget(harmonics_nth_edit, 17, 2)
        grid.addWidget(exception_column_label, 18, 0)
        grid.addWidget(exception_column_edit, 18, 2)
        
        self.signal_tab.setLayout(grid)
        
        # --------- VALIDATORS
        behead_edit.setValidator(QIntValidator())
        select_column_edit.setValidator(QIntValidator())
        filter_first_cut_edit.setValidator(QDoubleValidator())
        filter_second_cut_edit.setValidator(QDoubleValidator())
        filter_sampling_frequency_edit.setValidator(QDoubleValidator())
        harmonics_frequency_edit.setValidator(QDoubleValidator())
        fft_edit.setValidator(QDoubleValidator())
        subsample_edit.setValidator(QIntValidator())
        lin_interp_edit.setValidator(QIntValidator())
        filter_order_edit.setValidator(QIntValidator())
        harmonics_nth_edit.setValidator(QIntValidator())
        
        # --------- SAVE WIDGETS
        names = [(behead_ckbox, "behead_ckbox"), (behead_edit, "behead_edit"), (select_column_ckbox, "select_column_ckbox"),
                 (select_column_edit, "select_column_edit"),
                 (select_column_mode_cbbox, "select_column_mode_cbbox"), (select_column_metric_cbbox, "select_column_metric_cbbox"),
                 (subsample_ckbox, "subsample_ckbox"), (subsample_edit, "subsample_edit"), (fft_ckbox, "fft_ckbox"),
                 (fft_edit, "fft_edit"), (average_ckbox, "average_ckbox"), (lin_interp_ckbox, "lin_interp_ckbox"),
                 (lin_interp_edit, "lin_interp_edit"), (filter_ckbox, "filter_ckbox"), (filter_order_edit, "filter_order_edit"),
                 (filter_sampling_frequency_edit, "filter_sampling_frequency_edit"), (filter_first_cut_edit, "filter_first_cut_edit"),
                 (filter_second_cut_edit, "filter_second_cut_edit"),(filter_type_cbbox, "filter_type_cbbox"),
                 (harmonics_ckbox, "harmonics_ckbox"), (harmonics_type_cbbox, "harmonics_type_cbbox"),
                 (harmonics_nth_edit, "harmonics_nth_edit"), (harmonics_frequency_edit, "harmonics_frequency_edit"),
                 (exception_column_edit, "exception_column_edit"),]
        for widget, name in names:
            self.widgets[name] = widget
        
        
    def manage_filename_tab(self):
        filename_icon = QIcon(
            QPixmap(resource_path("data/firelearn_img/filename_grey.png")).transformed(QTransform().rotate(90))
        )
        self.processing_steps_tabs.addTab(self.filename_tab, filename_icon, "")
        grid = QGridLayout()
        # n_rows = 20
        # for i in range(n_rows):
        #     grid.setRowStretch(i, 1)
        
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 20)
        
        # --------- WIDGETS
        random_key_ckbox = QCheckBox(parent=self.filename_tab, text="Add random key to file name")
        timestamp_ckbox = QCheckBox(parent=self.filename_tab, text="Add timestamp to file name")
        keyword_ckbox = QCheckBox(parent=self.filename_tab, text="Add keyword to file name")
        keyword_edit = QLineEdit(parent=self.filename_tab, )
        make_dataset_ckbox = QCheckBox(parent=self.filename_tab, text="Concatenate files as full dataset", )
        make_dataset_ckbox.setChecked(True)
        filename_ckbox = QCheckBox(parent = self.filename_tab, text="Specify file name: ")
        filename_edit = QLineEdit(parent = self.filename_tab, )
        save_label = QLabel(parent=self.filename_tab, text="Save processed files under:")
        save_btn = QPushButton(parent=self.filename_tab, text="Open")
        save_edit = QLineEdit(parent=self.filename_tab, )
        save_edit.setEnabled(False)
        
        check_steps_btn = QPushButton(parent=self.filename_tab, text="Check processing steps")
        process_btn = QPushButton(parent=self.filename_tab, text="Start processing")
        export_summary_btn = QPushButton(parent=self.filename_tab, text="Export processing summary", )
        export_summary_btn.setEnabled(False)
        
        grid.addWidget(random_key_ckbox, 0, 0)
        grid.addWidget(timestamp_ckbox, 1, 0)
        grid.addWidget(timestamp_ckbox, 1, 2)
        grid.addWidget(keyword_ckbox, 2, 0)
        grid.addWidget(keyword_edit, 2, 2)
        grid.addWidget(make_dataset_ckbox, 3, 0)
        grid.addWidget(filename_ckbox, 4, 0)
        grid.addWidget(filename_edit, 4, 2)
        grid.addWidget(save_label, 5, 0)
        grid.addWidget(save_btn, 5, 1)
        grid.addWidget(save_edit, 5, 2)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(check_steps_btn)
        buttons_layout.addWidget(process_btn)
        buttons_layout.addWidget(export_summary_btn)
        
        grid.addLayout(buttons_layout, 6, 0, 1, 4)
        
        self.filename_tab.setLayout(grid)
        # -------- SAVE WIDGETS
        names = [(random_key_ckbox, "random_key_ckbox"), (timestamp_ckbox, "timestamp_ckbox"),
                 (keyword_ckbox, "keyword_ckbox"), (keyword_edit, "keyword_edit"), (make_dataset_ckbox, "make_dataset_ckbox"),
                 (filename_ckbox, "filename_ckbox"), (filename_edit, "filename_edit"), (save_edit, "save_edit"),]
        for widget, name in names:
            self.widgets[name] = widget
            
        # -------- STYLE
        for btn in [process_btn, check_steps_btn, export_summary_btn]:
            btn.setFixedHeight(50)
            if btn != export_summary_btn:
                btn.setObjectName("StartProcessButton")
        
        # ------- SIGNALS
        save_btn.clicked.connect(self.controller.select_save_processed_files_under)
        check_steps_btn.clicked.connect(self.controller.check_params_validity)
        export_summary_btn.clicked.connect(self.controller.export_summary)
        process_btn.clicked.connect(self.controller.init_processing)
        
    def save_widgets(self, widgets):
        for widget in widgets:
            self.controller.save_widget(widget)
        
    def manage_summary(self):
        pass