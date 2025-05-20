import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
from collections import defaultdict

class StartupDialog:
    def __init__(self, root):
        self.root = root
        self.root.title("Robot Placement")
        
        # Default grid size (9x9 for 282cm/30cm)
        self.grid_size = 9
        self.direction = 0  # Default direction (0=Up, 1=Right, 2=Down, 3=Left)
        
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
            0: ("▲ Up", (1, 0)),
            3: ("◄ Left", (0, 1)),
            1: ("► Right", (2, 1)),
            2: ("▼ Down", (1, 2))
        }
        
        for dir_num, (text, pos) in directions.items():
            btn = ttk.Button(btn_frame, text=text, width=6,
                            command=lambda d=dir_num: self.set_direction(d))
            btn.grid(row=pos[1], column=pos[0], padx=5, pady=5)
            self.dir_btns[dir_num] = btn
        
        # Highlight default direction
        self.set_direction(0)
        
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
        
        # Grid parameters
        self.cell_size = 60  # pixels per cell (30cm)
        self.grid_cells = 9   # 282cm / 30cm ≈ 9.4 → 9 cells
        self.robot_x = start_x
        self.robot_y = start_y
        self.robot_direction = start_direction  # 0=Up, 1=Right, 2=Down, 3=Left
        
        # Grid states: 0=unvisited, 1=visited, 2=available, 3=current
        self.grid = [[0 for _ in range(self.grid_cells)] for _ in range(self.grid_cells)]
        self.available_cells = defaultdict(int)  # Tracks available moves
        
        # Create main container
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left side - Grid Canvas
        self.canvas = tk.Canvas(self.main_frame, bg='white', 
                               width=self.cell_size*self.grid_cells, 
                               height=self.cell_size*self.grid_cells)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Right side - Control Panel
        self.right_frame = ttk.Frame(self.main_frame, width=250)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        # Create all UI elements first
        self.create_control_panel()
        
        # Initialize first position and available moves
        self.mark_position(self.robot_x, self.robot_y, 3)  # Current position
        self.update_available_cells({"right":1, "left":1, "forward":1})  # Initial available moves
        
        # Key bindings
        self.root.bind('f', lambda e: self.manual_move("forward"))
        self.root.bind('l', lambda e: self.manual_move("left"))
        self.root.bind('r', lambda e: self.manual_move("right"))
        self.root.bind('b', lambda e: self.manual_move("backward"))
        
        # File monitoring
        self.file_path = '/home/vivi/Desktop/LegoRobotOutputFile/outputFile.txt'
        self.last_mod_time = 0
        self.set_mode()
        self.draw_grid()
        self.watch_file()

    def get_direction_string(self):
        """Get string representation of current direction"""
        directions = {0: "Up", 1: "Right", 2: "Down", 3: "Left"}
        return directions.get(self.robot_direction, "Unknown")

    def create_control_panel(self):
        """Create all control panel elements"""
        # Mode selection
        ttk.Label(self.right_frame, text="Control Mode", font=('Arial', 12, 'bold')).pack(pady=10, anchor='w')
        self.mode_var = tk.StringVar(value="Auto Mode")
        ttk.Radiobutton(self.right_frame, text="Auto Mode", variable=self.mode_var, 
                       value="Auto Mode", command=self.set_mode).pack(anchor='w', padx=5)
        ttk.Radiobutton(self.right_frame, text="Manual Mode", variable=self.mode_var, 
                       value="Manual Mode", command=self.set_mode).pack(anchor='w', padx=5)
        
        # Manual controls
        self.manual_frame = ttk.LabelFrame(self.right_frame, text="Manual Controls")
        self.manual_frame.pack(fill=tk.X, padx=5, pady=10)
        
        self.btn_forward = ttk.Button(self.manual_frame, text="Forward (F)", 
                                    command=lambda: self.manual_move("forward"))
        self.btn_forward.pack(pady=2, fill=tk.X)
        
        self.btn_left = ttk.Button(self.manual_frame, text="Left (L)", 
                                 command=lambda: self.manual_move("left"))
        self.btn_left.pack(side=tk.LEFT, pady=2, expand=True)
        
        self.btn_right = ttk.Button(self.manual_frame, text="Right (R)", 
                                  command=lambda: self.manual_move("right"))
        self.btn_right.pack(side=tk.RIGHT, pady=2, expand=True)
        
        self.btn_backward = ttk.Button(self.manual_frame, text="Backward (B)", 
                                     command=lambda: self.manual_move("backward"))
        self.btn_backward.pack(pady=2, fill=tk.X)
        
        # Position info
        self.info_frame = ttk.LabelFrame(self.right_frame, text="Position Information")
        self.info_frame.pack(fill=tk.X, padx=5, pady=10)
        
        self.position_label = ttk.Label(self.info_frame, text=f"Position: ({self.robot_x}, {self.robot_y})")
        self.position_label.pack(anchor='w', padx=5, pady=2)
        
        self.direction_label = ttk.Label(self.info_frame, text=f"Direction: {self.get_direction_string()}")
        self.direction_label.pack(anchor='w', padx=5, pady=2)
        
        self.available_label = ttk.Label(self.info_frame, text="Available: right:1, left:1, forward:1")
        self.available_label.pack(anchor='w', padx=5, pady=2)
        
        # Legend
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
    
    def set_mode(self):
        """Enable/disable manual controls based on mode"""
        if self.mode_var.get() == "Manual Mode":
            for btn in [self.btn_forward, self.btn_left, self.btn_right, self.btn_backward]:
                btn.configure(state=tk.NORMAL)
        else:
            for btn in [self.btn_forward, self.btn_left, self.btn_right, self.btn_backward]:
                btn.configure(state=tk.DISABLED)
    
    def watch_file(self):
        """Monitor output file for changes"""
        try:
            if os.path.exists(self.file_path):
                mod_time = os.path.getmtime(self.file_path)
                if mod_time != self.last_mod_time:
                    self.last_mod_time = mod_time
                    self.process_sensor_file()
        except Exception as e:
            print(f"Error checking file: {e}")
        
        self.root.after(100, self.watch_file)

    def process_sensor_file(self):
        """Process the sensor data file"""
        try:
            with open(self.file_path, 'r') as f:
                content = f.read().strip()
                
                # Clean the content if needed
                if content.startswith('[') and content.endswith(']'):
                    content = content[1:-1]  # Remove brackets if present
                
                # Parse JSON data
                data = json.loads(content)
                
                # Process the data (only update available moves, ignore direction)
                possible_ways = data.get("possible_ways", {})
                self.update_available_cells(possible_ways)
                
                # Update the available paths label
                available_text = ", ".join([f"{k}:{v}" for k, v in possible_ways.items()])
                self.available_label.config(text=f"Available: {available_text}")
                
                # Force UI update
                self.draw_grid()
                
        except json.JSONDecodeError:
            print("Invalid JSON format in file")
        except IOError as e:
            print(f"Error reading file: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    def update_available_cells(self, possible_ways):
        """Update available cells based on possible ways"""
        self.available_cells = possible_ways.copy()
        
        # Clear all previously available cells
        for x in range(self.grid_cells):
            for y in range(self.grid_cells):
                if self.grid[x][y] == 2:  # Available state
                    self.grid[x][y] = 0   # Reset to unvisited
        
        # Mark new available cells
        directions = {
            "forward": self.get_forward_position(),
            "left": self.get_left_position(),
            "right": self.get_right_position()
        }
        
        for direction, (x, y) in directions.items():
            if possible_ways.get(direction, 0) and 0 <= x < self.grid_cells and 0 <= y < self.grid_cells:
                self.mark_position(x, y, 2)  # Mark as available

    def manual_move(self, direction):
        """Handle manual movement commands"""
        if self.mode_var.get() != "Manual Mode":
            return
        
        # Check if move is available (only for forward movement)
        if direction == "forward" and not self.available_cells.get("forward", 0):
            messagebox.showwarning("Invalid Move", "Cannot move forward - path not available")
            return
        elif direction in ["left", "right"] and not self.available_cells.get(direction, 0):
            messagebox.showwarning("Invalid Move", f"Cannot turn {direction} - path not available")
            return
        
        # Mark current position as visited before moving (unless it's already visited)
        if self.grid[self.robot_x][self.robot_y] != 1:
            self.mark_position(self.robot_x, self.robot_y, 1)
        
        if direction == "forward":
            if self.robot_direction == 0:    # Up
                self.robot_y -= 1
            elif self.robot_direction == 1:  # Right
                self.robot_x += 1
            elif self.robot_direction == 2:  # Down
                self.robot_y += 1
            elif self.robot_direction == 3:  # Left
                self.robot_x -= 1
        elif direction == "left":
            # Turn left (counter-clockwise)
            self.robot_direction = (self.robot_direction - 1) % 4
            # Then move forward
            if self.robot_direction == 0:    # Up
                self.robot_y -= 1
            elif self.robot_direction == 1:  # Right
                self.robot_x += 1
            elif self.robot_direction == 2:  # Down
                self.robot_y += 1
            elif self.robot_direction == 3:  # Left
                self.robot_x -= 1
        elif direction == "right":
            # Turn right (clockwise)
            self.robot_direction = (self.robot_direction + 1) % 4
            # Then move forward
            if self.robot_direction == 0:    # Up
                self.robot_y -= 1
            elif self.robot_direction == 1:  # Right
                self.robot_x += 1
            elif self.robot_direction == 2:  # Down
                self.robot_y += 1
            elif self.robot_direction == 3:  # Left
                self.robot_x -= 1
        elif direction == "backward":
            # First turn 180 degrees (reverse direction)
            self.robot_direction = (self.robot_direction + 2) % 4
            # Then move forward in the new direction
            if self.robot_direction == 0:    # Up
                self.robot_y -= 1
            elif self.robot_direction == 1:  # Right
                self.robot_x += 1
            elif self.robot_direction == 2:  # Down
                self.robot_y += 1
            elif self.robot_direction == 3:  # Left
                self.robot_x -= 1
        
        # Ensure new position is within bounds
        self.robot_x = max(0, min(self.grid_cells-1, self.robot_x))
        self.robot_y = max(0, min(self.grid_cells-1, self.robot_y))
        
        # Mark new position as current (blue) - this will override any previous state
        self.mark_position(self.robot_x, self.robot_y, 3)
        
        # Update available cells from file after moving
        self.process_sensor_file()
        
        # Update UI
        self.position_label.config(text=f"Position: ({self.robot_x}, {self.robot_y})")
        self.direction_label.config(text=f"Direction: {self.get_direction_string()}")
        self.draw_grid()
    
    def get_forward_position(self):
        """Calculate forward position based on current direction"""
        if self.robot_direction == 0:    # Up
            return self.robot_x, self.robot_y - 1
        elif self.robot_direction == 1:  # Right
            return self.robot_x + 1, self.robot_y
        elif self.robot_direction == 2:  # Down
            return self.robot_x, self.robot_y + 1
        elif self.robot_direction == 3:  # Left
            return self.robot_x - 1, self.robot_y
    
    def get_left_position(self):
        """Calculate left position based on current direction"""
        if self.robot_direction == 0:    # Up
            return self.robot_x - 1, self.robot_y
        elif self.robot_direction == 1:  # Right
            return self.robot_x, self.robot_y - 1
        elif self.robot_direction == 2:  # Down
            return self.robot_x + 1, self.robot_y
        elif self.robot_direction == 3:  # Left
            return self.robot_x, self.robot_y + 1
    
    def get_right_position(self):
        """Calculate right position based on current direction"""
        if self.robot_direction == 0:    # Up
            return self.robot_x + 1, self.robot_y
        elif self.robot_direction == 1:  # Right
            return self.robot_x, self.robot_y + 1
        elif self.robot_direction == 2:  # Down
            return self.robot_x - 1, self.robot_y
        elif self.robot_direction == 3:  # Left
            return self.robot_x, self.robot_y - 1
    
    def mark_position(self, x, y, state):
        """Mark position with specified state"""
        if 0 <= x < self.grid_cells and 0 <= y < self.grid_cells:
            self.grid[x][y] = state
    
    def draw_grid(self):
        """Draw the grid visualization with direction indicator"""
        self.canvas.delete("all")
        
        for x in range(self.grid_cells):
            for y in range(self.grid_cells):
                screen_x = x * self.cell_size
                screen_y = y * self.cell_size
                
                # Determine cell color
                if (x, y) == (self.robot_x, self.robot_y):
                    color = "blue"  # Current position
                elif self.grid[x][y] == 1:
                    color = "red"   # Visited
                elif self.grid[x][y] == 2:
                    color = "green" # Available
                else:
                    color = "white" # Unvisited
                
                # Draw cell
                self.canvas.create_rectangle(
                    screen_x, screen_y,
                    screen_x + self.cell_size, screen_y + self.cell_size,
                    fill=color, outline="black"
                )
                
                # Draw direction indicator if current position
                if (x, y) == (self.robot_x, self.robot_y):
                    arrow_size = self.cell_size // 3
                    center_x = screen_x + self.cell_size // 2
                    center_y = screen_y + self.cell_size // 2
                    
                    if self.robot_direction == 0:    # Up
                        self.canvas.create_polygon(
                            center_x, center_y - arrow_size,
                            center_x - arrow_size//2, center_y,
                            center_x + arrow_size//2, center_y,
                            fill="white", outline="black"
                        )
                    elif self.robot_direction == 1:  # Right
                        self.canvas.create_polygon(
                            center_x + arrow_size, center_y,
                            center_x, center_y - arrow_size//2,
                            center_x, center_y + arrow_size//2,
                            fill="white", outline="black"
                        )
                    elif self.robot_direction == 2:  # Down
                        self.canvas.create_polygon(
                            center_x, center_y + arrow_size,
                            center_x - arrow_size//2, center_y,
                            center_x + arrow_size//2, center_y,
                            fill="white", outline="black"
                        )
                    elif self.robot_direction == 3:  # Left
                        self.canvas.create_polygon(
                            center_x - arrow_size, center_y,
                            center_x, center_y - arrow_size//2,
                            center_x, center_y + arrow_size//2,
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