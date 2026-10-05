from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox, QFormLayout, QGroupBox, QHBoxLayout


class OutputDialog(QDialog):
    def __init__(self, results: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Shaft Design Results & Summary")
        self.setMinimumWidth(450)

        main_layout = QVBoxLayout(self)

        # 1. Status Header
        status_label = QLabel()
        if results["success"]:
            status_label.setText(
                "<h3 style='color: green;'>✓ Design Constraints Satisfied</h3>")
        else:
            status_label.setText(
                "<h3 style='color: red;'>✗ Design Constraints Violated</h3>")
        main_layout.addWidget(status_label)

        # 2. Diameter & Deflection Summary
        dia_group = QGroupBox("Calculated Dimensions")
        dia_layout = QFormLayout()

        dia_layout.addRow("Calculated Diameter (d_calc):", QLabel(
            f"<b>{results['d_calculated']:.2f} mm</b>"))

        std_d_str = f"<b>{results['d_standard']} mm</b>" if results['d_standard'] else "<span style='color:red;'>None Available</span>"
        dia_layout.addRow("Selected Standard Diameter:", QLabel(std_d_str))

        dia_layout.addRow("Max Allowed Diameter:",
                          QLabel(f"{results['d_max']:.1f} mm"))
        dia_layout.addRow("Actual Angular Twist (θ_actual):",
                          QLabel(f"{results['actual_theta']:.4f}°"))
        dia_layout.addRow("Max Allowed Twist (θ_max):",
                          QLabel(f"{results['theta_max']:.2f}°"))

        dia_group.setLayout(dia_layout)
        main_layout.addWidget(dia_group)

        # 3. Static Reactions (Alternating & Mean)
        react_group = QGroupBox("Support Reactions (Fluctuating)")
        react_layout = QFormLayout()

        react_layout.addRow("R1 (Left Support):", QLabel(
            f"Alt: {results['R1_a']:.1f} N | Mean: {results['R1_m']:.1f} N"))
        react_layout.addRow("R2 (Right Support):", QLabel(
            f"Alt: {results['R2_a']:.1f} N | Mean: {results['R2_m']:.1f} N"))

        if results.get("T_R1_a", 0.0) != 0.0 or results.get("T_R1_m", 0.0) != 0.0:
            react_layout.addRow("T_R1 (Reaction Torque):", QLabel(
                f"Alt: {results['T_R1_a']:.1f} N-mm | Mean: {results['T_R1_m']:.1f} N-mm"))

        react_group.setLayout(react_layout)
        main_layout.addWidget(react_group)

        # 4. Critical Moments, Torques & Fatigue Parameters
        fatigue_group = QGroupBox("Critical Moments & Fatigue Parameters")
        fatigue_layout = QFormLayout()

        fatigue_layout.addRow("Bending Moment (M_a / M_m):",
                              QLabel(f"{results['M_a']:.1f} / {results['M_m']:.1f} N-mm"))
        fatigue_layout.addRow("Torsional Load (T_a / T_m):",
                              QLabel(f"{results['T_a']:.1f} / {results['T_m']:.1f} N-mm"))
        fatigue_layout.addRow("Endurance Limit (Se):",
                              QLabel(f"{results['Se']:.2f} MPa"))
        fatigue_layout.addRow("Bending Conc. Factor (Kf):",
                              QLabel(f"{results['Kf']:.3f}"))
        fatigue_layout.addRow("Shear Conc. Factor (Kfs):",
                              QLabel(f"{results['Kfs']:.3f}"))

        fatigue_group.setLayout(fatigue_layout)
        main_layout.addWidget(fatigue_group)

        # 5. OK Button
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        main_layout.addWidget(button_box)
