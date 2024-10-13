from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QMainWindow,
    QFileDialog,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QLabel,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
)
import koolstof as ks
import pandas as pd
import numpy as np
import matplotlib as mpl
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from . import funcs

mpl.use("Qt5Agg")

# TODO
# - allow identification of +20 samples (and other types?)
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
        # === SAMPLES TAB ==============================================================
        # Button to import results file
        s_button_initialise = QPushButton("Import results file")
        s_button_initialise.released.connect(self.import_dataset_and_initialise)
        # Text giving name of currently imported file
        self.s_current_file = QLabel("Current file: none")
        # Table with one-per-sample information
        self.s_table_samples = QTableWidget()
        self.s_table_samples.setColumnCount(7)
        self.s_table_samples.setHorizontalHeaderLabels(
            [
                "Type",
                "Sample name",
                "Salinity",
                "Temperature / °C",
                "pH",
                "SD(pH)",
                "Expected pH",
            ]
        )
        self.s_col_sample_type = 0
        self.s_col_sample_name = 1
        self.s_col_salinity = 2
        self.s_col_temperature = 3
        self.s_col_pH = 4
        self.s_col_pH_std = 5
        self.s_col_pH_expected = 6
        # Plot of one-per-sample information
        self.s_fig_samples = MplCanvas(
            self, width=6, height=9, dpi=100, nrows=3, sharex=True
        )
        self.s_fig_samples_nav = NavigationToolbar2QT(self.s_fig_samples, self)
        # === MEASUREMENTS TAB =========================================================
        # Plot of the sample's data points
        self.m_fig_measurements = MplCanvas(self, dpi=100)
        self.m_fig_measurements_nav = NavigationToolbar2QT(
            self.m_fig_measurements, self
        )
        # Data for the given sample
        self.m_sample_name = QLabel("Sample name")
        self.m_sample_salinity = QLabel("Salinity")
        self.m_sample_temperature = QLabel("Temperature / °C")
        self.m_sample_pH = QLabel("pH")
        self.m_table_measurements = QTableWidget()
        self.m_table_measurements.setColumnCount(1)
        self.m_table_measurements.setHorizontalHeaderLabels(["pH"])
        # === ASSEMBLE LAYOUT ==========================================================
        # - Samples table column
        l_samples_table = QVBoxLayout()
        l_samples_table.addWidget(s_button_initialise)
        l_samples_table.addWidget(self.s_current_file)
        l_samples_table.addWidget(self.s_table_samples)
        w_samples_table = QWidget()
        w_samples_table.setLayout(l_samples_table)
        # - Samples plot column
        l_samples_plot = QVBoxLayout()
        l_samples_plot.addWidget(self.s_fig_samples_nav)
        l_samples_plot.addWidget(self.s_fig_samples)
        w_samples_plot = QWidget()
        w_samples_plot.setLayout(l_samples_plot)
        # - Samples tab
        l_samples = QHBoxLayout()
        l_samples.addWidget(w_samples_table)
        l_samples.addWidget(w_samples_plot)
        w_samples = QWidget()
        w_samples.setLayout(l_samples)
        # - Measurements tab
        l_measurements = QVBoxLayout()
        l_measurements.addWidget(self.m_fig_measurements_nav)
        l_measurements.addWidget(self.m_fig_measurements)
        # TODO use layout.addStretch() and some QHBoxLayouts here for alignment
        l_measurements.addWidget(self.m_sample_name)
        l_measurements.addWidget(self.m_sample_salinity)
        l_measurements.addWidget(self.m_sample_temperature)
        l_measurements.addWidget(self.m_sample_pH)
        l_measurements.addWidget(self.m_table_measurements)
        w_measurements = QWidget()
        w_measurements.setLayout(l_measurements)
        # Tabs
        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.West)
        tabs.addTab(w_samples, "Samples")
        tabs.addTab(w_measurements, "Measurements")
        self.setCentralWidget(tabs)

    def import_dataset_and_initialise(self):
        # Open file dialog for user to choose the results file from the instrument
        dialog_open = QFileDialog(self, filter="*.txt")
        dialog_open.setFileMode(QFileDialog.FileMode.ExistingFile)
        if dialog_open.exec():
            self.filename = dialog_open.selectedFiles()[0]
            self.measurements, self.samples = funcs.read_measurements_create_samples(
                self.filename
            )
            # Set up samples tab
            self.s_create_table_samples()
            self.s_plot_samples()
            # Set up measurements tab
            self.m_which_sample = 1
            self.m_create_table_measurements()

    def s_create_table_samples(self):
        self.s_current_file.setText("Current file: {}".format(self.filename))
        self.s_table_samples.setRowCount(self.samples.shape[0])
        # Loop through samples and set values in GUI table
        for s, sample in self.samples.iterrows():
            r = s - 1
            self.s_set_cell_sample_type(r, sample)
            self.s_set_cell_sample_name(r, sample)
            self.s_set_cell_salinity(r, sample)
            self.s_set_cell_temperature(r, sample)
            self.s_set_cell_pH(r, sample)
            self.s_set_cell_pH_std(r, sample)
            self.s_set_cell_pH_expected(r, sample)
        self.s_table_samples_U = self.s_table_samples.cellChanged.connect(
            self.s_update_table_samples
        )

    def s_set_cell_sample_type(self, r, sample):
        if sample.is_tris:
            sample_type = "Tris"
        else:
            sample_type = "Sample"
        cell_sample_type = QTableWidgetItem(sample_type)
        self.s_table_samples.setItem(r, self.s_col_sample_type, cell_sample_type)

    def s_set_cell_sample_name(self, r, sample):
        cell_sample_name = QTableWidgetItem(sample.sample_name)
        self.s_table_samples.setItem(r, self.s_col_sample_name, cell_sample_name)

    def s_set_cell_salinity(self, r, sample):
        cell_salinity = QTableWidgetItem(str(sample.salinity))
        self.s_table_samples.setItem(r, self.s_col_salinity, cell_salinity)

    def s_set_cell_temperature(self, r, sample):
        cell_temperature = QTableWidgetItem(str(sample.temperature))
        self.s_table_samples.setItem(r, self.s_col_temperature, cell_temperature)

    def s_set_cell_pH(self, r, sample):
        cell_pH = QTableWidgetItem("{:.4f}".format(sample.pH))
        cell_pH.setFlags(cell_pH.flags() & ~Qt.ItemIsEditable)
        self.s_table_samples.setItem(r, self.s_col_pH, cell_pH)

    def s_set_cell_pH_std(self, r, sample):
        cell_pH_std = QTableWidgetItem("{:.4f}".format(sample.pH_std))
        cell_pH_std.setFlags(cell_pH_std.flags() & ~Qt.ItemIsEditable)
        self.s_table_samples.setItem(r, self.s_col_pH_std, cell_pH_std)

    def s_set_cell_pH_expected(self, r, sample):
        if sample.is_tris:
            pH_expected = "{:.4f}".format(sample.pH_tris_expected)
        else:
            pH_expected = ""
        cell_pH_expected = QTableWidgetItem(pH_expected)
        cell_pH_expected.setFlags(cell_pH_expected.flags() & ~Qt.ItemIsEditable)
        self.s_table_samples.setItem(r, self.s_col_pH_expected, cell_pH_expected)

    def s_plot_samples(self):
        ax = self.s_fig_samples.ax[0]
        ax.cla()
        ax.scatter(self.samples.index, self.samples.pH, s=50, c="xkcd:pale purple")
        ax.scatter(
            self.samples.index,
            self.samples.pH_tris_expected,
            marker="+",
            s=50,
            c="xkcd:dark purple",
        )
        ax.scatter(
            self.measurements.xpos[self.measurements.pH_good],
            self.measurements.pH[self.measurements.pH_good],
            s=10,
            c="xkcd:dark",
            alpha=0.8,
            edgecolor="none",
        )
        ax.scatter(
            self.measurements.xpos[~self.measurements.pH_good],
            self.measurements.pH[~self.measurements.pH_good],
            s=10,
            c="xkcd:dark",
            alpha=0.8,
            marker="x",
        )
        ax.set_ylabel("pH (total scale)")
        ax.set_xticks(self.samples.index)
        ax.set_xticklabels(self.samples.sample_name, rotation=-90)
        ax.tick_params(top=True, labeltop=True, bottom=True, labelbottom=False)
        ax = self.s_fig_samples.ax[1]
        ax.cla()
        ax.scatter(self.samples.index, self.samples.salinity, s=50, c="xkcd:sage")
        ax.set_ylabel("Salinity")
        ax.set_xticks(self.samples.index)
        ax.tick_params(top=True, labeltop=False, bottom=True, labelbottom=False)
        ax = self.s_fig_samples.ax[2]
        ax.cla()
        ax.scatter(self.samples.index, self.samples.temperature, c="xkcd:coral")
        ax.set_ylabel("Temperature / °C")
        ax.set_xticks(self.samples.index)
        ax.set_xticklabels(self.samples.sample_name, rotation=-90)
        ax.tick_params(top=True, labeltop=False, bottom=True, labelbottom=True)
        for ax in self.s_fig_samples.ax:
            ax.grid(alpha=0.2)
        self.s_fig_samples.fig.tight_layout()
        self.s_fig_samples.draw()

    def s_update_table_samples(self, r, c, v=None):
        # === UPDATE SELF.SAMPLES AND SELF.MEASUREMENTS ================================
        if v is None:
            # If triggered when user edits the samples table
            v = self.s_table_samples.item(r, c).data(0)  # the updated value
            # otherwise (e.g., user edited in measurements tab), v is provided as kwarg
        s = r + 1  # the index for the corresponding row of self.samples
        M = (
            self.measurements.sample_name == self.samples.loc[s].sample_name
        )  # the corresponding measurements
        # User has edited sample_type
        if c == self.s_col_sample_type:
            self.samples.loc[s, "is_tris"] = v.upper() in ["TRIS", "T"]
        # User has edited sample_name
        elif c == self.s_col_sample_name:
            self.measurements.loc[M, "sample_name"] = v
            self.samples.loc[s, "sample_name"] = v
            # self.update_sample_measurements()
        # User has edited salinity
        elif c == self.s_col_salinity:
            self.measurements.loc[M, "salinity"] = float(v)
            self.samples.loc[s, "salinity"] = float(v)
        # User has edited temperature
        elif c == self.s_col_temperature:
            self.measurements.loc[M, "temperature"] = float(v)
            self.samples.loc[s, "temperature"] = float(v)
        # If salinity or temperature were edited, recalculate pH
        if c in [self.s_col_salinity, self.s_col_temperature]:
            self.measurements.loc[M, "pH"] = ks.spectro.pH_NIOZ(
                self.measurements.loc[M].abs578,
                self.measurements.loc[M].abs434,
                self.measurements.loc[M].abs730,
                temperature=self.samples.loc[s].temperature,
                salinity=self.samples.loc[s].salinity,
            )
            self.samples.loc[s, "pH"] = self.measurements.loc[M].pH.mean()
            self.samples.loc[s, "pH_std"] = self.measurements.loc[M].pH.std()
        # If sample_type, temperature or salinity were edited, recalculate
        # pH_tris_expected
        if c in [self.s_col_sample_type, self.s_col_temperature, self.s_col_salinity]:
            if self.samples.loc[s, "is_tris"]:
                self.samples.loc[s, "pH_tris_expected"] = ks.pH_tris_DD98(
                    temperature=self.samples.loc[s].temperature,
                    salinity=self.samples.loc[s].salinity,
                )
            else:
                self.samples.loc[s, "pH_tris_expected"] = np.nan
        # === UPDATE GUI SAMPLES TABLE =================================================
        # Next, we have to disconnect the cellChanged signal to prevent recursion
        self.s_table_samples.cellChanged.disconnect(self.s_table_samples_U)
        sample = self.samples.loc[s]
        # If sample_type, temperature or salinity were edited, update sample_type and
        # pH_expected
        if c in [self.s_col_sample_type, self.s_col_temperature, self.s_col_salinity]:
            self.s_set_cell_sample_type(r, sample)
            self.s_set_cell_pH_expected(r, sample)
        # If salinity or temperature were edited, update pH and pH_std
        if c in [self.s_col_salinity, self.s_col_temperature]:
            self.s_set_cell_pH(r, sample)
            self.s_set_cell_pH_std(r, sample)
            # self.update_sample_measurements()
        # Re-connect the cellChanged signal
        self.s_table_samples_U = self.s_table_samples.cellChanged.connect(
            self.s_update_table_samples
        )
        # === UPDATE GUI SAMPLES PLOT ==================================================
        self.s_plot_samples()

    def m_create_table_measurements(self):
        s = self.m_which_sample
        sample = self.samples.loc[s]
        M = self.measurements.sample_name == sample.sample_name
        self.m_sample_name.setText("Sample: {}".format(sample.sample_name))
        self.m_sample_salinity.setText("Salinity: {}".format(sample.salinity))
        self.m_sample_temperature.setText(
            "Temperature: {} °C".format(sample.temperature)
        )
        self.m_sample_pH.setText("pH: {:.4f} ± {:.4f}".format(sample.pH, sample.pH_std))
        self.m_table_measurements.clearContents()
        self.m_table_measurements.setRowCount(sample.pH_count)
        # Loop through measurements and set values in GUI table
        for r, (m, measurement) in enumerate(self.measurements.loc[M].iterrows()):
            self.m_set_cell_pH(r, measurement)
        self.m_table_measurements_U = self.m_table_measurements.cellChanged.connect(
            self.m_edit_table_measurements
        )

    def m_set_cell_pH(self, r, measurement):
        cell_pH = QTableWidgetItem("{:.4f}".format(measurement.pH))
        cell_pH.setFlags(cell_pH.flags() & ~Qt.ItemIsEditable)
        if measurement.pH_good:
            cell_pH.setCheckState(Qt.Checked)
        else:
            cell_pH.setCheckState(Qt.Unchecked)
        self.m_table_measurements.setItem(r, 0, cell_pH)

    def m_edit_table_measurements(self, r, c):
        s = self.m_which_sample
        sample = self.samples.loc[s]
        M = self.measurements.sample_name == sample.sample_name
        m = self.measurements[M].index[r]
        self.measurements.loc[m, "pH_good"] = (
            self.m_table_measurements.item(r, c).checkState() == Qt.Checked
        )
        # TODO also update pH and pH_std in self.samples and then refresh samples tab
        self.m_update_table_measurements()

    def m_update_table_measurements(self):
        # First, we have to disconnect the cellChanged signal to prevent recursion
        self.m_table_measurements.cellChanged.disconnect(self.m_table_measurements_U)
        self.m_create_table_measurements()

    def plot_measurements(self):
        # TODO revise this with new style etc. and get it running / correctly signalled
        ax = self.m_fig_measurements.ax
        ax.cla()
        L = (
            self.measurements.sample_name
            == self.samples.loc[self.m_which_sample].sample_name
        )
        Lg = L & self.measurements.pH_good
        Lb = L & ~self.measurements.pH_good
        fx = 1 + np.arange(L.sum())
        Lx = self.measurements.pH_good[L].values
        ax.scatter(fx[Lx], self.measurements.pH[Lg])
        ax.scatter(fx[~Lx], self.measurements.pH[Lb], marker="x")
        ax.axhline(self.samples.loc[self.m_which_sample].pH)
        ax.set_xticks(fx)
        ax.grid(alpha=0.2)
        ax.set_xlabel("Measurement number")
        ax.set_ylabel("pH (total scale)")
        self.m_fig_measurements.fig.tight_layout()
        self.m_fig_measurements.draw()
