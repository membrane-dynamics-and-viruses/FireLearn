from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QFrame, QVBoxLayout, QGridLayout, QLabel, QPushButton, QLineEdit, QComboBox, \
    QSlider

from QtScripts.WIDGETS.CustomProgressBar import CustomProgressBar
from QtScripts.WIDGETS.TableEditor import TableEditor
from QtScripts.WIDGETS.TitleLabel import TitleLabel


class UtilitiesView(QFrame):
    def __init__(self, app: QApplication, parent:QFrame=None, controller=None):
        super().__init__(parent=parent)
        self.app = app
        self.controller = controller
        self.parent = parent
        self.viewlayout = QVBoxLayout()
        self.parent.setLayout(self.viewlayout)
        
        self.main_grid = QGridLayout()
        
        self.widgets = {}
        
        
        self.progress_bar = CustomProgressBar()
        self.progress_bar.set_task("No task running.")
        
        self.viewlayout.addLayout(self.main_grid, stretch=20)
        self.viewlayout.addWidget(self.progress_bar, stretch=1)
        
        self.split_layout = QGridLayout()
        self.rename_layout = QGridLayout()
        self.explore_layout = QGridLayout()
        self.merge_layout = QGridLayout()
        self.main_grid.addLayout(self.split_layout, 0, 0)
        self.main_grid.addLayout(self.rename_layout, 1, 0)
        self.main_grid.addLayout(self.explore_layout, 0, 1)
        self.main_grid.addLayout(self.merge_layout, 1, 1)
        
        self.manage_split_layout()
        self.manage_rename_layout()
        self.manage_explore_layout()
        self.manage_merge_layout()
        
    def manage_split_layout(self):
        split_title = TitleLabel(parent=self, text="SPLIT DATASET", section='title1')
        split_load_btn = QPushButton(parent=self, text="Load full_dataset",)
        split_load_edit = QLineEdit(parent=self)
        split_load_edit.setEnabled(False)
        split_ratio_label = QLabel(parent=self, text="Train/Test split Ratio: 0.7")
        split_ratio_slider = QSlider(parent=self)
        # slider range and config
        split_ratio_slider.setMinimum(0)
        split_ratio_slider.setMaximum(100)
        split_ratio_slider.setTickInterval(10)
        split_ratio_slider.setValue(70)  # Representing 0.7
        split_ratio_slider.setOrientation(Qt.Orientation.Horizontal)
        split_target_column_label = QLabel(parent=self, text="Target column:")
        split_target_column_cbbox = QComboBox(parent=self)
        split_target_column_cbbox.view().setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        split_method_label = QLabel(parent=self, text="Split method:")
        split_method_cbbox = QComboBox(parent=self)
        split_method_cbbox.addItems(["Standard Split", "StratifiedShuffleSplit"])
        split_btn = QPushButton(parent=self, text="Split")
        
        self.split_layout.addWidget(split_title, 0, 0)
        self.split_layout.addWidget(split_load_btn, 1, 0)
        self.split_layout.addWidget(split_load_edit, 1, 1)
        self.split_layout.addWidget(split_ratio_label, 2, 0)
        self.split_layout.addWidget(split_ratio_slider, 2, 1)
        self.split_layout.addWidget(split_target_column_label, 3, 0)
        self.split_layout.addWidget(split_target_column_cbbox, 3, 1)
        self.split_layout.addWidget(split_btn, 4, 1)
        self.split_layout.addWidget(split_method_label, 4, 0)
        self.split_layout.addWidget(split_method_cbbox, 4, 1)
        self.split_layout.addWidget(split_btn, 5, 1)
        
        # --- CONNECT
        split_load_btn.clicked.connect(lambda: self.controller.load_dataset("split_load_edit", "split_target_column_cbbox"))
        split_ratio_slider.valueChanged.connect(
            lambda val: split_ratio_label.setText(f"Train/Test split Ratio: {val / 100:.2f}")
        )
        split_btn.clicked.connect(self.controller.split_dataset)
        
        # --- STORE WIDGETS
        names = [(split_load_btn, "split_load_btn"), (split_load_edit, "split_load_edit"),
                 (split_ratio_slider, "split_ratio_slider"), (split_target_column_cbbox, "split_target_column_cbbox"),(split_method_cbbox, "split_method_cbbox")]
        for widget, name in names:
            self.widgets[name] = widget
            
    def manage_rename_layout(self):
        rename_title = TitleLabel(parent=self, text="RENAME TARGETS", section='title1')
        rename_load_btn = QPushButton(parent=self, text="Load full_dataset",)
        rename_load_edit = QLineEdit(parent=self)
        rename_load_edit.setEnabled(False)
        rename_target_column_label = QLabel(parent=self, text="Target column:")
        rename_target_column_cbbox = QComboBox(parent=self)
        rename_target_column_cbbox.view().setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        rename_tableedit = TableEditor(parent=self, headers=["Original", "Renamed"])
        rename_save_btn = QPushButton(parent=self, text="Save full_dataset under",)
        rename_save_edit = QLineEdit(parent=self)
        rename_save_edit.setEnabled(False)
        rename_btn = QPushButton(parent=self, text="Rename")
        
        self.rename_layout.addWidget(rename_title, 0, 0)
        self.rename_layout.addWidget(rename_load_btn, 1, 0)
        self.rename_layout.addWidget(rename_load_edit, 1, 1)
        self.rename_layout.addWidget(rename_target_column_label, 2, 0)
        self.rename_layout.addWidget(rename_target_column_cbbox, 2, 1)
        self.rename_layout.addWidget(rename_tableedit, 3, 0, 1, 2)
        self.rename_layout.addWidget(rename_save_btn, 4, 0)
        self.rename_layout.addWidget(rename_save_edit, 4, 1)
        self.rename_layout.addWidget(rename_btn, 5, 1)
        
        # ---- CONNECT
        rename_btn.clicked.connect(self.controller.rename_targets)
        rename_load_btn.clicked.connect(lambda: self.controller.load_dataset("rename_load_edit", "rename_target_column_cbbox"))
        rename_save_btn.clicked.connect(lambda: self.controller.save_dataset("rename_save_edit",))
        
        # ---- STORE WIDGETS
        
        names = [(rename_tableedit, "rename_tableedit"), (rename_load_edit, "rename_load_edit"),
                 (rename_save_edit, "rename_save_edit"), (rename_target_column_cbbox, "rename_target_column_cbbox")]
        for widget, name in names:
            self.widgets[name] = widget
            
    def manage_explore_layout(self):
        explore_title = TitleLabel(parent=self, text="EXPLORE DATASET", section='title1')
        
        explore_load_btn = QPushButton(parent=self, text="Load full_dataset", )
        explore_load_edit = QLineEdit(parent=self)
        explore_load_edit.setEnabled(False)
        
        explore_n_rows_label = QLabel(parent=self, text="Number of rows:")
        explore_n_cols_label = QLabel(parent=self, text="Number of columns:")
        
        explore_target_column_label = QLabel(parent=self, text="Column to check:")
        explore_target_column_cbbox = QComboBox(parent=self)
        explore_target_column_cbbox.view().setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        explore_check_cols_btn = QPushButton(parent=self, text="Check column unique values")
        explore_column_label = QLabel(parent=self, text="Unique values:")

        explore_column_cbbox = QComboBox(parent=self)
        explore_column_cbbox.view().setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # ---- LAYOUT
        self.explore_layout.addWidget(explore_title, 0, 0)
        self.explore_layout.addWidget(explore_load_btn, 1, 0)
        self.explore_layout.addWidget(explore_load_edit, 1, 1)
        self.explore_layout.addWidget(explore_n_rows_label, 2, 0)
        self.explore_layout.addWidget(explore_n_cols_label, 3, 0)
        self.explore_layout.addWidget(explore_target_column_label, 4, 0)
        self.explore_layout.addWidget(explore_target_column_cbbox, 4, 1)
        self.explore_layout.addWidget(explore_check_cols_btn, 5, 0)
        self.explore_layout.addWidget(explore_column_label, 6, 0)
        self.explore_layout.addWidget(explore_column_cbbox, 6, 1)

        
        # ---- CONNECT
        explore_load_btn.clicked.connect(self.controller.load_and_explore_dataset)
        explore_check_cols_btn.clicked.connect(self.controller.explore_column)
        
        # ---- STORE WIDGETS
        names = [(explore_load_edit, "explore_load_edit"), (explore_n_rows_label, "explore_n_rows_label"),
                 (explore_n_cols_label, "explore_n_cols_label"), (explore_target_column_cbbox, "explore_target_column_cbbox"),
                 (explore_column_label, "explore_column_label"), (explore_column_cbbox, "explore_column_cbbox")]
        for widget, name in names:
            self.widgets[name] = widget
            
    def manage_merge_layout(self):
        merge_title_label = TitleLabel(parent=self, text="MERGE DATASETS", section='title1')
        merge_load_first_btn = QPushButton(parent=self, text="Load first full_dataset", )
        merge_load_first_edit = QLineEdit(parent=self)
        merge_load_first_edit.setEnabled(False)
        merge_load_second_btn = QPushButton(parent=self, text="Load second full_dataset", )
        merge_load_second_edit = QLineEdit(parent=self)
        merge_load_second_edit.setEnabled(False)
        merge_save_btn = QPushButton(parent=self, text="Save merged full_dataset as", )
        merge_save_edit = QLineEdit(parent=self)
        merge_save_edit.setEnabled(False)
        merge_btn = QPushButton(parent=self, text="Merge datasets", )
        
        # --- LAYOUT
        self.merge_layout.addWidget(merge_title_label, 0, 0)
        self.merge_layout.addWidget(merge_load_first_btn, 1, 0)
        self.merge_layout.addWidget(merge_load_first_edit, 1, 1)
        self.merge_layout.addWidget(merge_load_second_btn, 2, 0)
        self.merge_layout.addWidget(merge_load_second_edit, 2, 1)
        self.merge_layout.addWidget(merge_save_btn, 3, 0)
        self.merge_layout.addWidget(merge_save_edit, 3, 1)
        self.merge_layout.addWidget(merge_btn, 4, 1)
        
        #----- STORE WIDGETS
        names = [(merge_load_first_edit, "merge_load_first_edit"), (merge_load_second_edit, "merge_load_second_edit"),
                 (merge_save_edit, "merge_save_edit"), ]
        for widget, name in names:
            self.widgets[name] = widget
        
        # ---- CONNECT
        merge_load_first_btn.clicked.connect(lambda: self.controller.load_merge_datasets("merge_load_first_edit", mode='getOpenFileName'))
        merge_load_second_btn.clicked.connect(lambda: self.controller.load_merge_datasets("merge_load_second_edit", mode='getOpenFileName'))
        merge_save_btn.clicked.connect(lambda: self.controller.load_merge_datasets("merge_save_edit", mode='getSaveFileName',
                                                                                   extension='.csv'))
        merge_btn.clicked.connect(self.controller.merge_datasets)