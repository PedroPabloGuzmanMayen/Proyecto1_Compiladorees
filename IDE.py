import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import subprocess
import sys

class PythonIDE:
    def __init__(self, root):
        self.root = root
        self.root.title("Python IDE")
        self.root.geometry("1200x800")
        self.root.configure(bg='#2b2b2b')
        
        # Variables
        self.current_file = None
        self.file_saved = True
        
        # Create the interface
        self.create_header()
        self.create_main_layout()
        self.create_file_manager()
        self.create_editor()
        self.create_status_bar()
        
        # Bind events
        self.bind_events()
        
        # Set initial directory
        self.current_directory = os.getcwd()
        self.refresh_file_manager()
    
    def create_header(self):
        """Create the header with tool buttons"""
        self.header_frame = tk.Frame(self.root, bg='#3c3c3c', height=50)
        self.header_frame.pack(fill='x', padx=5, pady=5)
        self.header_frame.pack_propagate(False)
        
        # File operations
        tk.Button(self.header_frame, text="📄 Nuevo", command=self.new_file,
                 bg='#4a4a4a', fg='white', relief='flat', padx=10).pack(side='left', padx=2)
        
        tk.Button(self.header_frame, text="📁 Abrir", command=self.open_file,
                 bg='#4a4a4a', fg='white', relief='flat', padx=10).pack(side='left', padx=2)
        
        tk.Button(self.header_frame, text="💾 Guardar", command=self.save_file,
                 bg='#4a4a4a', fg='white', relief='flat', padx=10).pack(side='left', padx=2)
        
        tk.Button(self.header_frame, text="💾 Guardar Como", command=self.save_as_file,
                 bg='#4a4a4a', fg='white', relief='flat', padx=10).pack(side='left', padx=2)
        
        # Separator
        tk.Frame(self.header_frame, width=2, bg='#666666').pack(side='left', fill='y', padx=10)
        
        # Edit operations
        tk.Button(self.header_frame, text="✂️ Cortar", command=self.cut_text,
                 bg='#4a4a4a', fg='white', relief='flat', padx=10).pack(side='left', padx=2)
        
        tk.Button(self.header_frame, text="📋 Copiar", command=self.copy_text,
                 bg='#4a4a4a', fg='white', relief='flat', padx=10).pack(side='left', padx=2)
        
        tk.Button(self.header_frame, text="📌 Pegar", command=self.paste_text,
                 bg='#4a4a4a', fg='white', relief='flat', padx=10).pack(side='left', padx=2)
        
        # Separator
        tk.Frame(self.header_frame, width=2, bg='#666666').pack(side='left', fill='y', padx=10)
        
        # Run button
        tk.Button(self.header_frame, text="▶️ Ejecutar", command=self.run_python,
                 bg='#0d7377', fg='white', relief='flat', padx=10).pack(side='left', padx=2)
        
        # File name label
        self.file_label = tk.Label(self.header_frame, text="Sin título", 
                                  bg='#3c3c3c', fg='white', font=('Arial', 10))
        self.file_label.pack(side='right', padx=10)
    
    def create_main_layout(self):
        """Create the main layout with paned window"""
        self.main_frame = tk.Frame(self.root, bg='#2b2b2b')
        self.main_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create paned window for resizable panels
        self.paned_window = tk.PanedWindow(self.main_frame, orient='horizontal', 
                                          bg='#2b2b2b', sashwidth=5)
        self.paned_window.pack(fill='both', expand=True)
    
    def create_editor(self):
        """Create the text editor"""
        self.editor_frame = tk.Frame(self.paned_window, bg='#2b2b2b')
        
        # Editor with line numbers
        self.editor_container = tk.Frame(self.editor_frame, bg='#2b2b2b')
        self.editor_container.pack(fill='both', expand=True)
        
        # Line numbers
        self.line_numbers = tk.Text(self.editor_container, width=4, padx=3, takefocus=0,
                                   border=0, state='disabled', wrap='none',
                                   bg='#3c3c3c', fg='#888888', font=('Consolas', 11))
        self.line_numbers.pack(side='left', fill='y')
        
        # Text editor
        self.text_editor = scrolledtext.ScrolledText(
            self.editor_container,
            wrap='none',
            bg='#1e1e1e',
            fg='#ffffff',
            font=('Consolas', 11),
            insertbackground='white',
            selectbackground='#264f78',
            relief='flat',
            borderwidth=0
        )
        self.text_editor.pack(side='left', fill='both', expand=True)
        
        # Add to paned window
        self.paned_window.add(self.editor_frame, width=800)
    
    def create_file_manager(self):
        """Create the file manager"""
        self.file_frame = tk.Frame(self.paned_window, bg='#2b2b2b')
        
        # File manager header
        fm_header = tk.Frame(self.file_frame, bg='#3c3c3c', height=30)
        fm_header.pack(fill='x')
        fm_header.pack_propagate(False)
        
        tk.Label(fm_header, text="📁 Explorador de Archivos", 
                bg='#3c3c3c', fg='white', font=('Arial', 10, 'bold')).pack(side='left', padx=10, pady=5)
        
        tk.Button(fm_header, text="🔄", command=self.refresh_file_manager,
                 bg='#4a4a4a', fg='white', relief='flat', width=3).pack(side='right', padx=5)
        
        # Directory path
        self.path_frame = tk.Frame(self.file_frame, bg='#2b2b2b')
        self.path_frame.pack(fill='x', padx=5, pady=2)
        
        self.path_label = tk.Label(self.path_frame, text="", bg='#2b2b2b', fg='#cccccc', 
                                  font=('Arial', 9), anchor='w')
        self.path_label.pack(fill='x')
        
        # File tree
        self.file_tree = ttk.Treeview(self.file_frame, show='tree')
        self.file_tree.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Configure treeview style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', background='#1e1e1e', foreground='white', 
                       fieldbackground='#1e1e1e')
        style.configure('Treeview.Heading', background='#3c3c3c', foreground='white')
        
        # Add to paned window
        self.paned_window.add(self.file_frame, width=300)
    
    def create_status_bar(self):
        """Create the status bar"""
        self.status_bar = tk.Frame(self.root, bg='#3c3c3c', height=25)
        self.status_bar.pack(fill='x', side='bottom')
        self.status_bar.pack_propagate(False)
        
        self.status_label = tk.Label(self.status_bar, text="Listo", 
                                    bg='#3c3c3c', fg='white', font=('Arial', 9))
        self.status_label.pack(side='left', padx=10, pady=2)
        
        # Cursor position
        self.cursor_label = tk.Label(self.status_bar, text="Línea: 1, Columna: 1", 
                                    bg='#3c3c3c', fg='white', font=('Arial', 9))
        self.cursor_label.pack(side='right', padx=10, pady=2)
    
    def bind_events(self):
        """Bind keyboard and mouse events"""
        # File tree double click
        self.file_tree.bind('<Double-1>', self.on_file_double_click)
        
        # Text editor events
        self.text_editor.bind('<KeyRelease>', self.on_text_change)
        self.text_editor.bind('<Button-1>', self.update_cursor_position)
        self.text_editor.bind('<KeyRelease>', self.update_cursor_position, add='+')
        
        # Keyboard shortcuts
        self.root.bind('<Control-n>', lambda e: self.new_file())
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_file())
        self.root.bind('<Control-Shift-S>', lambda e: self.save_as_file())
        self.root.bind('<F5>', lambda e: self.run_python())
        
        # Window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def refresh_file_manager(self):
        """Refresh the file manager tree"""
        # Clear existing items
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # Update path label
        self.path_label.config(text=f"📁 {self.current_directory}")
        
        # Add parent directory option
        parent_dir = os.path.dirname(self.current_directory)
        if parent_dir != self.current_directory:
            self.file_tree.insert('', 'end', text='📁 ..', values=[parent_dir], tags=['directory'])
        
        try:
            # List directory contents
            items = os.listdir(self.current_directory)
            items.sort()
            
            # Add directories first
            for item in items:
                item_path = os.path.join(self.current_directory, item)
                if os.path.isdir(item_path):
                    self.file_tree.insert('', 'end', text=f'📁 {item}', 
                                        values=[item_path], tags=['directory'])
            
            # Add files
            for item in items:
                item_path = os.path.join(self.current_directory, item)
                if os.path.isfile(item_path):
                    icon = '🐍' if item.endswith('.py') else '📄'
                    self.file_tree.insert('', 'end', text=f'{icon} {item}', 
                                        values=[item_path], tags=['file'])
        
        except PermissionError:
            self.status_label.config(text="Error: Sin permisos para acceder al directorio")
    
    def on_file_double_click(self, event):
        """Handle file tree double click"""
        selection = self.file_tree.selection()
        if selection:
            item = selection[0]
            item_path = self.file_tree.item(item, 'values')[0]
            
            if os.path.isdir(item_path):
                self.current_directory = item_path
                self.refresh_file_manager()
            else:
                self.open_specific_file(item_path)
    
    def new_file(self):
        """Create a new file"""
        if not self.file_saved:
            if not self.ask_save_changes():
                return
        
        self.text_editor.delete(1.0, tk.END)
        self.current_file = None
        self.file_saved = True
        self.update_title()
        self.update_line_numbers()
        self.status_label.config(text="Nuevo archivo creado")
    
    def open_file(self):
        """Open a file dialog to select and open a file"""
        if not self.file_saved:
            if not self.ask_save_changes():
                return
        
        file_path = filedialog.askopenfilename(
            title="Abrir archivo",
            filetypes=[
                ("Archivos Python", "*.py"),
                ("Archivos de texto", "*.txt"),
                ("Todos los archivos", "*.*")
            ]
        )
        
        if file_path:
            self.open_specific_file(file_path)
    
    def open_specific_file(self, file_path):
        """Open a specific file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            self.text_editor.delete(1.0, tk.END)
            self.text_editor.insert(1.0, content)
            self.current_file = file_path
            self.file_saved = True
            self.update_title()
            self.update_line_numbers()
            self.status_label.config(text=f"Archivo abierto: {os.path.basename(file_path)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el archivo:\n{str(e)}")
    
    def save_file(self):
        """Save the current file"""
        if self.current_file:
            try:
                content = self.text_editor.get(1.0, tk.END + '-1c')
                with open(self.current_file, 'w', encoding='utf-8') as file:
                    file.write(content)
                
                self.file_saved = True
                self.update_title()
                self.status_label.config(text=f"Archivo guardado: {os.path.basename(self.current_file)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar el archivo:\n{str(e)}")
        else:
            self.save_as_file()
    
    def save_as_file(self):
        """Save the file with a new name"""
        file_path = filedialog.asksaveasfilename(
            title="Guardar como",
            defaultextension=".py",
            filetypes=[
                ("Archivos Python", "*.py"),
                ("Archivos de texto", "*.txt"),
                ("Todos los archivos", "*.*")
            ]
        )
        
        if file_path:
            try:
                content = self.text_editor.get(1.0, tk.END + '-1c')
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(content)
                
                self.current_file = file_path
                self.file_saved = True
                self.update_title()
                self.status_label.config(text=f"Archivo guardado como: {os.path.basename(file_path)}")
                self.refresh_file_manager()
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar el archivo:\n{str(e)}")
    
    def cut_text(self):
        """Cut selected text"""
        try:
            self.text_editor.event_generate("<<Cut>>")
            self.status_label.config(text="Texto cortado")
        except:
            pass
    
    def copy_text(self):
        """Copy selected text"""
        try:
            self.text_editor.event_generate("<<Copy>>")
            self.status_label.config(text="Texto copiado")
        except:
            pass
    
    def paste_text(self):
        """Paste text from clipboard"""
        try:
            self.text_editor.event_generate("<<Paste>>")
            self.status_label.config(text="Texto pegado")
        except:
            pass
    
    def run_python(self):
        """Run the current Python file"""
        if not self.current_file or not self.current_file.endswith('.py'):
            messagebox.showwarning("Advertencia", "Guarda el archivo como .py antes de ejecutar")
            return
        
        if not self.file_saved:
            self.save_file()
        
        try:
            # Run the Python file in a new terminal/command prompt
            if sys.platform.startswith('win'):
                subprocess.Popen(['cmd', '/c', 'start', 'cmd', '/k', 'python', self.current_file])
            elif sys.platform.startswith('darwin'):  # macOS
                subprocess.Popen(['open', '-a', 'Terminal', self.current_file])
            else:  # Linux
                subprocess.Popen(['gnome-terminal', '--', 'python3', self.current_file])
            
            self.status_label.config(text="Ejecutando archivo Python...")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo ejecutar el archivo:\n{str(e)}")
    
    def on_text_change(self, event=None):
        """Handle text changes"""
        self.file_saved = False
        self.update_title()
        self.update_line_numbers()
    
    def update_line_numbers(self):
        """Update line numbers"""
        self.line_numbers.config(state='normal')
        self.line_numbers.delete(1.0, tk.END)
        
        # Get number of lines
        line_count = int(self.text_editor.index('end-1c').split('.')[0])
        
        # Add line numbers
        for i in range(1, line_count + 1):
            self.line_numbers.insert(tk.END, f"{i:>3}\n")
        
        self.line_numbers.config(state='disabled')
    
    def update_cursor_position(self, event=None):
        """Update cursor position in status bar"""
        cursor_pos = self.text_editor.index(tk.INSERT)
        line, column = cursor_pos.split('.')
        self.cursor_label.config(text=f"Línea: {line}, Columna: {int(column) + 1}")
    
    def update_title(self):
        """Update window title and file label"""
        if self.current_file:
            filename = os.path.basename(self.current_file)
            title = f"Python IDE - {filename}"
            if not self.file_saved:
                title += " *"
                filename += " *"
        else:
            title = "Python IDE - Sin título"
            filename = "Sin título"
            if not self.file_saved:
                title += " *"
                filename += " *"
        
        self.root.title(title)
        self.file_label.config(text=filename)
    
    def ask_save_changes(self):
        """Ask user if they want to save changes"""
        result = messagebox.askyesnocancel(
            "Guardar cambios",
            "¿Deseas guardar los cambios antes de continuar?"
        )
        
        if result is True:  # Yes
            self.save_file()
            return self.file_saved
        elif result is False:  # No
            return True
        else:  # Cancel
            return False
    
    def on_closing(self):
        """Handle window closing"""
        if not self.file_saved:
            if self.ask_save_changes():
                self.root.destroy()
        else:
            self.root.destroy()

def main():
    """Main function to run the IDE"""
    root = tk.Tk()
    ide = PythonIDE(root)
    
    # Center the window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (1200 // 2)
    y = (root.winfo_screenheight() // 2) - (800 // 2)
    root.geometry(f"1200x800+{x}+{y}")
    
    print("[v0] IDE de Python iniciado correctamente")
    print("[v0] Características disponibles:")
    print("  - Editor de texto con números de línea")
    print("  - Explorador de archivos integrado")
    print("  - Botones de herramientas (Nuevo, Abrir, Guardar, etc.)")
    print("  - Atajos de teclado (Ctrl+N, Ctrl+O, Ctrl+S, F5)")
    print("  - Ejecución de archivos Python")
    print("  - Tema oscuro")
    
    root.mainloop()

if __name__ == "__main__":
    main()

