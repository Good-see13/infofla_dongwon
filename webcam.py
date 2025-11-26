import os
import sys
import importlib.util

spec = importlib.util.find_spec("PySide6")
if spec and spec.origin:
    qt_dir = os.path.join(os.path.dirname(spec.origin), "Qt", "plugins")
    os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", qt_dir)
    os.environ.setdefault("QT_PLUGIN_PATH", qt_dir)

from PySide6 import QtWidgets

from src.core.config import API_SERVER_URL
from src.gui import AnalyzerWindow


def main():
    app = QtWidgets.QApplication(sys.argv)
    try:
        window = AnalyzerWindow(API_SERVER_URL)
    except RuntimeError as err:
        QtWidgets.QMessageBox.critical(None, "시작 실패", str(err))
        sys.exit(1)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
