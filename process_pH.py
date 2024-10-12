from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
)
import koolstof as ks

# NEXT STEP:
# - plot temperature and salinity lines
# --- see https://www.pythonguis.com/tutorials/pyside-plotting-matplotlib/
# THEN:
# - allow identification of tris and +20 samples (and other types?)
# - add tab for looking at individual samples and selecting good points
# - results export
# - code generation / save state


class MainWindow(QMainWindow):
    def __init__(self):
        # Initialise
        super().__init__()
        self.setWindowTitle("Spectro pH processing")
        # Button to import results file
        button_openFile = QPushButton("Import results file")
        button_openFile.released.connect(self.open_file)
        # Text giving name of currently imported file
        self.currently_open_file = QLabel("Current file: none")
        # Table with one-per-sample information
        self.samples_table = QTableWidget()
        # Assemble layout
        layout = QVBoxLayout()
        layout.addWidget(button_openFile)
        layout.addWidget(self.currently_open_file)
        layout.addWidget(self.samples_table)
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def open_file(self):
        # Open file dialog
        dialog_open = QFileDialog(self, filter="*.txt")
        dialog_open.setFileMode(QFileDialog.FileMode.ExistingFile)
        if dialog_open.exec():
            filename = dialog_open.selectedFiles()
            # Import pH data file from instrument and recalculate pH
            self.data = ks.spectro.read_agilent_pH(filename[0])
            self.data["pH"] = ks.spectro.pH_NIOZ(
                self.data.abs578,
                self.data.abs434,
                self.data.abs730,
                temperature=self.data.temperature,
                salinity=self.data.salinity,
            )
            # Get one-per-sample table
            self.samples = (
                self.data[["sample_name", "salinity", "temperature", "pH"]]
                .groupby("sample_name")
                .mean()
            )
            # Populate filename and GUI samples table
            self.currently_open_file.setText("Current file: {}".format(filename[0]))
            self.samples_table.setRowCount(self.samples.shape[0])
            self.samples_table.setColumnCount(4)
            self.samples_table.setHorizontalHeaderLabels(
                ["Sample name", "Salinity", "Temperature / °C", "pH (total)"]
            )
            for i, (sample, row) in enumerate(self.samples.iterrows()):
                self.samples_table.setItem(i, 0, QTableWidgetItem(sample))
                self.samples_table.setItem(i, 1, QTableWidgetItem(str(row.salinity)))
                self.samples_table.setItem(i, 2, QTableWidgetItem(str(row.temperature)))
                self.samples_table.setItem(
                    i, 3, QTableWidgetItem("{:.4f}".format(row.pH))
                )
            self.cx_table_updater = self.samples_table.cellChanged.connect(
                self.update_samples_table
            )

    def update_samples_table(self, r, c):
        v = self.samples_table.item(r, c).data(0)
        L = self.data.sample_name == self.samples.index[r]
        ix = self.samples.index[r]
        if c == 0:  # edit sample name in data and samples
            self.data.loc[L, "sample_name"] = v
            self.samples.rename(index={ix: v}, inplace=True)
        elif c == 1:  # edit salinity in data and samples
            self.data.loc[L, "salinity"] = float(v)
            self.samples.loc[ix, "salinity"] = float(v)
        elif c == 2:  # edit temperature in data and samples
            self.data.loc[L, "temperature"] = float(v)
            self.samples.loc[ix, "temperature"] = float(v)
        if c in [1, 2]:  # if salinity or temperature edited, recalculate pH
            self.data.loc[L, "pH"] = ks.spectro.pH_NIOZ(
                self.data.loc[L, "abs578"],
                self.data.loc[L, "abs434"],
                self.data.loc[L, "abs730"],
                temperature=self.data.loc[L, "temperature"],
                salinity=self.data.loc[L, "salinity"],
            )
            self.samples.loc[ix, "pH"] = self.data.loc[L, "pH"].mean()
        if c in [1, 2, 3]:  # update pH in GUI table if necessary
            # We have to dis- & re-connect the cellChanged signal to prevent recursion
            self.samples_table.cellChanged.disconnect(self.cx_table_updater)
            self.samples_table.setItem(
                r, 3, QTableWidgetItem("{:.4f}".format(self.samples.loc[ix].pH))
            )
            self.cx_table_updater = self.samples_table.cellChanged.connect(
                self.update_samples_table
            )


app = QApplication([])
window = MainWindow()
window.show()
app.exec()
