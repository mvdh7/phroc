import matplotlib as mpl
from PySide6.QtWidgets import QApplication

import phroc


mpl.use("Qt5Agg")
app = QApplication([])
window = phroc.gui.MainWindow()
window.show()
app.exec()
