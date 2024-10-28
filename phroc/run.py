import matplotlib as mpl
from PySide6.QtWidgets import QApplication
from . import gui


def phroc_run():
    mpl.use("Qt5Agg")
    app = QApplication([])
    window = gui.MainWindow()
    window.show()
    app.exec()
