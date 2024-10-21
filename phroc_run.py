import phroc
import matplotlib as mpl

mpl.use("Qt5Agg")
app = phroc.gui.QApplication([])
window = phroc.gui.MainWindow()
window.show()
app.exec()
