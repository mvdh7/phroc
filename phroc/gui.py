from sys import argv

import matplotlib as mpl
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from . import meta
from .process.read import read_excel, read_phroc
from .process.usd import UpdatingSummaryDataset


LightRed = QColor(255, 71, 76)
LightOrange = QColor(253, 170, 72)


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
        self.setWindowTitle("pHroc v{}".format(meta.__version__))
        # === SAMPLES TAB ==============================================================
        # Buttons to import and export results file
        s_button_initialise = QPushButton("Import results file")
        s_button_initialise.released.connect(self.import_dataset_and_initialise)
        self.s_button_find_windows = QPushButton(
            "Automatically detect measurement windows"
        )
        self.file_loaded = False
        self.s_button_export_phroc = QPushButton("Export to .phroc")
        self.s_button_export_excel = QPushButton("Export to .xlsx")
        # Text giving name of currently imported file
        self.s_current_file = QLabel("Current file: none")
        # Table with one-per-sample information
        self.s_table_samples = QTableWidget()
        s_table_samples_ncols = 10
        self.s_table_samples.setColumnCount(s_table_samples_ncols)
        self.s_table_samples.setHorizontalHeaderLabels(
            [
                "Sample name",
                "Tris?",
                "Extra\nmCP?",
                "Salinity",
                "Temperature\n/ °C",
                "pH",
                "pH\nrange",
                "Expected\npH",
                "Measurements\n(used / total)",
                "Comments",
            ]
        )
        self.s_col_sample_name = 0
        self.s_col_is_tris = 1
        self.s_col_extra_mcp = 2
        self.s_col_salinity = 3
        self.s_col_temperature = 4
        self.s_col_pH = 5
        self.s_col_pH_spread = 6
        self.s_col_pH_expected = 7
        self.s_col_measurements = 8
        self.s_col_comments = 9
        self.s_cols = {
            self.s_col_sample_name: "sample_name",
            self.s_col_is_tris: "is_tris",
            self.s_col_extra_mcp: "extra_mcp",
            self.s_col_salinity: "salinity",
            self.s_col_temperature: "temperature",
            self.s_col_comments: "comments",
        }
        header = self.s_table_samples.horizontalHeader()
        for c in range(s_table_samples_ncols):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self.s_table_samples_U = None
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
        self.m_comments = QLineEdit("")
        self.m_comments.textEdited.connect(self.m_edit_comments)
        self.m_table_measurements = QTableWidget()
        self.m_table_measurements.setColumnCount(1)
        self.m_table_measurements.setHorizontalHeaderLabels(["pH"])
        # Previous / next sample buttons
        self.m_button_first = QPushButton("⇐ First sample")
        self.m_button_final = QPushButton("Final sample ⇒")
        self.m_button_prev = QPushButton("← Previous sample")
        self.m_button_next = QPushButton("Next sample →")
        # Move measurements button
        self.m_button_first_to_prev = QPushButton(
            "Move first measurement to previous sample"
        )
        self.m_button_last_to_next = QPushButton("Move last measurement to next sample")
        # Split measurements
        self.m_button_split = QPushButton("Split sample at measurement number ")
        self.m_combo_split = QComboBox()
        self.m_combo_split.addItem("-")
        # === ASSEMBLE LAYOUT ==========================================================
        # - Samples table column
        l_samples_table = QVBoxLayout()
        l_samples_table.addWidget(s_button_initialise)
        l_samples_table.addWidget(self.s_button_find_windows)
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
        # MEASUREMENTS TAB
        # - Measurements tab central column
        l_measurements_central = QVBoxLayout()
        # --- Figure
        l_measurements_central.addWidget(self.m_fig_measurements_nav)
        l_measurements_central.addWidget(self.m_fig_measurements)
        # --- Two-column info section
        # ----- Left column
        l_measurements_info_left = QVBoxLayout()
        l_measurements_info_left.addWidget(self.m_sample_name)
        l_measurements_info_left.addWidget(self.m_sample_pH)
        w_measurements_info_left = QWidget()
        w_measurements_info_left.setLayout(l_measurements_info_left)
        # ----- Right column
        l_measurements_info_right = QVBoxLayout()
        l_measurements_info_right.addWidget(self.m_sample_salinity)
        l_measurements_info_right.addWidget(self.m_sample_temperature)
        w_measurements_info_right = QWidget()
        w_measurements_info_right.setLayout(l_measurements_info_right)
        # ----- Combine columns
        l_measurements_info = QHBoxLayout()
        l_measurements_info.addWidget(w_measurements_info_left)
        l_measurements_info.addWidget(w_measurements_info_right)
        w_measurements_info = QWidget()
        w_measurements_info.setLayout(l_measurements_info)
        l_measurements_central.addWidget(w_measurements_info)
        # --- Comments box
        l_m_comments_header = QHBoxLayout()
        l_m_comments_header.addWidget(QLabel("Comments:"))
        l_m_comments_header.addWidget(self.m_comments)
        w_m_comments_header = QWidget()
        w_m_comments_header.setLayout(l_m_comments_header)
        l_measurements_central.addWidget(w_m_comments_header)
        # --- Buttons below info section
        l_measurements_central.addWidget(self.m_button_first_to_prev)
        l_measurements_central.addWidget(self.m_table_measurements)
        l_measurements_central.addWidget(self.m_button_last_to_next)
        l_measurements_split = QHBoxLayout()
        l_measurements_split.addWidget(self.m_button_split)
        l_measurements_split.addWidget(self.m_combo_split)
        w_measurements_split = QWidget()
        w_measurements_split.setLayout(l_measurements_split)
        l_measurements_central.addWidget(w_measurements_split)
        w_measurements_central = QWidget()
        w_measurements_central.setLayout(l_measurements_central)
        # - Measurements tab left column
        l_m_left = QVBoxLayout()
        l_m_left.addStretch()
        l_m_left.addWidget(self.m_button_first)
        l_m_left.addWidget(self.m_button_prev)
        l_m_left.addStretch()
        w_m_left = QWidget()
        w_m_left.setLayout(l_m_left)
        # - Measurements tab right column
        l_m_right = QVBoxLayout()
        l_m_right.addStretch()
        l_m_right.addWidget(self.m_button_final)
        l_m_right.addWidget(self.m_button_next)
        l_m_right.addStretch()
        w_m_right = QWidget()
        w_m_right.setLayout(l_m_right)
        # - Assemble measurements tab
        l_measurements = QHBoxLayout()
        l_measurements.addStretch()
        l_measurements.addWidget(w_m_left)
        l_measurements.addWidget(w_measurements_central)
        l_measurements.addWidget(w_m_right)
        l_measurements.addStretch()
        w_measurements = QWidget()
        w_measurements.setLayout(l_measurements)
        # Assemble tabs
        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.West)
        tabs.addTab(w_samples, "Samples")
        tabs.addTab(w_measurements, "Measurements")
        tabs.currentChanged.connect(self.change_tab)
        self.setCentralWidget(tabs)
        # If provided on command line, import file
        if len(argv) > 1:
            self.filename = argv[1]
            self._import_dataset_and_initialise()

    def change_tab(self, index):
        if index == 0:
            self.s_create_table_samples()
            self.s_plot_samples()
        elif index == 1:
            self.m_refresh_table_measurements()
            self.m_plot_measurements()

    def m_edit_comments(self, text):
        self.usd.set_sample(self.m_which_sample, comments=text)

    def auto_find_windows(self):
        self.usd.find_windows(cutoff=0.001, minimum_values=3)
        self.s_create_table_samples()
        self.s_plot_samples()
        # self.s_table_samples.item(0, 0).setBackground(QBrush)

    def initialise(self):
        # Set up samples tab
        self.s_create_table_samples()
        self.s_plot_samples()
        self.s_button_export_phroc.released.connect(self.export_phroc)
        self.s_button_export_excel.released.connect(self.export_excel)
        self.s_button_find_windows.released.connect(self.auto_find_windows)
        # Set up measurements tab
        self.m_which_sample = 1
        if not self.file_loaded:
            self.m_create_table_measurements()
            self.m_button_split.released.connect(self.m_split)
            self.m_button_prev.released.connect(self.m_to_sample_prev)
            self.m_button_next.released.connect(self.m_to_sample_next)
            self.m_button_first.released.connect(self.m_to_sample_first)
            self.m_button_final.released.connect(self.m_to_sample_final)
            self.m_button_first_to_prev.released.connect(self.m_first_to_prev)
            self.m_button_last_to_next.released.connect(self.m_last_to_next)
        else:
            self.m_refresh_table_measurements()

    def _import_dataset_and_initialise(self):
        if self.filename.lower().endswith(".txt"):
            self.usd = UpdatingSummaryDataset(self.filename)
        elif self.filename.lower().endswith(".phroc"):
            self.usd = read_phroc(self.filename)
        elif self.filename.lower().endswith(".xlsx"):
            self.usd = read_excel(self.filename)
        self.initialise()
        self.file_loaded = True

    def import_dataset_and_initialise(self):
        # Open file dialog for user to choose the results file from the instrument
        dialog_open = QFileDialog(
            self, filter="Potentially compatible files (*.txt *.phroc *.xlsx)"
        )
        dialog_open.setFileMode(QFileDialog.FileMode.ExistingFile)
        if dialog_open.exec():
            self.filename = dialog_open.selectedFiles()[0]
            self._import_dataset_and_initialise()

    def s_create_table_samples(self):
        self.s_current_file.setText("Current file: {}".format(self.filename))
        if self.s_table_samples_U is not None:
            self.s_table_samples.cellChanged.disconnect(self.s_table_samples_U)
        self.s_table_samples.clearContents()
        self.s_table_samples.setRowCount(self.usd.samples.shape[0])
        # Loop through samples and set values in GUI table
        for s, sample in self.usd.samples.iterrows():
            r = s - 1
            self.s_set_all_cells(r, sample)
        self.s_table_samples_U = self.s_table_samples.cellChanged.connect(
            self.s_update_table_samples
        )

    def s_set_all_cells(self, r, sample):
        self.s_set_cell_sample_name(r, sample)
        self.s_set_cell_is_tris(r, sample)
        self.s_set_cell_extra_mcp(r, sample)
        self.s_set_cell_salinity(r, sample)
        self.s_set_cell_temperature(r, sample)
        self.s_set_cell_pH(r, sample)
        self.s_set_cell_pH_spread(r, sample)
        self.s_set_cell_pH_expected(r, sample)
        self.s_set_cell_measurements(r, sample)
        self.s_set_cell_comments(r, sample)

    def s_set_cell_sample_name(self, r, sample):
        cell_sample_name = QTableWidgetItem(sample.sample_name)
        self.s_table_samples.setItem(r, self.s_col_sample_name, cell_sample_name)

    def s_set_cell_is_tris(self, r, sample):
        cell_is_tris = QTableWidgetItem()
        cell_is_tris.setFlags(cell_is_tris.flags() & ~Qt.ItemIsEditable)
        if sample.is_tris:
            cell_is_tris.setCheckState(Qt.Checked)
        else:
            cell_is_tris.setCheckState(Qt.Unchecked)
        self.s_table_samples.setItem(r, self.s_col_is_tris, cell_is_tris)

    def s_set_cell_extra_mcp(self, r, sample):
        cell_extra_mcp = QTableWidgetItem()
        cell_extra_mcp.setFlags(cell_extra_mcp.flags() & ~Qt.ItemIsEditable)
        if sample.extra_mcp:
            cell_extra_mcp.setCheckState(Qt.Checked)
        else:
            cell_extra_mcp.setCheckState(Qt.Unchecked)
        self.s_table_samples.setItem(r, self.s_col_extra_mcp, cell_extra_mcp)

    def s_set_cell_salinity(self, r, sample):
        cell_salinity = QTableWidgetItem(str(sample.salinity))
        cell_salinity.setTextAlignment(Qt.AlignCenter)
        if sample.salinity < 0:
            cell_salinity.setBackground(LightRed)
        self.s_table_samples.setItem(r, self.s_col_salinity, cell_salinity)

    def s_set_cell_temperature(self, r, sample):
        cell_temperature = QTableWidgetItem(str(sample.temperature))
        cell_temperature.setTextAlignment(Qt.AlignCenter)
        self.s_table_samples.setItem(r, self.s_col_temperature, cell_temperature)

    def s_set_cell_pH(self, r, sample):
        cell_pH = QTableWidgetItem("{:.4f}".format(sample.pH))
        cell_pH.setFlags(cell_pH.flags() & ~Qt.ItemIsEditable)
        self.s_table_samples.setItem(r, self.s_col_pH, cell_pH)

    def s_set_cell_pH_spread(self, r, sample):
        cell_pH_spread = QTableWidgetItem("{:.4f}".format(sample.pH_range))
        cell_pH_spread.setFlags(cell_pH_spread.flags() & ~Qt.ItemIsEditable)
        if sample.pH_range > 0.001:
            cell_pH_spread.setBackground(LightOrange)
        if sample.pH_range > 0.0012:
            cell_pH_spread.setBackground(LightRed)
        self.s_table_samples.setItem(r, self.s_col_pH_spread, cell_pH_spread)

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
        if sample.pH_good < 3:
            cell_measurements.setBackground(LightOrange)
        if sample.pH_good < 1:
            cell_measurements.setBackground(LightRed)
        cell_measurements.setFlags(cell_measurements.flags() & ~Qt.ItemIsEditable)
        cell_measurements.setTextAlignment(Qt.AlignCenter)
        self.s_table_samples.setItem(r, self.s_col_measurements, cell_measurements)

    def s_set_cell_comments(self, r, sample):
        cell_comments = QTableWidgetItem(sample.comments)
        self.s_table_samples.setItem(r, self.s_col_comments, cell_comments)

    def s_plot_samples(self):
        samples = self.usd.samples
        measurements = self.usd.measurements
        ax = self.s_fig_samples.ax[0]
        ax.cla()
        ax.scatter(samples.index, samples.pH, s=50, c="xkcd:pale purple")
        ax.scatter(
            samples.index,
            samples.pH_tris_expected,
            marker="+",
            s=50,
            c="xkcd:dark purple",
        )
        ax.scatter(
            measurements.xpos[measurements.pH_good],
            measurements.pH[measurements.pH_good],
            s=10,
            c="xkcd:dark",
            alpha=0.8,
            edgecolor="none",
        )
        ax.scatter(
            measurements.xpos[~measurements.pH_good],
            measurements.pH[~measurements.pH_good],
            s=10,
            c="xkcd:dark",
            alpha=0.8,
            marker="x",
        )
        ax.set_ylabel("pH (total scale)")
        ax.set_xticks(samples.index)
        ax.set_xticklabels(samples.sample_name, rotation=-90)
        ax.tick_params(top=True, labeltop=True, bottom=True, labelbottom=False)
        ax = self.s_fig_samples.ax[1]
        ax.cla()
        ax.scatter(samples.index, samples.salinity, s=50, c="xkcd:sage")
        ax.set_ylabel("Salinity")
        ax.set_xticks(samples.index)
        ax.tick_params(top=True, labeltop=False, bottom=True, labelbottom=False)
        ax = self.s_fig_samples.ax[2]
        ax.cla()
        ax.scatter(samples.index, samples.temperature, c="xkcd:coral")
        ax.set_ylabel("Temperature / °C")
        ax.set_xticks(samples.index)
        ax.set_xticklabels(samples.sample_name, rotation=-90)
        ax.tick_params(top=True, labeltop=False, bottom=True, labelbottom=True)
        for ax in self.s_fig_samples.ax:
            ax.grid(alpha=0.2)
        self.s_fig_samples.fig.tight_layout()
        self.s_fig_samples.draw()

    def s_update_table_samples(self, r, c):
        # === UPDATE SELF.USD ==========================================================
        v = self.s_table_samples.item(r, c).data(0)  # the updated value
        s = r + 1  # the index for the corresponding row of self.samples
        col = self.s_cols[c]  # the column name in self.usd.samples
        # Update the dataset
        if col in ["salinity", "temperature"]:
            try:
                v = float(v)
            except ValueError:
                # Don't allow temperature and salinity to be changed to non-numbers
                v = self.usd.samples.loc[s, col]
        elif col in ["is_tris", "extra_mcp"]:
            v = self.s_table_samples.item(r, c).checkState() == Qt.Checked
        self.usd.set_sample(s, **{col: v})
        # === UPDATE GUI SAMPLES TABLE & PLOT ==========================================
        self.s_create_table_samples()
        self.s_plot_samples()

    def m_create_table_measurements(self):
        s = self.m_which_sample
        sample = self.usd.samples.loc[s]
        M = self.usd.measurements.order_analysis == s
        self.m_sample_name.setText(
            "Sample {} of {}: {}".format(
                s, self.usd.samples.shape[0], sample.sample_name
            )
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
        self.m_comments.setText(sample.comments)
        self.m_table_measurements.clearContents()
        self.m_table_measurements.setRowCount(sample.pH_count)
        # Loop through measurements and set values in GUI table
        for r, (m, measurement) in enumerate(self.usd.measurements.loc[M].iterrows()):
            self.m_set_cell_pH(r, measurement)
        self.m_table_measurements_U = self.m_table_measurements.cellChanged.connect(
            self.m_update_table_measurements
        )
        self.m_plot_measurements()
        # Update splitting box contents
        self.m_combo_split.clear()
        self.m_combo_split.addItem("-")
        combo_list = [str(_m) for _m in range(2, M.sum() + 1)]
        self.m_combo_split.addItems(combo_list)

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
        M = self.usd.measurements.order_analysis == s
        m = self.usd.measurements[M].index[r]
        self.usd.set_measurement(
            m, pH_good=(self.m_table_measurements.item(r, c).checkState() == Qt.Checked)
        )
        self.m_refresh_table_measurements()

    def m_refresh_table_measurements(self):
        # First, we have to disconnect the cellChanged signal to prevent recursion
        self.m_table_measurements.cellChanged.disconnect(self.m_table_measurements_U)
        self.m_create_table_measurements()

    def m_plot_measurements(self):
        sample = self.usd.samples.loc[self.m_which_sample]
        measurements = self.usd.measurements
        ax = self.m_fig_measurements.ax
        ax.cla()
        M = measurements.order_analysis == self.m_which_sample
        Mg = M & measurements.pH_good
        Mb = M & ~measurements.pH_good
        fx = 1 + np.arange(M.sum())
        L = measurements.pH_good[M].values
        ax.scatter(fx[L], measurements[Mg].pH)
        ax.scatter(fx[~L], measurements[Mb].pH, marker="x")
        ax.axhline(sample.pH)
        if sample.is_tris:
            ax.axhline(sample.pH_tris_expected, ls=":")
        ax.set_xticks(fx)
        # Make sure y-axis range is always at least 0.002
        ylim = ax.get_ylim()
        ydiff = ylim[1] - ylim[0]
        if ydiff < 0.002:
            sdiff = measurements[M].pH.max() - measurements[M].pH.min()
            yextra = (0.002 - sdiff) / 2
            ylim = (
                measurements[M].pH.min() - yextra,
                measurements[M].pH.max() + yextra,
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
            self.m_which_sample = self.usd.samples.shape[0]
        self.m_refresh_table_measurements()

    def m_to_sample_first(self):
        self.m_which_sample = 1
        self.m_refresh_table_measurements()

    def m_to_sample_final(self):
        self.m_which_sample = self.usd.samples.shape[0]
        self.m_refresh_table_measurements()

    def m_to_sample_next(self):
        self.m_which_sample += 1
        if self.m_which_sample > self.usd.samples.shape[0]:
            self.m_which_sample = 1
        self.m_refresh_table_measurements()

    def m_move_measurement(self, direction):
        # Direction is -1 to move measurement backwards or +1 for forwards
        assert direction in [-1, 1]
        s = self.m_which_sample
        s_new = s + direction
        # Only do anything if we're not already on the first (-1) or last (+1) sample
        if direction == -1:
            neither_first_nor_last = s_new > 0
            m_ix = 0  # the iloc in the subset of the measurements table to move (first)
        elif direction == 1:
            neither_first_nor_last = s_new < self.usd.samples.shape[0]
            m_ix = -1  # the iloc in the subset of the measurements table to move (last)
        if neither_first_nor_last:
            M = self.usd.measurements.order_analysis == s
            m = self.usd.measurements[M].index[m_ix]  # the measurement to move
            # Move the sample by renaming
            self.usd.set_measurement(
                m, sample_name=self.usd.samples.sample_name.loc[s_new]
            )
            self.m_refresh_table_measurements()

    def m_first_to_prev(self):
        self.m_move_measurement(-1)

    def m_last_to_next(self):
        self.m_move_measurement(1)

    def m_split(self):
        split_at = self.m_combo_split.currentText()
        if split_at != "-":
            split_at = int(split_at)
            print("Let's move measurement {} onwards to a new sample!".format(split_at))
            s = self.m_which_sample
            M = self.usd.measurements.order_analysis == s
            Mn = self.usd.measurements[M].index[(split_at - 1) :]  # the new sample
            # Update by renaming - note that if the following sample already ends with
            # "__SPLIT" then the new split will just add data to that next sample,
            # instead of making a new one - but I think that's not really a problem
            sample_name_new = self.usd.samples.sample_name.loc[s] + "__SPLIT"
            self.usd.set_measurements(Mn, sample_name=sample_name_new)
            self.m_which_sample += 1
            self.m_refresh_table_measurements()

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
            self.usd.to_phroc(filename)

    def export_excel(self):
        dialog_save = self.export_prep("xlsx")
        if dialog_save.exec():
            filename = dialog_save.selectedFiles()[0]
            self.usd.to_excel(filename)
