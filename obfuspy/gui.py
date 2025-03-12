from PySide6.QtWidgets import *
from PySide6.QtCore import Qt


class ObfLayer:
    def __init__(self, name: str, settings: dict):
        self.name = name
        self.settings = settings

    def __str__(self):
        settings = ','.join(f"{k}={v}" for k, v in self.settings.items())
        settings = f" ({settings})" if settings else ""
        return f"{self.name}{settings}"

    def __repr__(self):
        return str(self)

    def copy(self):
        return ObfLayer(self.name, self.settings.copy())


class DragDropList(QListWidget):
    def __init__(self):
        super().__init__()
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #171717;
                border-radius: 4px;
                outline: none;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #171717;
                outline: none;
            }
            QListWidget::item:selected {
                background-color: #3498DB;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #323232;
            }
            QListWidget::item:selected:hover {
                background-color: #2980B9;
                color: #FFFFFF;
            }
            QListWidget:focus {
                outline: none;  /* Remove focus outline when widget has focus */
            }+
            QScrollBar:vertical {
                border: none;
                background: #2b2b2b;
                width: 8px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #404040;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #505050;
            }
            QScrollBar::add-line:vertical {
                height: 0px;
            }
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

    def get_items_order(self) -> list:
        return [self.item(i) for i in range(self.count())]


class DragDropWindow(QWidget):
    """
    Most likely an error occured if this text is visible within the description.
    """

    def __init__(self, obfuscation_layers: dict):
        super().__init__()
        self.obfuscation_layers = obfuscation_layers
        self.setWindowTitle("obfuspy - Silas A. Kraume")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("background-color: #202020;")

        main_layout = QHBoxLayout(self)

        left_panel = QVBoxLayout()
        self.list_widget = DragDropList()
        left_panel.addWidget(self.list_widget)
        left_panel.addLayout(self.add_button_layout())

        right_panel = QVBoxLayout()
        settings_group = QGroupBox()
        settings_group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 1px solid #171717;
                border-radius: 4px;
                margin-top: 0;
                padding-top: 10px;
            }
        """)
        self.add_settings_layout(settings_group)
        right_panel.addWidget(settings_group)
        right_panel.addStretch()

        main_layout.addLayout(left_panel, stretch=2)
        main_layout.addLayout(right_panel, stretch=1)

        steps = ["Step 1: Start", "Step 2: Process", "Step 3: Verify", "Step 4: Finish"]
        for step in steps:
            layer = ObfLayer(step, {"key": "value"})
            item = QListWidgetItem(str(layer))
            item.setData(Qt.UserRole, layer)
            self.list_widget.addItem(item)

    def add_button_layout(self) -> QHBoxLayout:
        button_layout = QHBoxLayout()

        add_button = QPushButton("Duplicate Layer")
        add_button.clicked.connect(self.duplicate_selected)
        add_button.setStyleSheet("""
            QPushButton {
                background-color: #00ff00;
                color: #202020;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #15e304;
            }
        """)
        remove_button = QPushButton("Remove Layer")
        remove_button.clicked.connect(self.remove_selected)
        remove_button.setStyleSheet("""
            QPushButton {
                background-color: #e74856;
                color: #202020;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
        """)
        import_button = QPushButton("Import")
        import_button.clicked.connect(self.print_order)
        import_button.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: #202020;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
        """)
        export_button = QPushButton("Export")
        export_button.clicked.connect(self.print_order)
        export_button.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: #202020;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
        """)

        button_layout.addWidget(add_button)
        button_layout.addWidget(remove_button)
        button_layout.addWidget(import_button)
        button_layout.addWidget(export_button)

        return button_layout

    def add_settings_layout(self, settings_group: QGroupBox) -> QVBoxLayout:
        label_style = """
            QLabel {
                color: white;
                padding-left: 2px;  /* Add left padding to labels */
            }
        """
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setContentsMargins(10, 10, 10, 10)

        layer_label = QLabel("Layer:")
        layer_label.setStyleSheet(label_style)
        settings_layout.addWidget(layer_label)
        self.method_combo = QComboBox()
        self.method_combo.addItems(self.obfuscation_layers.keys())
        self.method_combo.currentTextChanged.connect(self.on_layer_changed)
        self.method_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: white;
                padding: 5px;
                border: 1px solid #171717;
                border-radius: 4px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #171717;
                margin-right: 5px;
            }
        """)
        settings_layout.addWidget(self.method_combo)

        description_label = QLabel("Description:")
        description_label.setStyleSheet(label_style)
        settings_layout.addWidget(description_label)
        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setMaximumHeight(100)
        self.description_text.setStyleSheet("""
            QTextEdit {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #171717;
                border-radius: 4px;
            }
        """)
        settings_layout.addWidget(self.description_text)

        self.optional_widgets = {}
        denominator_label = QLabel("Denominator:")
        denominator_label.setStyleSheet(label_style)
        denominator_spin = QSpinBox()
        denominator_spin.setRange(2, 100)
        denominator_spin.setValue(6)
        denominator_spin.setStyleSheet("""
            QSpinBox {
                background-color: #2b2b2b;
                color: white;
                padding: 5px;
                border: 1px solid #171717;
                border-radius: 4px;
            }
        """)
        self.optional_widgets['Numerical Constants'] = (denominator_label, denominator_spin)

        anti_debug_label = QLabel("Anti-Debug Statement Probability")
        anti_debug_label.setStyleSheet(label_style)
        anti_debug_spin = QDoubleSpinBox()
        anti_debug_spin.setRange(0.0, 1.0)
        anti_debug_spin.setValue(0.2)
        anti_debug_spin.setSingleStep(0.01)
        anti_debug_spin.setDecimals(2)
        anti_debug_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #2b2b2b;
                color: white;
                padding: 5px;
                border: 1px solid #171717;
                border-radius: 4px;
            }
        """)
        self.optional_widgets['Anti-Debug Statements'] = (anti_debug_label, anti_debug_spin)

        dead_code_label = QLabel("Dead Code Probability")
        dead_code_label.setStyleSheet(label_style)
        dead_code_spin = QDoubleSpinBox()
        dead_code_spin.setRange(0.0, 1.0)
        dead_code_spin.setValue(0.2)
        dead_code_spin.setSingleStep(0.01)
        dead_code_spin.setDecimals(2)
        dead_code_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #2b2b2b;
                color: white;
                padding: 5px;
                border: 1px solid #171717;
                border-radius: 4px;
            }
        """)
        self.optional_widgets['Dead Code'] = (dead_code_label, dead_code_spin)

        for label, *widgets in self.optional_widgets.values():
            settings_layout.addWidget(label)
            for widget in widgets:
                settings_layout.addWidget(widget)
        self.on_layer_changed()

        action_button = QPushButton("Add Layer")
        action_button.clicked.connect(self.add_new_step)
        action_button.setStyleSheet("""
            QPushButton {
                background-color: #00ff00;
                color: #202020;
                padding: 8px 20px;
                border-radius: 4px;
                margin: 0 2px;
            }
            QPushButton:hover {
                background-color: #15e304;
            }
        """)
        settings_layout.addWidget(action_button)

        return settings_layout

    def on_layer_changed(self):
        def clean_doc_text(text):
            text = text.replace('\t', '')
            while '\n  ' in text:
                text = text.replace('\n  ', '\n ')
            return f" {text.strip()}"
        layer_name = self.method_combo.currentText()
        for label, *widgets in self.optional_widgets.values():
            label.hide()
            for widget in widgets:
                widget.hide()
        if layer_name in self.optional_widgets:
            label, *widgets = self.optional_widgets[layer_name]
            label.show()
            for widget in widgets:
                widget.show()
        self.description_text.setText(clean_doc_text(self.obfuscation_layers.get(layer_name, self).__doc__))

    def add_new_step(self):
        def clean_label_text(text):
            return ''.join(c if c.isalpha() else '_' for c in text.rstrip(':').lower())
        current_item = self.method_combo.currentText()
        additional_data = {}
        if current_item in self.optional_widgets:
            label, *widgets = self.optional_widgets[current_item]
            for widget in widgets:
                if isinstance(widget,(QSpinBox, QDoubleSpinBox)):
                    additional_data[clean_label_text(label.text())] = widget.value()
                else:
                    print("Unknown widget type", type(widget))
        layer = ObfLayer(current_item, additional_data)
        item = QListWidgetItem(str(layer))
        item.setData(Qt.UserRole, layer)
        self.list_widget.addItem(item)

    def duplicate_selected(self):
        current_item = self.list_widget.selectedItems()
        if current_item:
            layer: ObfLayer = current_item[0].data(Qt.UserRole)
            new_layer = layer.copy()
            item = QListWidgetItem(str(new_layer))
            item.setData(Qt.UserRole, new_layer)
            self.list_widget.insertItem(
                self.list_widget.row(current_item[0])+1,
                item
            )

    def remove_selected(self):
        current_item = self.list_widget.selectedItems()
        if current_item:
            self.list_widget.takeItem(self.list_widget.row(current_item[0]))

    def print_order(self):
        current_order = self.list_widget.get_items_order()
        print("Current order of steps:")
        for i, step in enumerate(current_order, 1):
            print(f"{i}. {step.data(Qt.UserRole)}")



class GUI:
    def __init__(self, obfuscation_layers: dict):
        self.app = QApplication([])
        self.window = DragDropWindow(obfuscation_layers)

    def run(self):
        self.window.show()
        self.app.exec()
        return {
            "layers": [l.data(Qt.UserRole) for l in self.window.list_widget.get_items_order()],
            "comments": True,
            "indentation": '    ',
        }

if __name__ == "__main__":
    GUI()
