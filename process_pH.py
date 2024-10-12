from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
)
import koolstof as ks
import pandas as pd
import numpy as np
import matplotlib as mpl
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT

mpl.use("Qt5Agg")

# NEXT STEP:
# - plot temperature and salinity lines
# --- see https://www.pythonguis.com/tutorials/pyside-plotting-matplotlib/
# THEN:
# - allow identification of tris and +20 samples (and other types?)
# - add tab for looking at individual samples and selecting good points
# - results export
# - code generation / save state


class MplCanvas(FigureCanvasQTAgg):
    def __init__(
        self,
        parent=None,
        width=5,
        height=4,
        dpi=100,
        nrows=1,
        ncols=1,
        sharex=False,
        sharey=False,
    ):
        self.fig, self.ax = plt.subplots(
            figsize=(width, height),
            dpi=dpi,
            nrows=nrows,
            ncols=ncols,
            sharex=sharex,
            sharey=sharey,
        )
        super(MplCanvas, self).__init__(self.fig)


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
        # Plot of one-per-sample information
        self.fig_pH = MplCanvas(self, width=6, height=9, dpi=100, nrows=3, sharex=True)
        self.fig_pH_nav = NavigationToolbar2QT(self.fig_pH, self)
        # Assemble layout
        # - Samples table column
        ly_samples_table = QVBoxLayout()
        ly_samples_table.addWidget(button_openFile)
        ly_samples_table.addWidget(self.currently_open_file)
        ly_samples_table.addWidget(self.samples_table)
        w_samples_table = QWidget()
        w_samples_table.setLayout(ly_samples_table)
        # - Samples plot column
        ly_samples_plot = QVBoxLayout()
        ly_samples_plot.addWidget(self.fig_pH_nav)
        ly_samples_plot.addWidget(self.fig_pH)
        w_samples_plot = QWidget()
        w_samples_plot.setLayout(ly_samples_plot)
        # - Samples tab
        ly_samples = QHBoxLayout()
        ly_samples.addWidget(w_samples_table)
        ly_samples.addWidget(w_samples_plot)
        w_samples = QWidget()
        w_samples.setLayout(ly_samples)
        self.setCentralWidget(w_samples)

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
            def _get_samples(sample):
                return pd.Series(
                    {
                        "salinity": sample.salinity.mean(),
                        "temperature": sample.temperature.mean(),
                        "pH": sample.pH.mean(),
                        "pH_count": sample.pH.size,
                    }
                )

            self.samples = self.data.groupby("sample_name").apply(
                _get_samples, include_groups=False
            )
            self.samples["number"] = np.arange(self.samples.shape[0]).astype(float)
            self.data["number"] = self.samples.number[self.data.sample_name].values
            for s, row in self.samples.iterrows():
                L = self.data.sample_name == s
                self.data.loc[L, "number"] += (
                    0.5 + np.arange(row.pH_count) - row.pH_count / 2
                ) * 0.05
            self.samples["is_tris"] = self.samples.index.str.upper().str.startswith(
                "TRIS"
            )
            T = self.samples.is_tris
            self.samples["pH_tris_expected"] = ks.pH_tris_DD98(
                temperature=self.samples.temperature[T],
                salinity=self.samples.salinity[T],
            )
            # Populate filename and GUI samples table
            self.currently_open_file.setText("Current file: {}".format(filename[0]))
            self.samples_table.setRowCount(self.samples.shape[0])
            self.samples_table.setColumnCount(6)
            self.samples_table.setHorizontalHeaderLabels(
                [
                    "Type",
                    "Sample name",
                    "Salinity",
                    "Temperature / °C",
                    "pH (total)",
                    "pH expected",
                ]
            )
            for i, (sample, row) in enumerate(self.samples.iterrows()):
                if row.is_tris:
                    sample_type = "Tris"
                    pH_expected = "{:.4f}".format(row.pH_tris_expected)
                else:
                    sample_type = "Sample"
                    pH_expected = ""
                self.samples_table.setItem(i, 0, QTableWidgetItem(sample_type))
                self.samples_table.setItem(i, 1, QTableWidgetItem(sample))
                self.samples_table.setItem(i, 2, QTableWidgetItem(str(row.salinity)))
                self.samples_table.setItem(i, 3, QTableWidgetItem(str(row.temperature)))
                self.samples_table.setItem(
                    i, 4, QTableWidgetItem("{:.4f}".format(row.pH))
                )
                self.samples_table.setItem(i, 5, QTableWidgetItem(pH_expected))
            self.cx_table_updater = self.samples_table.cellChanged.connect(
                self.update_samples_table
            )
            # Draw plots
            self.plot_pH()

    def plot_pH(self):
        ax = self.fig_pH.ax[0]
        ax.cla()
        ax.scatter(self.samples.number, self.samples.pH, s=50, c="xkcd:pale purple")
        ax.scatter(
            self.samples.number,
            self.samples.pH_tris_expected,
            marker="+",
            s=50,
            c="xkcd:dark purple",
        )
        ax.scatter(
            self.data.number,
            self.data.pH,
            s=10,
            c="xkcd:dark",
            alpha=0.8,
            edgecolor="none",
        )
        ax.set_ylabel("pH (total scale)")
        ax.set_xticks(self.samples.number)
        ax.set_xticklabels(self.samples.index, rotation=-90)
        ax.tick_params(top=True, labeltop=True, bottom=True, labelbottom=False)
        ax = self.fig_pH.ax[1]
        ax.cla()
        ax.scatter(self.samples.number, self.samples.salinity, s=50, c="xkcd:sage")
        ax.set_ylabel("Salinity")
        ax.set_xticks(self.samples.number)
        ax.tick_params(top=True, labeltop=False, bottom=True, labelbottom=False)
        ax = self.fig_pH.ax[2]
        ax.cla()
        ax.scatter(self.samples.number, self.samples.temperature, c="xkcd:coral")
        ax.set_ylabel("Temperature / °C")
        ax.set_xticks(self.samples.number)
        ax.set_xticklabels(self.samples.index, rotation=-90)
        ax.tick_params(top=True, labeltop=False, bottom=True, labelbottom=True)
        for ax in self.fig_pH.ax:
            ax.grid(alpha=0.2)
        self.fig_pH.fig.tight_layout()
        self.fig_pH.draw()

    def update_samples_table(self, r, c):
        v = self.samples_table.item(r, c).data(0)
        L = self.data.sample_name == self.samples.index[r]
        ix = self.samples.index[r]
        if c == 0:  # edit sample type in samples
            self.samples.loc[ix, "is_tris"] = v.upper() in ["TRIS", "T"]
        if c == 1:  # edit sample name in data and samples
            self.data.loc[L, "sample_name"] = v
            self.samples.rename(index={ix: v}, inplace=True)
        elif c == 2:  # edit salinity in data and samples
            self.data.loc[L, "salinity"] = float(v)
            self.samples.loc[ix, "salinity"] = float(v)
        elif c == 3:  # edit temperature in data and samples
            self.data.loc[L, "temperature"] = float(v)
            self.samples.loc[ix, "temperature"] = float(v)
        if c in [2, 3]:  # if salinity or temperature edited, recalculate pH
            self.data.loc[L, "pH"] = ks.spectro.pH_NIOZ(
                self.data.loc[L, "abs578"],
                self.data.loc[L, "abs434"],
                self.data.loc[L, "abs730"],
                temperature=self.data.loc[L, "temperature"],
                salinity=self.data.loc[L, "salinity"],
            )
            self.samples.loc[ix, "pH"] = self.data.loc[L, "pH"].mean()
        if c in [0, 3]:  # if type or temperature edited, recalculate pH_tris_expected
            if self.samples.loc[ix, "is_tris"]:
                self.samples.loc[ix, "pH_tris_expected"] = ks.pH_tris_DD98(
                    temperature=self.samples.loc[ix, "temperature"],
                    salinity=self.samples.loc[ix, "salinity"],
                )
            else:
                self.samples.loc[ix, "pH_tris_expected"] = np.nan
        # We have to dis- & re-connect the cellChanged signal to prevent recursion
        self.samples_table.cellChanged.disconnect(self.cx_table_updater)
        if c in [
            0,
            3,
            5,
        ]:  # update sample type and pH_expected in GUI table if necessary
            if self.samples.loc[ix, "is_tris"]:
                sample_type = "Tris"
                pH_expected = "{:.4f}".format(self.samples.loc[ix].pH_tris_expected)
            else:
                sample_type = "Sample"
                pH_expected = ""
            self.samples_table.setItem(r, 0, QTableWidgetItem(sample_type))
            self.samples_table.setItem(r, 5, QTableWidgetItem(pH_expected))
        if c in [2, 3, 4]:  # update pH in GUI table if necessary
            self.samples_table.setItem(
                r, 4, QTableWidgetItem("{:.4f}".format(self.samples.loc[ix].pH))
            )
        # Re-connect here
        self.cx_table_updater = self.samples_table.cellChanged.connect(
            self.update_samples_table
        )
        # Update plots
        self.plot_pH()


app = QApplication([])
window = MainWindow()
window.show()
app.exec()
