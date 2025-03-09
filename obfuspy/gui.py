from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QListWidget,
                              QListWidgetItem, QPushButton, QHBoxLayout, QInputDialog,
                              QComboBox, QLabel, QSpinBox, QGroupBox)


class DragDropList(QListWidget):
    """A QListWidget that supports drag-and-drop reordering."""
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
        return [self.item(i).text() for i in range(self.count())]


class DragDropWindow(QWidget):
    """Main application window."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("obfuspy - Silas A. Kraume")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("background-color: #202020;")

        # Main layout
        main_layout = QHBoxLayout(self)

        # Create the drag-and-drop list widget
        left_panel = QVBoxLayout()
        self.list_widget = DragDropList()
        left_panel.addWidget(self.list_widget)

        # Button layout
        button_layout = QHBoxLayout()

        # Add buttons
        add_button = QPushButton("Duplicate Layer")
        add_button.clicked.connect(self.add_new_step)
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

        print_button = QPushButton("Print Order")
        print_button.clicked.connect(self.print_order)
        print_button.setStyleSheet("""
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
        button_layout.addWidget(print_button)
        left_panel.addLayout(button_layout)

        right_panel = QVBoxLayout()

        # Settings group
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
        settings_layout = QVBoxLayout(settings_group)

        # Add various controls
        # Dropdown
        method_combo = QComboBox()
        method_combo.addItems(["Method 1", "Method 2", "Method 3"])
        method_combo.setStyleSheet("""
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
        settings_layout.addWidget(QLabel("Layer:"))
        settings_layout.addWidget(method_combo)

        # Spinbox
        iterations = QSpinBox()
        iterations.setRange(1, 100)
        iterations.setValue(10)
        iterations.setStyleSheet("""
            QSpinBox {
                background-color: #2b2b2b;
                color: white;
                padding: 5px;
                border: 1px solid #171717;
                border-radius: 4px;
            }
        """)
        settings_layout.addWidget(QLabel("Iterations:"))
        settings_layout.addWidget(iterations)

        # Action buttons
        action_button = QPushButton("Add Layer")
        action_button.setStyleSheet("""
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
        settings_layout.addWidget(action_button)

        # Add the panels to main layout
        main_layout.addLayout(left_panel, stretch=2)
        right_panel.addWidget(settings_group)
        right_panel.addStretch()
        main_layout.addLayout(right_panel, stretch=1)

        # Add initial steps
        steps = ["Step 1: Start", "Step 2: Process", "Step 3: Verify", "Step 4: Finish"]
        for step in steps:
            item = QListWidgetItem(step)
            self.list_widget.addItem(item)

    def add_new_step(self):
        text, ok = QInputDialog.getText(self, "Add Step", "Enter step description:")
        if ok and text:
            item = QListWidgetItem(text)
            self.list_widget.addItem(item)

    def remove_selected(self):
        current_item = self.list_widget.selectedItems()
        if current_item:
            self.list_widget.takeItem(self.list_widget.row(current_item[0]))

    def print_order(self):
        current_order = self.list_widget.get_items_order()
        print("Current order of steps:")
        for i, step in enumerate(current_order, 1):
            print(f"{i}. {step}")


if __name__ == "__main__":
    app = QApplication([])
    window = DragDropWindow()
    window.show()
    app.exec()
