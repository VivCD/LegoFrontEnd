import tkinter as tk
from tkinter import ttk, simpledialog

class StartupDialog:
    def __init__(self, root):
        self.root = root
        self.root.title("Robot Placement")
        
        # Default grid size (9x9 for 282cm/30cm)
        self.grid_size = 9
        self.direction = 1  # Default direction (1=Up, 2=Left, 3=Right, 4=Down)
        
        # Create the dialog content
        ttk.Label(root, text="Set Initial Position", font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Position Frame
        pos_frame = ttk.Frame(root)
        pos_frame.pack(pady=10)
        
        # X Position
        x_frame = ttk.Frame(pos_frame)
        x_frame.pack(pady=5)
        ttk.Label(x_frame, text="X Position (0-8):").pack(side=tk.LEFT)
        self.x_spinbox = ttk.Spinbox(x_frame, from_=0, to=self.grid_size-1, width=5)
        self.x_spinbox.pack(side=tk.LEFT, padx=5)
        self.x_spinbox.set(self.grid_size//2)  # Default to center
        
        # Y Position
        y_frame = ttk.Frame(pos_frame)
        y_frame.pack(pady=5)
        ttk.Label(y_frame, text="Y Position (0-8):").pack(side=tk.LEFT)
        self.y_spinbox = ttk.Spinbox(y_frame, from_=0, to=self.grid_size-1, width=5)
        self.y_spinbox.pack(side=tk.LEFT, padx=5)
        self.y_spinbox.set(self.grid_size//2)  # Default to center
        
        # Direction Selector
        dir_frame = ttk.LabelFrame(root, text="Initial Direction")
        dir_frame.pack(pady=10)
        
        # Visual direction buttons
        btn_frame = ttk.Frame(dir_frame)
        btn_frame.pack()
        
        # Create direction buttons in a cross pattern
        self.dir_btns = {}
        directions = {
            1: ("▲ Up", (1, 0)),
            2: ("◄ Left", (0, 1)),
            3: ("► Right", (2, 1)),
            4: ("▼ Down", (1, 2))
        }
        
        for dir_num, (text, pos) in directions.items():
            btn = ttk.Button(btn_frame, text=text, width=6,
                            command=lambda d=dir_num: self.set_direction(d))
            btn.grid(row=pos[1], column=pos[0], padx=5, pady=5)
            self.dir_btns[dir_num] = btn
        
        # Highlight default direction
        self.set_direction(1)
        
        # Start Button
        ttk.Button(root, text="Start Simulation", command=self.start_simulation).pack(pady=20)
        
        # Store the result
        self.result = None

    def set_direction(self, direction):
        """Update selected direction and button styles"""
        self.direction = direction
        for dir_num, btn in self.dir_btns.items():
            if dir_num == direction:
                btn.configure(style='Selected.TButton')
            else:
                btn.configure(style='TButton')

    
    def start_simulation(self):
        """Get the values and close the dialog"""
        try:
            x = int(self.x_spinbox.get())
            y = int(self.y_spinbox.get())
            
            if 0 <= x < self.grid_size and 0 <= y < self.grid_size:
                self.result = (x, y, self.direction)
                self.root.destroy()
            else:
                tk.messagebox.showerror("Error", "Position must be between 0 and 8")
        except ValueError:
            tk.messagebox.showerror("Error", "Please enter valid numbers")

class LabyrinthGridVisualizer:
    def __init__(self, root, start_x, start_y, start_direction):
        self.root = root
        self.root.title("Labyrinth Grid Visualizer")
        
        # Grid parameters - 282cm square with 30cm cells (9 cells)
        self.cell_size = 60  # pixels per cell (30cm)
        self.grid_cells = 9  # 282cm / 30cm ≈ 9.4 → 9 cells
        self.robot_x = start_x
        self.robot_y = start_y
        self.robot_direction = start_direction  # initial direction
        
        # Grid data: 0=unvisited, 1=visited, 2=available, 3=current
        self.grid = [[0 for _ in range(self.grid_cells)] for _ in range(self.grid_cells)]
        
        # Create main container
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left side - Grid Canvas
        self.canvas = tk.Canvas(self.main_frame, bg='white', 
                               width=self.cell_size*self.grid_cells, 
                               height=self.cell_size*self.grid_cells)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Right side - Control Panel (same as before)
        self.create_control_panel()
        
        # Draw the initial grid
        self.draw_grid()
    
    def create_control_panel(self):
        """Create the right-side control panel"""
        self.right_frame = ttk.Frame(self.main_frame, width=250)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        # Control Mode Section
        ttk.Label(self.right_frame, text="Control Mode", font=('Arial', 12, 'bold')).pack(pady=10, anchor='w')
        self.mode_var = tk.StringVar(value="Auto Mode")
        ttk.Radiobutton(self.right_frame, text="Auto Mode", variable=self.mode_var, 
                        value="Auto Mode").pack(anchor='w', padx=5)
        ttk.Radiobutton(self.right_frame, text="Manual Mode", variable=self.mode_var, 
                        value="Manual Mode").pack(anchor='w', padx=5)
        
        # Manual Controls Section
        ttk.LabelFrame(self.right_frame, text="Manual Controls").pack(fill=tk.X, padx=5, pady=10)
        controls_frame = ttk.Frame(self.right_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(controls_frame, text="Forward (F)").pack(side=tk.TOP, pady=2, fill=tk.X)
        ttk.Button(controls_frame, text="Left (L)").pack(side=tk.LEFT, pady=2, expand=True)
        ttk.Button(controls_frame, text="Right (R)").pack(side=tk.RIGHT, pady=2, expand=True)
        ttk.Button(controls_frame, text="Backward (B)").pack(side=tk.BOTTOM, pady=2, fill=tk.X)
        
        # Position Information Section
        info_frame = ttk.LabelFrame(self.right_frame, text="Position Information")
        info_frame.pack(fill=tk.X, padx=5, pady=10)
        
        self.position_label = ttk.Label(info_frame, text=f"Position: ({self.robot_x}, {self.robot_y})")
        self.position_label.pack(anchor='w', padx=5, pady=2)
        
        self.direction_label = ttk.Label(info_frame, text=f"Direction: {self.robot_direction}")
        self.direction_label.pack(anchor='w', padx=5, pady=2)
        
        self.available_label = ttk.Label(info_frame, text="Available: right:1, left:1, forward:1")
        self.available_label.pack(anchor='w', padx=5, pady=2)
        
        # Legend Section
        ttk.Label(self.right_frame, text="Legend", font=('Arial', 10, 'bold')).pack(pady=(20,5), anchor='w')
        self.create_legend_item("white", "Unvisited")
        self.create_legend_item("red", "Visited")
        self.create_legend_item("green", "Available")
        self.create_legend_item("blue", "Current Position")
    
    def create_legend_item(self, color, text):
        """Helper to create legend items"""
        frame = ttk.Frame(self.right_frame)
        frame.pack(fill=tk.X, padx=5, pady=2)
        tk.Canvas(frame, width=20, height=20, bg=color, bd=1, relief="solid").pack(side=tk.LEFT, padx=5)
        ttk.Label(frame, text=text).pack(side=tk.LEFT, anchor='w')
    
    def draw_grid(self):
        """Draw the grid visualization with direction indicator"""
        self.canvas.delete("all")
        
        # Draw cells
        for x in range(self.grid_cells):
            for y in range(self.grid_cells):
                screen_x = x * self.cell_size
                screen_y = y * self.cell_size
                
                # Determine cell color
                if (x, y) == (self.robot_x, self.robot_y):
                    # Draw blue square for current position
                    self.canvas.create_rectangle(
                        screen_x, screen_y,
                        screen_x + self.cell_size, screen_y + self.cell_size,
                        fill="blue", outline="black"
                    )
                    
                    # Draw direction indicator (arrow)
                    arrow_size = self.cell_size // 3
                    center_x = screen_x + self.cell_size // 2
                    center_y = screen_y + self.cell_size // 2
                    
                    if self.robot_direction == 1:  # Forward/Up
                        self.canvas.create_polygon(
                            center_x, center_y - arrow_size,
                            center_x - arrow_size//2, center_y,
                            center_x + arrow_size//2, center_y,
                            fill="white", outline="black"
                        )
                    elif self.robot_direction == 2:  # Left
                        self.canvas.create_polygon(
                            center_x - arrow_size, center_y,
                            center_x, center_y - arrow_size//2,
                            center_x, center_y + arrow_size//2,
                            fill="white", outline="black"
                        )
                    elif self.robot_direction == 3:  # Right
                        self.canvas.create_polygon(
                            center_x + arrow_size, center_y,
                            center_x, center_y - arrow_size//2,
                            center_x, center_y + arrow_size//2,
                            fill="white", outline="black"
                        )
                    elif self.robot_direction == 4:  # Backward/Down
                        self.canvas.create_polygon(
                            center_x, center_y + arrow_size,
                            center_x - arrow_size//2, center_y,
                            center_x + arrow_size//2, center_y,
                            fill="white", outline="black"
                        )
                else:
                    # Regular cell (unvisited)
                    self.canvas.create_rectangle(
                        screen_x, screen_y,
                        screen_x + self.cell_size, screen_y + self.cell_size,
                        fill="white", outline="black"
                    )

def main():
    # First show the startup dialog
    startup_root = tk.Tk()
    startup_root.geometry("350x400")
    
    # Create a style for the selected direction button
    style = ttk.Style(startup_root)
    style.configure('Selected.TButton', background='#4CAF50', foreground='white')
    
    dialog = StartupDialog(startup_root)
    startup_root.mainloop()
    
    if not dialog.result:
        return  # User closed the window without setting position
    
    # Get the selected position and direction
    start_x, start_y, start_direction = dialog.result
    
    # Then show the main window with these settings
    main_root = tk.Tk()
    main_root.geometry("800x600")
    app = LabyrinthGridVisualizer(main_root, start_x, start_y, start_direction)
    main_root.mainloop()

if __name__ == "__main__":
    main()