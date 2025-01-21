import matplotlib as mpl
from PySide6.QtWidgets import QApplication

from phroc.gui import MainWindow


mpl.use("Qt5Agg")
app = QApplication([])
window = MainWindow()
window.show()
app.exec()
