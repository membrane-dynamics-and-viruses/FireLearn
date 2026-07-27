from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMainWindow, QApplication, QWidget, QVBoxLayout, QMenu, QTabWidget, QFrame, QSizePolicy

from QtScripts.WIDGETS.ChooseModelDialog import ChooseModelDialog


class MainView(QMainWindow):
    about_to_close = pyqtSignal(object)  # will emit the QCloseEvent
    
    def __init__(self, app: QApplication, controller):
        super().__init__()
        self.app = app
        self.controller = controller
        
        # Set initial window size and minimum constraints
        self.resize(1440, 900)
        self.setMinimumSize(800, 450)
        
        # Central widget and layout
        central_widget = QWidget()
        self.viewlayout = QVBoxLayout()
        # TODO: add your widgets here, e.g., buttons, plots, views
        # layout.addWidget(...)
        central_widget.setLayout(self.viewlayout)
        self.setCentralWidget(central_widget)
        
        # ------------------- MENU --------------------
        
        # Setup menus in MainView
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        open_cfg_menu = QMenu("Open configuration", self)
        save_cfg_menu = QMenu("Save configuration", self)
        
        # Load config submenu
        load_processing = QMenu("Processing", self)
        load_learning = QMenu("Learning", self)
        load_analysis = QMenu("Analysis", self)
        open_cfg_menu.addMenu(load_processing)
        open_cfg_menu.addMenu(load_learning)
        open_cfg_menu.addMenu(load_analysis)
        load_processing.addAction(self._action("Dataset processing (.pcfg)...", self.load_processing_config))
        load_processing.addAction(self._action("Spike detection (.pcfg)...", self.load_spike_config))
        load_learning.addAction(self._action("RFC (.rfcfg)...", self.load_rfc_config))
        load_learning.addAction(self._action("SVC (.svcfg)...", self.load_svc_config))
        for label, cmd in [
            ("Plot (.pltcfg)...", self.load_plot_config),
            ("Feature importance (.ficfg)...", self.load_importance_config),
            ("PCA (.pcacfg)...", self.load_pca_config),
            ("Confusion matrix (.confcfg)...", self.load_confusion_config),
        ]:
            load_analysis.addAction(self._action(label, cmd))
        
        # Save config submenu
        save_processing = QMenu("Processing", self)
        save_learning = QMenu("Learning", self)
        save_analysis = QMenu("Analysis", self)
        save_cfg_menu.addMenu(save_processing)
        save_cfg_menu.addMenu(save_learning)
        save_cfg_menu.addMenu(save_analysis)
        save_processing.addAction(self._action("Dataset processing (.pcfg)...", self.save_processing_config))
        save_processing.addAction(self._action("Spike detection (.skcfg)...", self.save_spike_config))
        save_learning.addAction(self._action("RFC (.rfcfg)...", self.save_rfc_config))
        save_learning.addAction(self._action("SVC (.svcfg)...", self.save_svc_config))
        for label, cmd in [
            ("Plot (.pltcfg)...", self.save_plot_config),
            ("Feature importance (.ficfg)...", self.save_importance_config),
            ("PCA (.pcacfg)...", self.save_pca_config),
            ("Confusion matrix (.confcfg)...", self.save_confusion_config),
            ("Spike detection (.skcfg)...", self.save_spike_config),
        ]:
            save_analysis.addAction(self._action(label, cmd))
        
        # Populate File menu
        file_menu.addMenu(open_cfg_menu)
        file_menu.addMenu(save_cfg_menu)
        file_menu.addSeparator()
        file_menu.addAction(self._action("Exit", self.close))
        
        # Help menu
        self.choose_model_dialog = None
        help_menu = menubar.addMenu("Machine Learning")
        help_menu.addAction(self._action("How to choose a model", self.show_choose_model_dialog))
        help_menu.setEnabled(False)
        
        # About menu
        about_menu = menubar.addMenu("About")
        about_menu.addAction(self._action("Github...", lambda: self.open_web(
            "https://github.com/WillyLutz/FireLearn-GUI")))
        about_menu.addAction(self._action("About Us", self.about_us))
        about_menu.addSeparator()
        
        
        # ---------------- TABS
        self.tabs = QTabWidget()
        self.learning_tab = QFrame()
        self.processing_tab = QFrame()
        self.analysis_tab = QFrame()
        self.tabs.addTab(self.processing_tab, "Processing")
        self.tabs.addTab(self.learning_tab, "Learning")
        self.tabs.addTab(self.analysis_tab, "Analysis")
        self.tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.viewlayout.addWidget(self.tabs)
        
    
    def _action(self, label, slot):
        action = QAction(label, self)
        action.triggered.connect(slot)
        return action
        
        # Placeholder methods for menu actions (implement these)
    
    def load_processing_config(self):
        self.controller.load_processing_config()
    
    def load_spike_config(self):
        self.controller.load_spike_config()
        
    def load_rfc_config(self):
        self.controller.load_rfc_config()
        
    def load_svc_config(self):
        self.controller.load_svc_config()
    
    def load_plot_config(self):
        pass
    
    def load_importance_config(self):
        pass
    
    def load_pca_config(self):
        pass
    
    def load_confusion_config(self):
        pass
    
    
    def save_processing_config(self):
        self.controller.save_processing_config()
        
    def save_spike_config(self):
        self.controller.save_spike_config()
        
    def save_rfc_config(self):
        self.controller.save_rfc_config()
    
    def save_svc_config(self):
        self.controller.save_svc_config()
    
    def save_plot_config(self):
        pass
    
    def save_importance_config(self):
        pass
    
    def save_pca_config(self):
        pass
    
    def save_confusion_config(self):
        pass
    
    def show_choose_model_dialog(self):
        self.choose_model_dialog = ChooseModelDialog(self)
        self.choose_model_dialog.show()
    
    def about_us(self):
        pass
    
    def open_web(self, url):
        import webbrowser; webbrowser.open(url)
    
    def closeEvent(self, event):
        # emit the event so others can handle it
        self.about_to_close.emit(event)
        # don't call super().closeEvent(event) here — let your handlers
        # decide whether to accept/ignore