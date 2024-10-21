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
    QHeaderView,
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
        s_button_initialise = QPushButton("Import results files from instrument")
        s_button_initialise.released.connect(self.import_dataset_and_initialise)
        self.s_button_export_phroc = QPushButton("Export to .phroc")
        self.s_button_export_excel = QPushButton("Export to .xlsx")
        # Text giving name of currently imported file
        self.s_current_file = QLabel("Current file: none")
        # Table with one-per-sample information
        self.s_table_samples = QTableWidget()
        s_table_samples_ncols = 8
        self.s_table_samples.setColumnCount(s_table_samples_ncols)
        self.s_table_samples.setHorizontalHeaderLabels(
            [
                "Type",
                "Sample name",
                "Salinity",
                "Temperature\n/ °C",
                "pH",
                "SD(pH)",
                "Expected\npH",
                "Measurements\n(used / total)",
            ]
        )
        self.s_col_sample_type = 0
        self.s_col_sample_name = 1
        self.s_col_salinity = 2
        self.s_col_temperature = 3
        self.s_col_pH = 4
        self.s_col_pH_std = 5
        self.s_col_pH_expected = 6
        self.s_col_measurements = 7
        header = self.s_table_samples.horizontalHeader()
        for c in range(s_table_samples_ncols):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        # Plot of one-per-sample information
        self.s_fig_samples = MplCanvas(
            self, width=6, height=9, dpi=100, nrows=3, sharex=True
        )
        self.s_fig_samples_nav = NavigationToolbar2QT(self.s_fig_samples, self)
        # === MEASUREMENTS TAB =========================================================
        # Plot of the sample's data points
        self.m_fig_measurements = MplCanvas(self, width=6, dpi=100)
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
        # Previous / next sample buttons
        self.m_button_prev = QPushButton("← Previous sample")
        self.m_button_next = QPushButton("Next sample →")
        # Move measurements button
        self.m_button_first_to_prev = QPushButton(
            "Move first measurement to previous sample"
        )
        self.m_button_last_to_next = QPushButton("Move last measurement to next sample")
        # === ASSEMBLE LAYOUT ==========================================================
        # - Samples table column
        l_samples_table = QVBoxLayout()
        l_samples_table.addWidget(s_button_initialise)
        l_samples_table.addWidget(self.s_current_file)
        l_samples_table.addWidget(self.s_table_samples)
        l_samples_export = QHBoxLayout()
        l_samples_export.addWidget(self.s_button_export_phroc)
        l_samples_export.addWidget(self.s_button_export_excel)
        w_samples_export = QWidget()
        w_samples_export.setLayout(l_samples_export)
        l_samples_table.addWidget(w_samples_export)
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
        # - Measurements central column
        l_measurements_central = QVBoxLayout()
        l_measurements_central.addWidget(self.m_fig_measurements_nav)
        l_measurements_central.addWidget(self.m_fig_measurements)
        l_measurements_central.addWidget(self.m_sample_name)
        l_measurements_central.addWidget(self.m_sample_salinity)
        l_measurements_central.addWidget(self.m_sample_temperature)
        l_measurements_central.addWidget(self.m_sample_pH)
        l_measurements_central.addWidget(self.m_button_first_to_prev)
        l_measurements_central.addWidget(self.m_table_measurements)
        l_measurements_central.addWidget(self.m_button_last_to_next)
        w_measurements_central = QWidget()
        w_measurements_central.setLayout(l_measurements_central)
        # - Measurements tab
        l_measurements = QHBoxLayout()
        l_measurements.addStretch()
        l_measurements.addWidget(self.m_button_prev)
        l_measurements.addWidget(w_measurements_central)
        l_measurements.addWidget(self.m_button_next)
        l_measurements.addStretch()
        w_measurements = QWidget()
        w_measurements.setLayout(l_measurements)
        # Tabs
        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.West)
        tabs.addTab(w_samples, "Samples")
        tabs.addTab(w_measurements, "Measurements")
        self.setCentralWidget(tabs)

    def initialise(self):
        # Set up samples tab
        self.s_create_table_samples()
        self.s_plot_samples()
        self.s_button_export_phroc.released.connect(self.export_phroc)
        self.s_button_export_excel.released.connect(self.export_excel)
        # Set up measurements tab
        self.m_which_sample = 1
        self.m_create_table_measurements()
        self.m_button_prev.released.connect(self.m_to_sample_prev)
        self.m_button_next.released.connect(self.m_to_sample_next)
        self.m_button_first_to_prev.released.connect(self.m_first_to_prev)
        self.m_button_last_to_next.released.connect(self.m_last_to_next)

    def import_dataset_and_initialise(self):
        # Open file dialog for user to choose the results file from the instrument
        dialog_open = QFileDialog(
            self, filter="Potentially compatible files (*.txt *.phroc *.xlsx)"
        )
        dialog_open.setFileMode(QFileDialog.FileMode.ExistingFile)
        if dialog_open.exec():
            self.filename = dialog_open.selectedFiles()[0]
            print(self.filename)
            if self.filename.lower().endswith(".txt"):
                self.measurements, self.samples = (
                    funcs.read_measurements_create_samples(self.filename)
                )
            elif self.filename.lower().endswith(".phroc"):
                self.measurements, self.samples = funcs.read_phroc(self.filename)
            elif self.filename.lower().endswith(".xlsx"):
                self.measurements, self.samples = funcs.read_excel(self.filename)
            self.initialise()

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
            self.s_set_cell_measurements(r, sample)
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
        cell_salinity.setTextAlignment(Qt.AlignCenter)
        self.s_table_samples.setItem(r, self.s_col_salinity, cell_salinity)

    def s_set_cell_temperature(self, r, sample):
        cell_temperature = QTableWidgetItem(str(sample.temperature))
        cell_temperature.setTextAlignment(Qt.AlignCenter)
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

    def s_set_cell_measurements(self, r, sample):
        cell_measurements = QTableWidgetItem(
            "{} / {}".format(sample.pH_good, sample.pH_count)
        )
        cell_measurements.setFlags(cell_measurements.flags() & ~Qt.ItemIsEditable)
        cell_measurements.setTextAlignment(Qt.AlignCenter)
        self.s_table_samples.setItem(r, self.s_col_measurements, cell_measurements)

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

    def s_update_table_samples(self, r, c):
        # === UPDATE SELF.SAMPLES AND SELF.MEASUREMENTS ================================
        v = self.s_table_samples.item(r, c).data(0)  # the updated value
        s = r + 1  # the index for the corresponding row of self.samples
        M = self.measurements.order_analysis == s  # the corresponding measurements
        Mg = M & self.measurements.pH_good  # the corresponding good measurements
        # User has edited sample_type
        if c == self.s_col_sample_type:
            is_tris = v.upper() in ["TRIS", "T"]
            self.measurements.loc[M, "is_tris"] = is_tris
            self.samples.loc[s, "is_tris"] = is_tris
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
                self.measurements[M].abs578,
                self.measurements[M].abs434,
                self.measurements[M].abs730,
                temperature=self.samples.loc[s].temperature,
                salinity=self.samples.loc[s].salinity,
            )
            self.samples.loc[s, "pH"] = self.measurements[Mg].pH.mean()
            self.samples.loc[s, "pH_std"] = self.measurements[Mg].pH.std()
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
        # If salinity, temperature or pH were edited, update pH, pH_std and measurements
        if c in [self.s_col_salinity, self.s_col_temperature, self.s_col_pH]:
            self.s_set_cell_pH(r, sample)
            self.s_set_cell_pH_std(r, sample)
            self.s_set_cell_measurements(r, sample)
        # Re-connect the cellChanged signal
        self.s_table_samples_U = self.s_table_samples.cellChanged.connect(
            self.s_update_table_samples
        )
        # === UPDATE GUI MEASUREMENTS TAB ==============================================
        # But only if this update wasn't caused by a change in the measurements tab!
        if c != self.s_col_pH:  # this only happens if the change was prompted there
            self.m_refresh_table_measurements()
        # === UPDATE GUI SAMPLES PLOT ==================================================
        self.s_plot_samples()

    def m_create_table_measurements(self):
        s = self.m_which_sample
        sample = self.samples.loc[s]
        M = self.measurements.order_analysis == s
        self.m_sample_name.setText(
            "Sample: {} ({} of {})".format(sample.sample_name, s, self.samples.shape[0])
        )
        self.m_sample_salinity.setText("Salinity: {}".format(sample.salinity))
        self.m_sample_temperature.setText(
            "Temperature: {} °C".format(sample.temperature)
        )
        self.m_sample_pH.setText(
            "pH: {:.4f} ± {:.4f} ({} of {} used)".format(
                sample.pH, sample.pH_std, sample.pH_good, sample.pH_count
            )
        )
        self.m_table_measurements.clearContents()
        self.m_table_measurements.setRowCount(sample.pH_count)
        # Loop through measurements and set values in GUI table
        for r, (m, measurement) in enumerate(self.measurements.loc[M].iterrows()):
            self.m_set_cell_pH(r, measurement)
        self.m_table_measurements_U = self.m_table_measurements.cellChanged.connect(
            self.m_update_table_measurements
        )
        self.m_plot_measurements()

    def m_set_cell_pH(self, r, measurement):
        cell_pH = QTableWidgetItem("{:.4f}".format(measurement.pH))
        cell_pH.setFlags(cell_pH.flags() & ~Qt.ItemIsEditable)
        if measurement.pH_good:
            cell_pH.setCheckState(Qt.Checked)
        else:
            cell_pH.setCheckState(Qt.Unchecked)
        self.m_table_measurements.setItem(r, 0, cell_pH)

    def m_update_table_measurements(self, r, c):
        s = self.m_which_sample
        sample = self.samples.loc[s]
        M = self.measurements.order_analysis == s
        m = self.measurements[M].index[r]
        self.measurements.loc[m, "pH_good"] = (
            self.m_table_measurements.item(r, c).checkState() == Qt.Checked
        )
        Mg = M & self.measurements.pH_good
        self.samples.loc[s, "pH"] = self.measurements[Mg].pH.mean()
        self.samples.loc[s, "pH_std"] = self.measurements[Mg].pH.std()
        self.samples.loc[s, "pH_good"] = Mg.sum()
        self.m_refresh_table_measurements()
        self.s_update_table_samples(s - 1, self.s_col_pH)

    def m_refresh_table_measurements(self):
        # First, we have to disconnect the cellChanged signal to prevent recursion
        self.m_table_measurements.cellChanged.disconnect(self.m_table_measurements_U)
        self.m_create_table_measurements()

    def m_plot_measurements(self):
        sample = self.samples.loc[self.m_which_sample]
        ax = self.m_fig_measurements.ax
        ax.cla()
        M = self.measurements.order_analysis == self.m_which_sample
        Mg = M & self.measurements.pH_good
        Mb = M & ~self.measurements.pH_good
        fx = 1 + np.arange(M.sum())
        L = self.measurements.pH_good[M].values
        ax.scatter(fx[L], self.measurements[Mg].pH)
        ax.scatter(fx[~L], self.measurements[Mb].pH, marker="x")
        ax.axhline(sample.pH)
        ax.set_xticks(fx)
        # Make sure y-axis range is always at least 0.002
        ylim = ax.get_ylim()
        ydiff = ylim[1] - ylim[0]
        if ydiff < 0.002:
            sdiff = self.measurements[M].pH.max() - self.measurements[M].pH.min()
            yextra = (0.002 - sdiff) / 2
            ylim = (
                self.measurements[M].pH.min() - yextra,
                self.measurements[M].pH.max() + yextra,
            )
            ydiff = ylim[1] - ylim[0]
            ax.set_ylim(ylim)
        if ydiff <= 0.006:
            ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(base=0.0005))
            ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(base=0.0001))
            ax.grid(which="major", alpha=0.3)
            ax.grid(which="minor", axis="y", alpha=0.1)
        else:
            ax.grid(alpha=0.2)
        # Final settings
        ax.set_xlabel("Measurement number")
        ax.set_ylabel("pH (total scale)")
        self.m_fig_measurements.fig.tight_layout()
        self.m_fig_measurements.draw()

    def m_to_sample_prev(self):
        self.m_which_sample -= 1
        if self.m_which_sample < 1:
            self.m_which_sample = self.samples.shape[0]
        self.m_refresh_table_measurements()

    def m_to_sample_next(self):
        self.m_which_sample += 1
        if self.m_which_sample > self.samples.shape[0]:
            self.m_which_sample = 1
        self.m_refresh_table_measurements()

    def m_move_measurement(self, direction):
        # Direction is -1 to move measurement backwards or +1 for forwards
        assert direction in [-1, 1]
        s = self.m_which_sample
        s_new = s + direction
        # Only do anything if we're not already on the first (-1) or last (+1) sample
        if direction == -1:
            condition = s_new > 0
            m_ix = 0
        elif direction == 1:
            condition = s_new < self.samples.shape[0]
            m_ix = -1
        if condition:
            sample = self.samples.loc[s]
            M = self.measurements.order_analysis == s
            m = self.measurements[M].index[m_ix]
            # Move the sample
            self.measurements.loc[m, "sample_name"] = self.samples.loc[
                s_new
            ].sample_name
            original_order_analysis = self.measurements.loc[m, "order_analysis"]
            self.measurements.loc[m, "order_analysis"] += direction
            self.measurements.loc[m, "is_tris"] = self.measurements.loc[
                m + direction, "is_tris"
            ]
            # Update samples table etc. if this move does not completely remove a sample
            if M.sum() > 1:
                Mu = (  # the current sample (with now one fewer measurement)
                    self.measurements.sample_name == sample.sample_name
                )
                Mp = (  # the other sample (with now one extra measurement)
                    self.measurements.sample_name == self.samples.loc[s_new].sample_name
                )
                for _s, _M in zip((s, s_new), (Mu, Mp)):
                    self.samples.loc[_s, "pH"] = self.measurements[_M].pH.mean()
                    self.samples.loc[_s, "pH_std"] = self.measurements[_M].pH.std()
                    self.samples.loc[_s, "pH_count"] = _M.sum()
                    self.samples.loc[_s, "pH_good"] = (
                        _M & self.measurements.pH_good
                    ).sum()
                funcs.get_xpos(self.measurements, self.samples)
                self.s_update_table_samples(s - 1, self.s_col_pH)
                self.s_update_table_samples(s_new - 1, self.s_col_pH)
            else:  # if we have now completely removed this sample
                # Update order_analysis
                self.measurements.loc[
                    self.measurements.order_analysis > original_order_analysis,
                    "order_analysis",
                ] -= 1
                # Recompute samples table
                self.samples = funcs.get_samples_from_measurements(self.measurements)
                # Remove removed sample from GUI samples table and update adjusted row
                r = s - 1
                self.s_table_samples.removeRow(r)
                if direction == -1:
                    self.m_which_sample -= 1
                    self.s_update_table_samples(r - 1, self.s_col_pH)
                else:
                    self.s_update_table_samples(r, self.s_col_pH)
            self.m_refresh_table_measurements()

    def m_first_to_prev(self):
        self.m_move_measurement(-1)

    def m_last_to_next(self):
        self.m_move_measurement(1)

    def export_prep(self, extension):
        dialog_save = QFileDialog(self, filter="*.{}".format(extension))
        dialog_save.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog_save.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        export_dir = self.filename
        if export_dir.upper().endswith(".TXT"):
            export_dir = "{}.{}".format(export_dir[:-4], extension)
        dialog_save.setDirectory(export_dir)
        return dialog_save

    def export_phroc(self):
        dialog_save = self.export_prep("phroc")
        if dialog_save.exec():
            filename = dialog_save.selectedFiles()[0]
            funcs.write_phroc(filename, self.measurements, self.samples)

    def export_excel(self):
        dialog_save = self.export_prep("xlsx")
        if dialog_save.exec():
            filename = dialog_save.selectedFiles()[0]
            print(filename)
            funcs.write_excel(filename, self.measurements, self.samples)
