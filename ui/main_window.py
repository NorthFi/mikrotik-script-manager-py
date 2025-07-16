import os
import tempfile
import subprocess
import platform
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                            QWidget, QLabel, QLineEdit, QPushButton, QComboBox,
                            QScrollArea, QGroupBox, QFileDialog, QMessageBox,
                            QTextEdit, QTabWidget, QInputDialog, QTreeWidget,
                            QTreeWidgetItem, QSplitter, QAction, QSizePolicy,
                            QDialog, QDialogButtonBox)
from PyQt5.QtCore import Qt, QRegularExpression, QSize
from PyQt5.QtGui import (QFont, QTextCharFormat, QColor, QSyntaxHighlighter,
                        QPalette, QIcon, QPixmap)
from PyQt5.QtCore import pyqtSignal

from ui.highlighter import MikroTikHighlighter
from ui.styles import apply_dark_style, apply_light_style
from core.script_manager import ScriptManager
from core.github_importer import GitHubImporter

class MikroTikScriptManager(QMainWindow):
    styleChanged = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MikroTik Script Manager")
        self.setGeometry(100, 100, 1200, 900)
        
        # Initialize core components
        self.script_manager = ScriptManager()
        self.current_vars = []
        self.final_script = ""
        self.dark_mode = self.script_manager.dark_mode
        self.temp_files = []
        
        # Initialize UI
        self.init_ui()
        self.apply_style()
        self.styleChanged.connect(self.on_style_changed)
        
        # Load initial data
        self.update_script_tree()

    def init_ui(self):
        self.tabs = QTabWidget()
        self.init_main_tab()
        self.init_help_tab()
        self.init_about_tab()
        self.init_menu_bar()
        self.setCentralWidget(self.tabs)
        self.setWindowIcon(QIcon.fromTheme('text-x-script'))

    def init_menu_bar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        file_menu.addAction(self.create_action('Import Script', self.import_script))
        file_menu.addAction(self.create_action('Import from GitHub', self.import_from_github))
        file_menu.addAction(self.create_action('Export Script', self.save_final_script))
        file_menu.addSeparator()
        file_menu.addAction(self.create_action('Exit', self.close))

        # View menu
        view_menu = menubar.addMenu('View')
        self.dark_mode_action = QAction('Dark Mode', self, checkable=True)
        self.dark_mode_action.setChecked(self.dark_mode)
        self.dark_mode_action.triggered.connect(self.toggle_dark_mode)
        view_menu.addAction(self.dark_mode_action)

        # Script menu
        script_menu = menubar.addMenu('Script')
        script_menu.addAction(self.create_action('Rename Script', self.rename_script))
        script_menu.addAction(self.create_action('Delete Script', self.delete_script))

        # Category menu
        category_menu = menubar.addMenu('Category')
        category_menu.addAction(self.create_action('New Category', self.add_category))
        category_menu.addAction(self.create_action('Rename Category', self.rename_category))
        category_menu.addAction(self.create_action('Delete Category', self.delete_category))

        # Help menu
        help_menu = menubar.addMenu('Help')
        help_menu.addAction(self.create_action('Documentation', self.show_documentation))
        help_menu.addAction(self.create_action('About', lambda: self.tabs.setCurrentIndex(2)))

    def create_action(self, name, callback):
        action = QAction(name, self)
        action.triggered.connect(callback)
        return action

    def init_main_tab(self):
        main_tab = QWidget()
        main_layout = QHBoxLayout()
        
        # Left panel - Script browser
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search scripts...")
        self.search_box.textChanged.connect(self.filter_scripts)
        left_layout.addWidget(self.search_box)
        
        self.script_tree = QTreeWidget()
        self.script_tree.setHeaderHidden(True)
        self.script_tree.itemClicked.connect(self.script_tree_selected)
        left_layout.addWidget(self.script_tree)
        
        left_panel.setLayout(left_layout)
        
        # Right panel - Script editor
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        self.script_desc = QLabel("Description will appear here")
        self.script_desc.setWordWrap(True)
        right_layout.addWidget(self.script_desc)
        
        splitter = QSplitter(Qt.Vertical)
        
        # Variables section
        self.vars_group = QGroupBox("Script Parameters")
        self.vars_widget = QWidget()
        self.vars_layout = QVBoxLayout(self.vars_widget)
        self.vars_layout.setSizeConstraint(QVBoxLayout.SetMinimumSize)
        
        vars_scroll = QScrollArea()
        vars_scroll.setWidgetResizable(True)
        vars_scroll.setWidget(self.vars_widget)
        vars_scroll.setMinimumHeight(200)
        vars_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        
        self.vars_group.setLayout(QVBoxLayout())
        self.vars_group.layout().addWidget(vars_scroll)
        splitter.addWidget(self.vars_group)
        
        # Preview section
        preview_group = QGroupBox("Script Preview")
        preview_layout = QVBoxLayout()
        self.preview_text = QTextEdit()
        self.preview_text.setFont(QFont("Courier New", 10))
        self.preview_highlighter = MikroTikHighlighter(self.preview_text.document())
        preview_layout.addWidget(self.preview_text)
        preview_group.setLayout(preview_layout)
        splitter.addWidget(preview_group)
        
        splitter.setSizes([300, 400])
        right_layout.addWidget(splitter)
        
        # Generate button
        self.generate_btn = QPushButton("Generate Final Script")
        self.generate_btn.clicked.connect(self.generate_final_script)
        right_layout.addWidget(self.generate_btn)
        
        # Output section
        output_group = QGroupBox("Final Script Output")
        output_layout = QVBoxLayout()
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Courier New", 10))
        self.output_highlighter = MikroTikHighlighter(self.output_text.document())
        output_layout.addWidget(self.output_text)
        output_group.setLayout(output_layout)
        right_layout.addWidget(output_group)
        
        # Action buttons
        action_layout = QHBoxLayout()
        save_btn = QPushButton("Save Script")
        save_btn.setIcon(QIcon.fromTheme('document-save'))
        save_btn.clicked.connect(self.save_final_script)
        action_layout.addWidget(save_btn)
        
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.setIcon(QIcon.fromTheme('edit-copy'))
        copy_btn.clicked.connect(self.copy_final_script)
        action_layout.addWidget(copy_btn)
        
        editor_btn = QPushButton("Open in Editor")
        editor_btn.setIcon(QIcon.fromTheme('accessories-text-editor'))
        editor_btn.clicked.connect(self.open_in_editor)
        action_layout.addWidget(editor_btn)
        
        right_layout.addLayout(action_layout)
        
        right_panel.setLayout(right_layout)
        
        # Combine panels
        main_layout.addWidget(left_panel, stretch=1)
        main_layout.addWidget(right_panel, stretch=3)
        main_tab.setLayout(main_layout)
        self.tabs.addTab(main_tab, "Script Manager")

    def init_help_tab(self):
        help_tab = QWidget()
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setMarkdown("""
        ## MikroTik Script Manager Help
        
        ### Script Management
        - **Import** scripts from files or GitHub
        - **Organize** scripts into categories
        - **Edit** variables in the parameters section
        
        ### Tips
        - Use `:global varname "value"` to define variables
        - Add comments above variables like `# varname - Description`
        - Place `### DO NOT EDIT FROM HERE ###` below editable sections
        
        ### Editor Integration
        - Click "Open in Editor" to edit in your default text editor
        - Changes must be saved back through the application
        """)
        layout = QVBoxLayout()
        layout.addWidget(help_text)
        help_tab.setLayout(layout)
        self.tabs.addTab(help_tab, "Help")

    def init_about_tab(self):
        about_tab = QWidget()
        about_text = QTextEdit()
        about_text.setReadOnly(True)
        about_text.setMarkdown("""
        ## MikroTik Script Manager
        
        **Version:** 2.2  
        **Author:** Daniel Jordaan
        **License:** MIT
        
        **Features:**
        - Script organization and management
        - Variable parameterization
        - Syntax highlighting
        - Dark/Light mode
        - Cross-platform support
        - Persistent storage
        - Editor integration
        """)
        layout = QVBoxLayout()
        layout.addWidget(about_text)
        about_tab.setLayout(layout)
        self.tabs.addTab(about_tab, "About")

    def apply_style(self):
        if self.dark_mode:
            apply_dark_style(QApplication.instance())
        else:
            apply_light_style(QApplication.instance())
        self.styleChanged.emit(self.dark_mode)

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.script_manager.dark_mode = self.dark_mode
        self.apply_style()
        self.script_manager.save_data()

    def on_style_changed(self, dark_mode):
        self.preview_highlighter = MikroTikHighlighter(self.preview_text.document())
        self.output_highlighter = MikroTikHighlighter(self.output_text.document())

    def update_script_tree(self):
        self.script_tree.clear()
        current_script = self.get_selected_script_name()
        
        # Sort categories alphabetically
        sorted_categories = sorted(self.script_manager.categories.keys())
        
        for category in sorted_categories:
            script_names = self.script_manager.categories[category]
            category_item = QTreeWidgetItem([category])
            self.script_tree.addTopLevelItem(category_item)
            
            # Sort scripts alphabetically
            for name in sorted(script_names):
                if name in self.script_manager.scripts:
                    script_item = QTreeWidgetItem([name])
                    category_item.addChild(script_item)
                    if current_script == name:
                        self.script_tree.setCurrentItem(script_item)
        
        self.script_tree.expandAll()

    def filter_scripts(self, text):
        search_text = text.lower()
        for i in range(self.script_tree.topLevelItemCount()):
            category_item = self.script_tree.topLevelItem(i)
            category_matches = search_text in category_item.text(0).lower()
            any_child_matches = False
            
            for j in range(category_item.childCount()):
                script_item = category_item.child(j)
                script_matches = search_text in script_item.text(0).lower()
                script_item.setHidden(not script_matches)
                if script_matches:
                    any_child_matches = True
            
            category_item.setHidden(not (category_matches or any_child_matches))

    def script_tree_selected(self, item, column):
        if item.parent():  # It's a script item
            script_name = item.text(0)
            if script_name in self.script_manager.scripts:
                self.script_selected(script_name)

    def add_category(self):
        name, ok = QInputDialog.getText(self, "New Category", "Category name:")
        if ok and name:
            if name not in self.script_manager.categories:
                self.script_manager.categories[name] = []
                self.update_script_tree()
                self.script_manager.save_data()
            else:
                QMessageBox.warning(self, "Duplicate", "Category already exists!")

    def rename_category(self):
        item = self.script_tree.currentItem()
        if not item or item.parent():
            return
            
        old_name = item.text(0)
        new_name, ok = QInputDialog.getText(
            self, "Rename Category", 
            "New category name:",
            QLineEdit.Normal,
            old_name
        )
        
        if ok and new_name and new_name != old_name:
            if new_name in self.script_manager.categories:
                QMessageBox.warning(self, "Duplicate", "Category already exists!")
                return
                
            self.script_manager.categories[new_name] = self.script_manager.categories.pop(old_name)
            for script in self.script_manager.categories[new_name]:
                if script in self.script_manager.scripts:
                    self.script_manager.scripts[script]['category'] = new_name
            self.update_script_tree()
            self.script_manager.save_data()

    def delete_category(self):
        item = self.script_tree.currentItem()
        if not item or item.parent():
            return
            
        category_name = item.text(0)
        if self.script_manager.categories[category_name]:
            reply = QMessageBox.question(
                self, "Category Not Empty",
                "Move scripts to 'Uncategorized' before deleting?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Yes:
                for script_name in self.script_manager.categories[category_name]:
                    if script_name in self.script_manager.scripts:
                        self.script_manager.scripts[script_name]['category'] = 'Uncategorized'
                        self.script_manager.categories['Uncategorized'].append(script_name)
                del self.script_manager.categories[category_name]
                self.update_script_tree()
                self.script_manager.save_data()
            elif reply == QMessageBox.No:
                del self.script_manager.categories[category_name]
                self.update_script_tree()
                self.script_manager.save_data()

    def import_script_with_options(self, path):
        """Handle script import with category selection"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Get suggested name from filename
            suggested_name = os.path.splitext(os.path.basename(path))[0]
            
            # Create dialog for import options
            dialog = QDialog(self)
            dialog.setWindowTitle("Import Options")
            layout = QVBoxLayout()
            
            # Script name
            name_layout = QHBoxLayout()
            name_layout.addWidget(QLabel("Script Name:"))
            name_edit = QLineEdit(suggested_name)
            name_layout.addWidget(name_edit)
            layout.addLayout(name_layout)
            
            # Description
            desc_layout = QHBoxLayout()
            desc_layout.addWidget(QLabel("Description:"))
            desc_edit = QLineEdit(f"Imported from {os.path.basename(path)}")
            desc_layout.addWidget(desc_edit)
            layout.addLayout(desc_layout)
            
            # Category selection
            category_layout = QHBoxLayout()
            category_layout.addWidget(QLabel("Category:"))
            category_combo = QComboBox()
            category_combo.addItems(sorted(self.script_manager.categories.keys()))
            category_combo.setEditable(True)
            category_layout.addWidget(category_combo)
            layout.addLayout(category_layout)
            
            # Buttons
            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)
            
            dialog.setLayout(layout)
            
            if dialog.exec_() == QDialog.Accepted:
                name = name_edit.text().strip()
                description = desc_edit.text().strip()
                category = category_combo.currentText().strip()
                
                if not name:
                    raise ValueError("Script name cannot be empty")
                
                self.save_script(name, code, description, category)
                return True
            return False
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import script:\n{str(e)}")
            return False

    def import_script(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Script", "", 
            "Scripts (*.rsc *.txt);;All Files (*)"
        )
        if path:
            self.import_script_with_options(path)

    def import_from_github(self):
        url, ok = QInputDialog.getText(
            self, "GitHub Import", 
            "Enter raw GitHub URL:"
        )
        if ok and url:
            try:
                name, code, description = GitHubImporter.import_from_url(url)
                
                # Create dialog for GitHub import options
                dialog = QDialog(self)
                dialog.setWindowTitle("GitHub Import Options")
                layout = QVBoxLayout()
                
                # Script name
                name_layout = QHBoxLayout()
                name_layout.addWidget(QLabel("Script Name:"))
                name_edit = QLineEdit(name)
                name_layout.addWidget(name_edit)
                layout.addLayout(name_layout)
                
                # Description
                desc_layout = QHBoxLayout()
                desc_layout.addWidget(QLabel("Description:"))
                desc_edit = QLineEdit(description)
                desc_layout.addWidget(desc_edit)
                layout.addLayout(desc_layout)
                
                # Category selection
                category_layout = QHBoxLayout()
                category_layout.addWidget(QLabel("Category:"))
                category_combo = QComboBox()
                category_combo.addItems(sorted(self.script_manager.categories.keys()))
                category_combo.setEditable(True)
                category_combo.setCurrentText("GitHub Imports")
                category_layout.addWidget(category_combo)
                layout.addLayout(category_layout)
                
                # Buttons
                button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                button_box.accepted.connect(dialog.accept)
                button_box.rejected.connect(dialog.reject)
                layout.addWidget(button_box)
                
                dialog.setLayout(layout)
                
                if dialog.exec_() == QDialog.Accepted:
                    name = name_edit.text().strip()
                    description = desc_edit.text().strip()
                    category = category_combo.currentText().strip()
                    
                    if not name:
                        raise ValueError("Script name cannot be empty")
                    
                    self.save_script(name, code, description, category)
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import from GitHub:\n{str(e)}")

    def save_script(self, name, code, description, category):
        if self.script_manager.EDIT_CUTOFF_MARKER not in code:
            reply = QMessageBox.question(
                self, "Warning",
                "Script is missing the required cutoff marker. Save anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # Ensure category exists
        if category not in self.script_manager.categories:
            self.script_manager.categories[category] = []
        
        # Handle existing script
        if name in self.script_manager.scripts:
            old_category = self.script_manager.scripts[name].get('category', 'Uncategorized')
            if old_category in self.script_manager.categories and name in self.script_manager.categories[old_category]:
                self.script_manager.categories[old_category].remove(name)
        
        # Add to new category
        if name not in self.script_manager.categories[category]:
            self.script_manager.categories[category].append(name)
        
        # Save script data
        self.script_manager.scripts[name] = {
            'code': code,
            'description': description,
            'category': category
        }
        
        self.update_script_tree()
        self.select_script_in_tree(name)
        self.script_manager.save_data()

    def select_script_in_tree(self, script_name):
        for i in range(self.script_tree.topLevelItemCount()):
            category_item = self.script_tree.topLevelItem(i)
            for j in range(category_item.childCount()):
                if category_item.child(j).text(0) == script_name:
                    self.script_tree.setCurrentItem(category_item.child(j))
                    return

    def rename_script(self):
        current = self.get_selected_script_name()
        if not current:
            return
            
        new_name, ok = QInputDialog.getText(
            self, "Rename Script", 
            "New script name:",
            QLineEdit.Normal,
            current
        )
        
        if ok and new_name and new_name != current:
            if new_name in self.script_manager.scripts:
                QMessageBox.warning(self, "Duplicate", "Script name already exists!")
                return
            
            # Update categories
            script_data = self.script_manager.scripts[current]
            category = script_data.get('category', 'Uncategorized')
            if category in self.script_manager.categories and current in self.script_manager.categories[category]:
                self.script_manager.categories[category].remove(current)
                self.script_manager.categories[category].append(new_name)
            
            # Update scripts
            self.script_manager.scripts[new_name] = script_data
            del self.script_manager.scripts[current]
            
            self.update_script_tree()
            self.select_script_in_tree(new_name)
            self.script_manager.save_data()

    def delete_script(self):
        current = self.get_selected_script_name()
        if not current:
            return
            
        confirm = QMessageBox.question(
            self, "Confirm Delete", 
            f"Delete script '{current}'?", 
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            # Remove from category
            script_data = self.script_manager.scripts.get(current, {})
            category = script_data.get('category', 'Uncategorized')
            if category in self.script_manager.categories and current in self.script_manager.categories[category]:
                self.script_manager.categories[category].remove(current)
            
            # Remove from scripts
            if current in self.script_manager.scripts:
                del self.script_manager.scripts[current]
            
            self.update_script_tree()
            self.clear_vars_layout()
            self.preview_text.clear()
            self.output_text.clear()
            self.script_manager.save_data()

    def get_selected_script_name(self):
        item = self.script_tree.currentItem()
        if item and item.parent():
            return item.text(0)
        return None

    def script_selected(self, name):
        if name in self.script_manager.scripts:
            script = self.script_manager.scripts[name]
            self.script_desc.setText(script['description'])
            self.preview_text.setPlainText(script['code'])
            self.populate_vars(script['code'])

    def populate_vars(self, code):
        self.clear_vars_layout()
        self.current_vars = []
        vars = self.script_manager.extract_ordered_vars(code)
        defaults = self.script_manager.extract_var_defaults(code)
        descriptions = self.script_manager.extract_var_descriptions(code)

        # Calculate needed height (60px per variable + 50px padding)
        needed_height = len(vars) * 60 + 50
        self.vars_group.setMinimumHeight(min(needed_height, 600))

        for var in vars:
            row = QHBoxLayout()
            
            # Description label
            desc = QLabel(descriptions.get(var, "No description available"))
            desc.setStyleSheet("color: gray; font-style: italic;")
            desc.setWordWrap(True)
            desc.setMinimumWidth(200)
            
            # Input field
            field = QLineEdit()
            field.setText(defaults.get(var, ""))
            field.setMinimumWidth(150)
            
            # Variable name label
            name = QLabel(f"${var}")
            name.setMinimumWidth(100)
            
            row.addWidget(desc, stretch=2)
            row.addWidget(field, stretch=1)
            row.addWidget(name, stretch=1)
            
            row_widget = QWidget()
            row_widget.setLayout(row)
            self.vars_layout.addWidget(row_widget)
            self.current_vars.append((var, field))
        
        self.vars_layout.addStretch()
        self.vars_widget.adjustSize()
        self.vars_group.adjustSize()

    def clear_vars_layout(self):
        while self.vars_layout.count():
            item = self.vars_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.vars_group.setMinimumHeight(200)

    def generate_final_script(self):
        name = self.get_selected_script_name()
        if not name or name not in self.script_manager.scripts:
            QMessageBox.warning(self, "Warning", "No script selected")
            return
            
        code = self.script_manager.scripts[name]['code']
        parts = code.split(self.script_manager.EDIT_CUTOFF_MARKER, 1)
        editable = parts[0]
        protected = parts[1] if len(parts) > 1 else ""

        for var, field in self.current_vars:
            val = field.text()
            # Replace variable declarations
            editable = self.script_manager.SET_PATTERN.sub(
                lambda m: f':set ${m.group(1)} "{val}"' if m.group(1) == var else m.group(0),
                editable
            )
            editable = self.script_manager.DEFAULT_PATTERN.sub(
                lambda m: f':global {m.group(1)} "{val}"' if m.group(1) == var else m.group(0),
                editable
            )
            # Replace variable references
            editable = editable.replace(f'${var}', val)

        self.final_script = editable + self.script_manager.EDIT_CUTOFF_MARKER + protected
        self.output_text.setPlainText(self.final_script)
        QMessageBox.information(self, "Success", "Script generated successfully!")

    def save_final_script(self):
        if not self.final_script:
            QMessageBox.warning(self, "Warning", "No script generated to save")
            return
            
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Script", 
            "", "MikroTik Script (*.rsc);;Text File (*.txt);;All Files (*)"
        )
        
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.final_script)
                QMessageBox.information(self, "Success", f"Script saved to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save script:\n{str(e)}")

    def copy_final_script(self):
        if not self.final_script:
            QMessageBox.warning(self, "Warning", "No script generated to copy")
            return
            
        QApplication.clipboard().setText(self.final_script)
        QMessageBox.information(self, "Success", "Script copied to clipboard!")

    def open_in_editor(self):
        if not self.final_script:
            QMessageBox.warning(self, "Warning", "No script generated to open")
            return
        
        try:
            # Create temp file
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.rsc',
                encoding='utf-8',
                delete=False
            ) as f:
                f.write(self.final_script)
                temp_path = f.name
                self.temp_files.append(temp_path)
            
            # Open based on platform
            system = platform.system()
            if system == 'Windows':
                os.startfile(temp_path)
            elif system == 'Darwin':
                subprocess.run(['open', temp_path])
            else:
                subprocess.run(['xdg-open', temp_path])
                
            QMessageBox.information(
                self,
                "Editor Opened",
                "\nScript opened, please select your favourite text editor."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open editor:\n{str(e)}")

    def cleanup_temp_files(self):
        """Clean up any remaining temporary files"""
        for temp_path in self.temp_files:
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except Exception as e:
                print(f"Error cleaning up temp file: {str(e)}")
        self.temp_files = []

    def closeEvent(self, event):
        """Handle window close event"""
        self.cleanup_temp_files()
        self.script_manager.save_data()
        super().closeEvent(event)

    def show_documentation(self):
        """Show documentation tab"""
        self.tabs.setCurrentIndex(1)