import sys
import logging
from PyQt6.QtWidgets import QApplication

from qwarp.engine import WarpEngine
from qwarp.state import WarpStateManager
from qwarp.ui import WarpWindow
from qwarp.tray import WarpTrayIcon

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    engine = WarpEngine()
    manager = WarpStateManager(engine)
    
    window = WarpWindow(manager)
    
    def toggle_window():
        if window.isVisible():
            window.hide()
        else:
            window.show()
            window.raise_()
            window.activateWindow()

    tray = WarpTrayIcon(manager, toggle_window)
    tray.show()
    
    logging.info("QWarp started successfully.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
