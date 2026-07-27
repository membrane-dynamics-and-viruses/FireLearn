import logging
import sys
from datetime import datetime

from PyQt6.QtCore import Qt, QThread
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import QApplication, QSplashScreen, QMessageBox

from QtScripts import params
from QtScripts.CONTROLLER.MainController import MainController
from QtScripts.params import resource_path

logger = logging.getLogger(__name__)
import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

class App(QApplication):
    def __init__(self):
        super().__init__([])
        # Application title and version
        self.setApplicationName(f"FireLearn GUI v{params.version}")
        self.threads = {}
        
        # Record loading start time
        loading_time_start = datetime.now()

        # Setup splash screen
        pixmap = QPixmap(resource_path('data/firelearn_img/logo firelearn no text.png'))
        pixmap = pixmap.scaledToWidth(400, Qt.TransformationMode.FastTransformation)
        splash = QSplashScreen(pixmap)
        splash.show()
        self.processEvents()  # Ensure splash is displayed

        # Initialize main view
        self.controller = MainController(self,)
        self.controller.view.about_to_close.connect(self.onClosure)
        
        self.main_window = self.controller.view
        self.main_window.setWindowTitle("FireLearn GUI")
        icon = QIcon(pixmap)
        self.main_window.setWindowIcon(icon)

        # Finish splash
        splash.finish(self.main_window)
        splash.deleteLater()

        # Log loading time
        loading_time_end = datetime.now()
        logger.info(f"Loading time: {loading_time_end - loading_time_start}")

        # Show main window
        self.main_window.show()

        # Track usage start
        global usage_start_time
        usage_start_time = datetime.now()

        # Connect close event
        # self.aboutToQuit.connect(self.onClosure)
    def closeEvent(self, event):
        self.onClosure(event)
        
    def onClosure(self, event):
        alive_threads = [name for name in self.threads.keys() if self.threads[name].isRunning()]
        if len(alive_threads) > 0:
            reply = QMessageBox.question(
                self.main_window,
                "Processes still running",
                f"There are still unfinished processes. Do you still wish to close the software ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                # # TODO : terminate processes
                # for name, thread in self.threads.items():
                #     if thread.isRunning():
                #         thread.stop()
                #         thread.wait()
                #
                # usage_end_time = datetime.now()
                # logger.info(f"Usage time: {usage_end_time - usage_start_time}")
                # logger.info("Closing app and cleaning...")
                start_closing = datetime.now()
                #
                # # Clean up plots
                # from matplotlib import pyplot as plt
                # plt.close('all')
                #
                end_closing = datetime.now()
                # event.accept()
                logger.info(f"Closing time: {end_closing - start_closing}")
                sys.exit()
                
            else:
                event.ignore()
        else:
            event.accept()
    
    def add_thread(self, name, thread: QThread):
        self.threads[name] = thread

def load_stylesheet(path):
    with open(resource_path(path), "r") as f:
        return f.read()

def main():
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    app = App()
    app.setStyleSheet(load_stylesheet("data/qtTheme.qss"))
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
