#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Created By  : João Santos with some help by ChatGPT
# Created Date: 2024/01/25
# Updated Date: 2024/01/31
# version ='1.1'
#
# Description:
#     JVET Meetings File Finder, searches for specific meeting files and
#     provides an interface for opening the directly
# ---------------------------------------------------------------------------

__author__ = "João Santos"
__copyright__ = "Copyright 2024, João Santos"
__license__ = "GPL2"
__version__ = "1.1"
__maintainer__ = "João Santos"
__email__ = "joaompssantos@gmail.com"
__status__ = "Production"


import json
import operator
import os
import platform
import subprocess
from enum import Enum
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QFileDialog,
    QListWidget, QComboBox, QHBoxLayout, QLabel, QMessageBox, QCheckBox,
    QCompleter
)
from PyQt6.QtCore import Qt
from pathlib import Path

# Enum to represent different operating systems
class Platform(Enum):
    WINDOWS = 'Windows'
    MACOS = 'Darwin'
    LINUX = 'Linux'

class JVETDocumentOpener(QWidget):
    def __init__(self):
        super().__init__()

        # Initialize attributes with default values
        self.documents_directory = Path.home()
        self.show_full_path = False
        self.hide_documents_directory = True
        self.found_files = []

        # Load user settings
        self.load_settings()

        # Initialize the GUI
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('JVET Document Finder')
        
        # Create directory_label
        self.directory_label = QLabel(f"Documents Directory: {self.documents_directory}", self)

        # Layout for the search interface
        search_layout = QVBoxLayout()

        # Layout for displaying and changing the documents directory
        directory_layout = QHBoxLayout()
        change_directory_button = QPushButton('Change', self)
        change_directory_button.setFixedWidth(change_directory_button.sizeHint().width())
        change_directory_button.clicked.connect(self.change_documents_directory)
        directory_layout.addWidget(self.directory_label)
        directory_layout.addWidget(change_directory_button)
        search_layout.addLayout(directory_layout)

        # Layout for the search box and search button
        search_box_layout = QHBoxLayout()

        # Use QComboBox to allow for a combination of dropdown menu and search text box
        self.search_box = QComboBox()
        self.search_box.addItems(self.immutable_docs[0])
        self.search_box.setCurrentIndex(-1)
        self.search_box.setInsertPolicy(QComboBox.InsertPolicy.InsertAtBottom)

        # Set text box properties
        self.search_box.setEditable(True)
        self.search_box.lineEdit().setPlaceholderText('Insert document number here')

        # Create a completer and set it for the search box
        completer = QCompleter(self.immutable_docs[0], self)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)  # Change filter mode if needed
        completer.setModel(self.search_box.model())
        self.search_box.setCompleter(completer)

        # Set the width of the search text box to match the QLabel's preferred size
        search_box_width = self.directory_label.sizeHint().width()
        self.search_box.setFixedWidth(search_box_width)

        search_box_layout.addWidget(self.search_box)

        search_button = QPushButton('Search', self)
        search_button.clicked.connect(self.perform_search)

        # Align the search box to the left and the button to the right
        search_box_layout.addWidget(search_button, alignment=Qt.AlignmentFlag.AlignRight)

        search_layout.addLayout(search_box_layout)

        # Create the document list and add it to the main layout
        self.document_list = QListWidget(self)
        self.document_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.document_list.doubleClicked.connect(lambda: self.open_selected_document(self.document_list.currentItem()))
        search_layout.addWidget(self.document_list)

        # Layout for displaying and opening documents
        open_show_layout = self.create_open_show_layout()
        search_layout.addLayout(open_show_layout)

        # Set the main layout
        self.setLayout(search_layout)

        # Set focus to search box
        self.search_box.setFocus()

        # Connect returnPressed signal to perform_search method
        self.search_box.lineEdit().returnPressed.connect(self.perform_search)

    def create_open_show_layout(self):
        # Layout for opening documents and toggling options
        open_show_layout = QHBoxLayout()

        open_button = QPushButton('Open Selected Document(s)', self)
        open_button.setFixedWidth(open_button.sizeHint().width())
        open_button.clicked.connect(self.open_selected_documents)
        open_show_layout.addWidget(open_button, alignment=Qt.AlignmentFlag.AlignLeft)

        # Align the check boxes to the right
        self.show_full_path_checkbox = QCheckBox('Show Full Path', self)
        self.show_full_path_checkbox.setChecked(self.show_full_path)
        self.show_full_path_checkbox.stateChanged.connect(self.toggle_show_full_path)
        open_show_layout.addWidget(self.show_full_path_checkbox, alignment=Qt.AlignmentFlag.AlignRight)

        self.hide_documents_directory_checkbox = QCheckBox('Hide Documents Directory', self)
        self.hide_documents_directory_checkbox.setChecked(self.hide_documents_directory)
        self.hide_documents_directory_checkbox.stateChanged.connect(self.toggle_hide_documents_directory)
        open_show_layout.addWidget(self.hide_documents_directory_checkbox, alignment=Qt.AlignmentFlag.AlignRight)

        return open_show_layout

    # Handler for changing documents directory
    def change_documents_directory(self):
        new_directory = QFileDialog.getExistingDirectory(
            self, 'Select Documents Directory', str(self.documents_directory)
        )

        if new_directory:
            self.documents_directory = Path(new_directory)
            self.directory_label.setText(f"Documents Directory: {self.documents_directory}")
            self.show_feedback_message('Directory changed successfully!')
        else:
            self.show_feedback_message('Directory change cancelled.')

    # Handler for toggling show full path option
    def toggle_show_full_path(self, state):
        self.show_full_path = self.show_full_path_checkbox.isChecked()
        self.update_displayed_items()

    # Handler for toggling hide documents directory option
    def toggle_hide_documents_directory(self, state):
        self.hide_documents_directory = self.hide_documents_directory_checkbox.isChecked()
        self.update_displayed_items()

    # Method to update displayed items in the document list
    def update_displayed_items(self):
        self.document_list.clear()

        for file_path, file_name in self.found_files:
            display_text = self.get_display_text(file_path, file_name)
            self.document_list.addItem(display_text)
    
    # Method to get the display text for a file or folder
    def get_display_text(self, file_path, file_name):
        is_dir = False

        if Path(file_path, file_name).is_dir():
            is_dir = True

        if self.show_full_path:
            display_text = str(Path(file_path, file_name)) if not is_dir else str(Path(file_path, file_name)) + os.path.sep
            if self.hide_documents_directory:
                display_text = display_text.replace(str(self.documents_directory) + os.path.sep, '')
        else:
            display_text = file_name if not is_dir else file_name + os.path.sep
        return display_text

    # Method to get found files
    def perform_search(self):
        # Get string to be searched
        target_string = self.get_document_number().lower()

        self.found_files = []

        self.show_feedback_message(f'Searching for {target_string}')
        for file_path in self.documents_directory.rglob('*'):
            # Ignore current item if its name starts with the target string followed by a _
            if file_path.name.startswith(f'{target_string}_'):
                continue
            # Check if the target_string is in the current item name
            elif (file_path.is_file() and not file_path.parent.name.startswith(f'{target_string}_') and target_string in str(Path(file_path.parent.name, file_path.name)).lower()) or \
                 (file_path.is_dir() and target_string in str(file_path.name).lower()):
                self.found_files.append([str(file_path.parent.absolute()), file_path.name])

        # Sorts output list alphabetically
        self.found_files.sort(key=operator.itemgetter(0, 1))

        # Update the list of displayed items
        self.update_displayed_items()

        if self.found_files:
            self.show_feedback_message(f'{len(self.found_files)} file(s) found successfully!')
        else:
            self.show_feedback_message('No files found.')

    # Map the immutable document name to its number (returns provided text is not present in immutables list)
    def get_document_number(self):
        if self.search_box.lineEdit().text() in self.immutable_docs[0]:
            return self.immutable_docs[1][self.immutable_docs[0].index(self.search_box.lineEdit().text())]
        else:
            return self.search_box.lineEdit().text()

    # Handler for opening selected document
    def open_selected_document(self, selected_item):
        selected_item_idx = self.document_list.row(selected_item)

        file_path = Path(*self.found_files[selected_item_idx])

        if selected_item:
            if Path(file_path).exists():
                open_command = self.get_open_command(file_path)
                self.open_document(open_command)

    # Handler for opening selected documents
    def open_selected_documents(self):
        selected_items = self.document_list.selectedItems()

        if selected_items:
            for selected_item in selected_items:
                self.open_selected_document(selected_item)

    # Method to open a document
    def open_document(self, open_command):
        print(f'Trying to open: {open_command}')
        try:
            subprocess.run(open_command, shell=True)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to open document: {str(e)}')

    # Method to get open command based on the platform
    def get_open_command(self, file_path):
        if Platform.WINDOWS.value in platform.system():
            return f'cmd /c start "" "{file_path}"'
        elif Platform.MACOS.value in platform.system():
            return f'open "{file_path}"'
        elif Platform.LINUX.value in platform.system():
            return f'xdg-open "{file_path}"'
        else:
            return file_path

    # Method to load user settings
    def load_settings(self):
        # Load settings from a file if available
        settings_file_path = 'settings.json'
        if Path(settings_file_path).exists():
            with open(settings_file_path, 'r') as settings_file:
                settings = json.load(settings_file)
                self.immutable_docs = self.parse_immutables(settings.get('immutable_documents', '').split(','))
                self.documents_directory = Path(settings.get('documents_directory', str(Path.home())))
                self.show_full_path = settings.get('show_full_path', False)
                self.hide_documents_directory = settings.get('hide_documents_directory', True)

    # Method to save user settings
    def save_settings(self):
        # Save settings to a file
        settings_file_path = 'settings.json'
        settings = {
            'immutable_documents': str(self.build_immutables()),
            'documents_directory': str(self.documents_directory),
            'show_full_path': self.show_full_path,
            'hide_documents_directory': self.hide_documents_directory
        }
        with open(settings_file_path, 'w') as settings_file:
            json.dump(settings, settings_file)
    
    # Parse immutable files to produce list
    def parse_immutables(self, immutables: list):
        return list(map(list, zip(*(string.split(':') for string in immutables))))

    # Build immutables string
    def build_immutables(self):
        return ','.join([f'{name}:{number}' for name, number in zip(*self.immutable_docs)])

    # Slot method for the closeEvent of the main window
    def closeEvent(self, event):
        # Save settings before closing the application
        self.save_settings()
        event.accept()

    # Method to show feedback messages
    def show_feedback_message(self, message):
        print((self, 'Feedback', message))
        # QMessageBox.information(self, 'Feedback', message)

if __name__ == '__main__':
    app = QApplication([])

    opener = JVETDocumentOpener()
    opener.show()

    app.exec()
