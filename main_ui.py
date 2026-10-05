import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
                             QVBoxLayout, QFormLayout, QLineEdit, QTableWidget,
                             QTableWidgetItem, QPushButton, QLabel, QComboBox,
                             QHeaderView, QAbstractItemView)
from PyQt5.QtGui import QFocusEvent
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import physics_engine as engine
from popup_output import OutputDialog


class AutoDeselectTableWidget(QTableWidget):
    """Custom QTableWidget that automatically clears selection when focus is lost."""

    def focusOutEvent(self, event: QFocusEvent):
        self.clearSelection()
        super().focusOutEvent(event)


class InteractiveCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(6, 4.2), dpi=100)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.parent_ui = parent

        self.shaft_length = 1000.0
        # Default loads structured with alternating ('a') and mean ('m') components
        self.loads = [
            {'x': 250.0, 'F_a': 250.0, 'F_m': 250.0, 'T_a': 10000.0,
                'T_m': 40000.0, 'M_a': 5000.0, 'M_m': 5000.0},
            {'x': 750.0, 'F_a': 400.0, 'F_m': 400.0, 'T_a': 20000.0,
                'T_m': 80000.0, 'M_a': 0.0, 'M_m': 0.0}
        ]
        self.support_left = "Pin"
        self.support_right = "Roller"

    def draw_support(self, x, s_type):
        if s_type == "Pin":
            self.ax.plot(x, -0.05, '^g', markersize=14)
            self.ax.plot([x - 35, x + 35], [-0.18, -0.18], 'k-', linewidth=2)
        elif s_type == "Roller":
            self.ax.plot(x, -0.05, 'og', markersize=12,
                         fillstyle='none', markeredgewidth=2)
            self.ax.plot([x - 35, x + 35], [-0.18, -0.18], 'k-', linewidth=2)
        elif s_type == "Fixed":
            self.ax.plot([x, x], [-0.4, 0.4], 'r-', linewidth=5)

    def redraw_shaft(self):
        self.ax.clear()

        # Main shaft body
        self.ax.plot([0, self.shaft_length], [0, 0],
                     color='gray', linewidth=10)

        # Draw supports
        self.draw_support(0, self.support_left)
        self.draw_support(self.shaft_length, self.support_right)

        # Sort loads by X position to calculate overlaps
        sorted_loads = sorted(enumerate(self.loads),
                              key=lambda item: item[1]['x'])

        # Render load markers and collision-aware annotations
        for idx_in_sorted, (orig_idx, load) in enumerate(sorted_loads):
            x = load['x']
            f_tot = load.get('F_a', 0) + load.get('F_m', 0)
            t_tot = load.get('T_a', 0) + load.get('T_m', 0)
            m_tot = load.get('M_a', 0) + load.get('M_m', 0)

            self.ax.plot(x, 0, 'ro', markersize=8)

            lbl = f"L{orig_idx+1}\nX:{x:.1f}\nF_peak:{f_tot:.1f}N\nT_peak:{t_tot:.1f}\nM_peak:{m_tot:.1f}"

            # Check proximity with preceding load to stagger vertically & horizontally
            stagger_y = 0.65
            offset_x = 0.0

            if idx_in_sorted > 0:
                prev_x = sorted_loads[idx_in_sorted - 1][1]['x']
                dist = abs(x - prev_x)
                if dist < 120.0:  # Threshold for close points
                    if idx_in_sorted % 2 != 0:
                        stagger_y = 1.30
                        offset_x = 20.0
                    else:
                        stagger_y = 0.65
                        offset_x = -20.0

            self.ax.annotate(
                lbl,
                xy=(x, 0.05),                         # Target point on shaft
                xytext=(x + offset_x, stagger_y),      # Callout text position
                ha='center',
                va='bottom',
                fontsize=7,
                bbox=dict(boxstyle="round,pad=0.3", fc="white",
                          ec="black", lw=0.8, alpha=0.9),
                arrowprops=dict(
                    arrowstyle='->',
                    color='red',
                    lw=1.2,
                    connectionstyle="arc3,rad=0.1"
                )
            )

        self.ax.set_xlim(-100, self.shaft_length + 100)
        # Upper range accommodates staggered boxes
        self.ax.set_ylim(-0.8, 2.2)
        self.ax.set_yticks([])
        self.ax.set_title(
            "Shaft Configuration & Applied Loads", fontsize=11, pad=8)
        self.ax.set_xlabel("X Position (mm)", fontsize=9, labelpad=5)

        self.fig.tight_layout(rect=[0, 0.05, 1, 1])
        self.draw()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ME 3104 - Power Transmission Shaft Designer")
        self.setGeometry(50, 50, 1350, 800)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # --- LEFT PANEL: Canvas & Load Table ---
        left_layout = QVBoxLayout()
        self.canvas = InteractiveCanvas(self)
        left_layout.addWidget(self.canvas)

        # Supports & Shaft Length
        supp_layout = QFormLayout()
        self.txt_length = QLineEdit("1000")
        self.cmb_left_supp = QComboBox()
        self.cmb_left_supp.addItems(["Pin", "Roller", "Fixed"])
        self.cmb_right_supp = QComboBox()
        self.cmb_right_supp.addItems(["Roller", "Pin", "Free"])

        self.txt_length.textChanged.connect(self.update_canvas_from_inputs)
        self.cmb_left_supp.currentIndexChanged.connect(
            self.update_canvas_from_inputs)
        self.cmb_right_supp.currentIndexChanged.connect(
            self.update_canvas_from_inputs)

        supp_layout.addRow("Shaft Length (mm):", self.txt_length)
        supp_layout.addRow("Left Support:", self.cmb_left_supp)
        supp_layout.addRow("Right Support:", self.cmb_right_supp)
        left_layout.addLayout(supp_layout)

        # Custom Auto-Deselect Load Table (Fluctuating parameters: Fa, Fm, Ta, Tm, Ma, Mm)
        left_layout.addWidget(
            QLabel("<b>Applied Fluctuating Loads & Moments Table:</b>"))
        self.load_table = AutoDeselectTableWidget()
        self.load_table.setColumnCount(7)
        self.load_table.setHorizontalHeaderLabels([
            "Pos X (mm)", "F_alt (N)", "F_mean (N)",
            "T_alt (N-mm)", "T_mean (N-mm)", "M_alt (N-mm)", "M_mean (N-mm)"
        ])
        self.load_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.load_table.itemChanged.connect(self.update_loads_from_table)

        btn_add_load = QPushButton("+ Add Load Point")
        btn_add_load.clicked.connect(self.add_load_row)
        btn_rem_load = QPushButton("- Remove Selected Load")
        btn_rem_load.clicked.connect(self.remove_load_row)

        btn_box = QHBoxLayout()
        btn_box.addWidget(btn_add_load)
        btn_box.addWidget(btn_rem_load)

        left_layout.addWidget(self.load_table)
        left_layout.addLayout(btn_box)

        main_layout.addLayout(left_layout, stretch=3)

        # --- RIGHT PANEL: DB, Factors, Constraints ---
        right_layout = QVBoxLayout()

        # Material Selection Table
        right_layout.addWidget(QLabel("<b>Standard Materials Database:</b>"))
        self.mat_table = QTableWidget()
        self.mat_table.setColumnCount(3)
        self.mat_table.setHorizontalHeaderLabels(
            ["Material", "Sut (MPa)", "Syt (MPa)"])
        self.mat_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.mat_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.mat_table.setSelectionMode(QAbstractItemView.SingleSelection)

        self.mat_table.setStyleSheet("""
            QTableWidget::item:selected {
                background-color: #505050;
                color: #ffffff;
            }
            QTableWidget::item:selected:!active {
                background-color: #505050;
                color: #ffffff;
            }
        """)

        self.populate_materials()
        right_layout.addWidget(self.mat_table)

        # Fatigue Factors Input
        right_layout.addWidget(
            QLabel("<b>Fatigue Factors (Customizable):</b>"))
        fatigue_form = QFormLayout()

        self.cmb_ka = QComboBox()
        self.cmb_ka.addItems(list(engine.SURFACE_FACTORS.keys()))
        self.txt_ka = QLineEdit("0.80")
        self.txt_ka.setMaximumWidth(80)

        ka_layout = QHBoxLayout()
        ka_layout.addWidget(self.cmb_ka)
        ka_layout.addWidget(self.txt_ka)

        self.cmb_kc = QComboBox()
        self.cmb_kc.addItems(list(engine.RELIABILITY_FACTORS.keys()))
        self.txt_kc = QLineEdit("0.897")
        self.txt_kc.setMaximumWidth(80)

        kc_layout = QHBoxLayout()
        kc_layout.addWidget(self.cmb_kc)
        kc_layout.addWidget(self.txt_kc)

        self.txt_kb = QLineEdit("0.85")
        self.txt_Kt = QLineEdit("1.50")
        self.txt_Kts = QLineEdit("1.30")
        self.txt_q = QLineEdit("0.80")
        self.txt_qs = QLineEdit("0.85")

        self.cmb_ka.currentIndexChanged.connect(self.toggle_ka_custom)
        self.cmb_kc.currentIndexChanged.connect(self.toggle_kc_custom)

        fatigue_form.addRow("Surface (ka):", ka_layout)
        fatigue_form.addRow("Reliability (kc):", kc_layout)
        fatigue_form.addRow("Size Factor (kb):", self.txt_kb)
        fatigue_form.addRow("Bending Conc. (Kt):", self.txt_Kt)
        fatigue_form.addRow("Torsion Conc. (Kts):", self.txt_Kts)
        fatigue_form.addRow("Bending Notch Sens. (q):", self.txt_q)
        fatigue_form.addRow("Torsion Notch Sens. (q_s):", self.txt_qs)
        right_layout.addLayout(fatigue_form)

        # Design Constraints
        right_layout.addWidget(QLabel("<b>Design Constraints:</b>"))
        constraint_form = QFormLayout()
        self.txt_fos = QLineEdit("2.0")
        self.txt_dmax = QLineEdit("50.0")
        self.txt_thetamax = QLineEdit("1.0")

        constraint_form.addRow("Factor of Safety (FoS):", self.txt_fos)
        constraint_form.addRow("Max Shaft Dia d_max (mm):", self.txt_dmax)
        constraint_form.addRow("Max Twist θ_max (deg):", self.txt_thetamax)
        right_layout.addLayout(constraint_form)

        btn_calc = QPushButton("Run Shaft Design Calculations")
        btn_calc.setStyleSheet(
            "background-color: #1565c0; color: white; font-weight: bold; padding: 10px;")
        btn_calc.clicked.connect(self.run_calculation)
        right_layout.addWidget(btn_calc)

        main_layout.addLayout(right_layout, stretch=2)

        self.populate_load_table()
        self.toggle_ka_custom()
        self.toggle_kc_custom()

    def populate_materials(self):
        self.mat_table.setRowCount(len(engine.MATERIALS_DB))
        for row, (mat_name, props) in enumerate(engine.MATERIALS_DB.items()):
            self.mat_table.setItem(row, 0, QTableWidgetItem(mat_name))
            self.mat_table.setItem(row, 1, QTableWidgetItem(str(props["Sut"])))
            self.mat_table.setItem(row, 2, QTableWidgetItem(str(props["Syt"])))
        self.mat_table.selectRow(0)

    def populate_load_table(self):
        self.load_table.blockSignals(True)
        self.load_table.setRowCount(len(self.canvas.loads))
        for r, load in enumerate(self.canvas.loads):
            self.load_table.setItem(r, 0, QTableWidgetItem(str(load['x'])))
            self.load_table.setItem(
                r, 1, QTableWidgetItem(str(load.get('F_a', 0.0))))
            self.load_table.setItem(
                r, 2, QTableWidgetItem(str(load.get('F_m', 0.0))))
            self.load_table.setItem(
                r, 3, QTableWidgetItem(str(load.get('T_a', 0.0))))
            self.load_table.setItem(
                r, 4, QTableWidgetItem(str(load.get('T_m', 0.0))))
            self.load_table.setItem(
                r, 5, QTableWidgetItem(str(load.get('M_a', 0.0))))
            self.load_table.setItem(
                r, 6, QTableWidgetItem(str(load.get('M_m', 0.0))))
        self.load_table.blockSignals(False)
        self.canvas.redraw_shaft()

    def add_load_row(self):
        self.canvas.loads.append({'x': 500.0, 'F_a': 500.0, 'F_m': 500.0,
                                 'T_a': 10000.0, 'T_m': 40000.0, 'M_a': 0.0, 'M_m': 0.0})
        self.populate_load_table()

    def remove_load_row(self):
        curr_row = self.load_table.currentRow()
        if curr_row >= 0 and len(self.canvas.loads) > 1:
            self.canvas.loads.pop(curr_row)
            self.populate_load_table()

    def update_loads_from_table(self):
        try:
            new_loads = []
            for r in range(self.load_table.rowCount()):
                x = float(self.load_table.item(r, 0).text())
                f_a = float(self.load_table.item(r, 1).text())
                f_m = float(self.load_table.item(r, 2).text())
                t_a = float(self.load_table.item(r, 3).text())
                t_m = float(self.load_table.item(r, 4).text())
                m_a = float(self.load_table.item(r, 5).text())
                m_m = float(self.load_table.item(r, 6).text())
                new_loads.append({
                    'x': x, 'F_a': f_a, 'F_m': f_m,
                    'T_a': t_a, 'T_m': t_m, 'M_a': m_a, 'M_m': m_m
                })
            self.canvas.loads = new_loads
            self.canvas.redraw_shaft()
        except (ValueError, AttributeError):
            pass

    def toggle_ka_custom(self):
        key = self.cmb_ka.currentText()
        if key == "Custom":
            self.txt_ka.setEnabled(True)
            self.txt_ka.setFocus()
        else:
            val = engine.SURFACE_FACTORS[key]
            self.txt_ka.setText(str(val))
            self.txt_ka.setEnabled(False)

    def toggle_kc_custom(self):
        key = self.cmb_kc.currentText()
        if key == "Custom":
            self.txt_kc.setEnabled(True)
            self.txt_kc.setFocus()
        else:
            val = engine.RELIABILITY_FACTORS[key]
            self.txt_kc.setText(str(val))
            self.txt_kc.setEnabled(False)

    def update_canvas_from_inputs(self):
        try:
            self.canvas.shaft_length = float(self.txt_length.text())
            self.canvas.support_left = self.cmb_left_supp.currentText()
            self.canvas.support_right = self.cmb_right_supp.currentText()
            self.canvas.redraw_shaft()
        except ValueError:
            pass

    def run_calculation(self):
        try:
            length = float(self.txt_length.text())
            fos = float(self.txt_fos.text())
            d_max = float(self.txt_dmax.text())
            theta_max = float(self.txt_thetamax.text())
            ka = float(self.txt_ka.text())
            kb = float(self.txt_kb.text())
            kc = float(self.txt_kc.text())
            Kt = float(self.txt_Kt.text())
            Kts = float(self.txt_Kts.text())
            q = float(self.txt_q.text())
            qs = float(self.txt_qs.text())

            selected_row = self.mat_table.currentRow()
            selected_mat = self.mat_table.item(
                selected_row if selected_row >= 0 else 0, 0).text()

            results = engine.compute_shaft_design(
                length, self.canvas.loads,
                self.cmb_left_supp.currentText(), self.cmb_right_supp.currentText(),
                fos, d_max, theta_max, selected_mat, ka, kb, kc, Kt, Kts, q, qs
            )

            dlg = OutputDialog(results, self)
            dlg.exec_()

        except ValueError as e:
            print("Calculation input error:", e)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
