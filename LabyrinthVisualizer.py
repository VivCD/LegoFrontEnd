import json

import tkinter as tk
import threading
import queue
import subprocess
from tkinter import ttk, messagebox
from collections import defaultdict
from FileProcessor import read_pipe_forever, write_x, stop_event  # Import from your existing file

class StartupDialog:
    def __init__(self, root):
        self.root = root
        self.root.title("Robot Placement")
        # Add this to ensure the window can expand
        self.root.pack_propagate(False)

        
        # Default grid size (9x9 for 282cm/30cm)
        self.grid_size = 9
        self.direction = 0  # Default direction (0=Up, 1=Right, 2=Down, 3=Left)

        # Create main container with padding
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create the dialog content
        ttk.Label(root, text="Set Initial Position", font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Position Frame
        pos_frame = ttk.Frame(main_frame)
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
        dir_frame = ttk.LabelFrame(main_frame, text="Initial Direction")
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
        
        # Mode selection
        mode_frame = ttk.LabelFrame(main_frame, text="Control Mode")
        mode_frame.pack(pady=10)
        
        # In StartupDialog.__init__():
        self.mode_var = tk.StringVar(value="Auto Mode")  # Changed from "Auto"
        ttk.Radiobutton(mode_frame, text="Auto Mode", variable=self.mode_var, 
                    value="Auto Mode").pack(anchor='w', padx=5)  # Changed value
        ttk.Radiobutton(mode_frame, text="Manual Mode", variable=self.mode_var, 
                    value="Manual Mode").pack(anchor='w', padx=5)  # Changed value
        # Start Button
        ttk.Button(main_frame, text="Start Simulation", command=self.start_simulation).pack(pady=(20, 10), fill=tk.X)
        
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
                # Use the mode value directly (it's already "Auto Mode" or "Manual Mode")
                self.result = (x, y, self.direction, self.mode_var.get())
                self.root.destroy()
            else:
                tk.messagebox.showerror("Error", "Position must be between 0 and 8")
        except ValueError:
            tk.messagebox.showerror("Error", "Please enter valid numbers")

class LabyrinthGridVisualizer:
    def __init__(self, root, start_x, start_y, start_direction, start_mode):
        self.root = root
        self.root.title("Labyrinth Grid Visualizer")
        
        # Grid parameters
        self.cell_size = 60  # pixels per cell (30cm)
        self.grid_cells = 9   # 282cm / 30cm ≈ 9.4 → 9 cells
        self.robot_x = start_x
        self.robot_y = start_y
        self.robot_direction = start_direction  # 0=Up, 1=Right, 2=Down, 3=Left
        
        # Initialize mode
        self.mode_var = tk.StringVar(value=start_mode)
        
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
        self.root.bind('w', lambda e: self.manual_move("forward"))
        self.root.bind('a', lambda e: self.manual_move("left"))
        self.root.bind('d', lambda e: self.manual_move("right"))
        self.root.bind('s', lambda e: self.manual_move("backward"))
        self.root.bind('b', lambda e: self.manual_move("rotate_back")) 
        
        # Data streaming setup
        self.data_queue = queue.Queue()
        self.start_data_stream()
        
        self.auto_running = True if start_mode == "Auto Mode" else False

        # Initial drawing
        self.draw_grid()

    def start_data_stream(self):
        """Start the thread to read data from the pipe"""
        print("[DEBUG] Starting data stream thread")
        self.reader_thread = threading.Thread(
            target=read_pipe_forever,
            args=(self.data_queue,),
            daemon=True
        )
        self.reader_thread.start()
        print("[DEBUG] Started reader thread, beginning queue processing")
        self.root.after(100, self.process_queue)

    def process_queue(self):
        """Process messages from the queue"""
        try:
            while not self.data_queue.empty():
                line = self.data_queue.get_nowait()
                print(f"[DEBUG] Raw data received: {line}")
                
                if line == 'x':
                    self.on_close()
                    return
                
                try:
                    # Skip non-JSON status messages
                    if line.startswith(('Started', 'Writing', 'Done', 'Test', 'Reset', 'Intersection')):
                        print(f"[DEBUG] Skipping status message: {line}")
                        continue
                        
                    data = json.loads(line)
                    print(f"[DEBUG] Parsed JSON data: {data}")
                    self.process_sensor_data(data)
                except json.JSONDecodeError as e:
                    print(f"[ERROR] Failed to parse JSON from: {line}\nError: {e}")
                except Exception as e:
                    print(f"[ERROR] Processing error: {str(e)}")
        
        except queue.Empty:
            pass
        
        if not stop_event.is_set():
            self.root.after(100, self.process_queue)

    def set_mode(self):
        """Enable/disable manual controls based on mode"""
        if self.mode_var.get() == "Manual Mode":
            for btn in [self.btn_forward, self.btn_left, self.btn_right, self.btn_backward]:
                btn.configure(state=tk.NORMAL)
            self.auto_running = False
        else:
            for btn in [self.btn_forward, self.btn_left, self.btn_right, self.btn_backward]:
                btn.configure(state=tk.DISABLED)
            self.auto_running = True


    def get_direction_string(self):
        """Get string representation of current direction"""
        directions = {0: "Up", 1: "Right", 2: "Down", 3: "Left"}
        return directions.get(self.robot_direction, "Unknown")

    def create_control_panel(self):
        """Create all control panel elements"""
        # Mode selection
        ttk.Label(self.right_frame, text="Control Mode", font=('Arial', 12, 'bold')).pack(pady=10, anchor='w')

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

        self.btn_rotate_back = ttk.Button(self.manual_frame, text="Rotate Back (B)", 
                                        command=lambda: self.manual_move("rotate_back"))
        self.btn_rotate_back.pack(pady=2, fill=tk.X)
        
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
    
    def process_sensor_data(self, data):
        """Process sensor data from the pipe"""
        print(f"Processing data: {data}")
        
        # Extract information from data
        node_id = data.get("node_id", "")
        possible_ways = data.get("possible_ways", {})
        distance = data.get("distance", "30.000000")
        current_direction = data.get("current_direction", "0")
        
        # Update robot direction if provided
        if current_direction:
            try:
                self.robot_direction = int(current_direction) % 4
            except ValueError:
                pass
        
        self.last_distance = distance
        
        # Update available moves
        self.update_available_cells(possible_ways)
        
        # Only process movement if in Auto Mode
        if self.mode_var.get() == "Auto Mode" and node_id:
            # Movement logic for your specific node format
            if node_id == "Rt_":
                # Root node - no movement yet
                self.last_node_id = node_id
            elif node_id.startswith("Rt_"):
                # Extract movement sequence
                moves = node_id[3:]  # Get everything after "Rt_"
                
                # Only process if we have new movements
                if hasattr(self, 'last_node_id'):
                    last_moves = self.last_node_id[3:] if self.last_node_id.startswith("Rt_") else ""
                    if len(moves) > len(last_moves):
                        new_move = moves[-1]  # Get the last move
                        if new_move == 'F':
                            self.perform_move("forward")
                        elif new_move == 'L':
                            self.perform_move("left")
                        elif new_move == 'R':
                            self.perform_move("right")
                
                self.last_node_id = node_id
        
        # Update UI
        self.position_label.config(text=f"Position: ({self.robot_x}, {self.robot_y})")
        self.direction_label.config(text=f"Direction: {self.get_direction_string()}")
        available_text = ", ".join([f"{k}:{v}" for k, v in possible_ways.items()])
        self.available_label.config(text=f"Available: {available_text}")
        self.draw_grid()

    def perform_move(self, direction):
        print(f"Attempting move: {direction}")
        
        old_x, old_y = self.robot_x, self.robot_y
        old_direction = self.robot_direction
        
        try:
            # Mark current position as visited before moving
            if self.grid[self.robot_x][self.robot_y] == 3:  # Only if current position
                self.mark_position(self.robot_x, self.robot_y, 1)  # Mark as visited
            
            # Handle movement or turning
            new_x, new_y = self.robot_x, self.robot_y
            cells_to_move = 1  # Default to 1 cell (30cm)
            
            # Check if we have distance information
            if hasattr(self, 'last_distance'):
                distance = float(self.last_distance)
                cells_to_move = int(distance / 30)  # Convert cm to cells (30cm per cell)
                cells_to_move = max(1, min(cells_to_move, 2))  # Limit to 1-2 cells
            
            if direction == "forward":
                # Calculate new position based on current direction and distance
                if self.robot_direction == 0:    # Up
                    # Mark all cells in path as visited
                    for i in range(1, cells_to_move + 1):
                        self.mark_position(self.robot_x, self.robot_y - i, 1)
                    new_y -= cells_to_move
                elif self.robot_direction == 1:  # Right
                    for i in range(1, cells_to_move + 1):
                        self.mark_position(self.robot_x + i, self.robot_y, 1)
                    new_x += cells_to_move
                elif self.robot_direction == 2:  # Down
                    for i in range(1, cells_to_move + 1):
                        self.mark_position(self.robot_x, self.robot_y + i, 1)
                    new_y += cells_to_move
                elif self.robot_direction == 3:  # Left
                    for i in range(1, cells_to_move + 1):
                        self.mark_position(self.robot_x - i, self.robot_y, 1)
                    new_x -= cells_to_move
                
                # For forward movement, check if path is available
                if not self.available_cells.get("forward", 0):
                    print("Cannot move forward - path not available")
                    return False
                    
                if 0 <= new_x < self.grid_cells and 0 <= new_y < self.grid_cells:
                    self.robot_x, self.robot_y = new_x, new_y
                else:
                    print("Cannot move - out of bounds")
                    return False
                    
            elif direction == "left":
                # Rotate left (counter-clockwise), no movement
                self.robot_direction = (self.robot_direction - 1) % 4
                print(f"Rotated left. New direction: {self.get_direction_string()}")
                self.direction_label.config(text=f"Direction: {self.get_direction_string()}")
                self.draw_grid()
                return True
                    
            elif direction == "right":
                # Rotate right (clockwise), no movement
                self.robot_direction = (self.robot_direction + 1) % 4
                print(f"Rotated right. New direction: {self.get_direction_string()}")
                self.direction_label.config(text=f"Direction: {self.get_direction_string()}")
                self.draw_grid()
                return True
                
            elif direction == "rotate_back":
                # Just rotate 180 degrees, do not move
                self.robot_direction = (self.robot_direction + 2) % 4
                print(f"Rotated 180 degrees. New direction: {self.get_direction_string()}")
                self.direction_label.config(text=f"Direction: {self.get_direction_string()}")
                self.draw_grid()
                return True
                    
            elif direction == "backward":
                # Move back to the previous cell, without rotating
                if self.robot_direction == 0:    # Up, so go down
                    new_x, new_y = self.robot_x, self.robot_y + 1
                elif self.robot_direction == 1:  # Right, so go left
                    new_x, new_y = self.robot_x - 1, self.robot_y
                elif self.robot_direction == 2:  # Down, so go up
                    new_x, new_y = self.robot_x, self.robot_y - 1
                elif self.robot_direction == 3:  # Left, so go right
                    new_x, new_y = self.robot_x + 1, self.robot_y

                if 0 <= new_x < self.grid_cells and 0 <= new_y < self.grid_cells:
                    self.mark_position(self.robot_x, self.robot_y, 1)  # mark current as visited
                    self.robot_x, self.robot_y = new_x, new_y
                    self.mark_position(self.robot_x, self.robot_y, 3)  # mark new as current
                    print(f"Moved backward to ({self.robot_x}, {self.robot_y})")
                    return True
                else:
                    print("Cannot move backward - out of bounds")
                    return False
                        
            # Mark new position as current (blue)
            self.mark_position(self.robot_x, self.robot_y, 3)
            
            print(f"Moved {direction} {cells_to_move} cells to ({self.robot_x}, {self.robot_y}), direction: {self.robot_direction}")
            
            # Update available cells based on new position/direction
            self.update_available_cells(self.available_cells)
            
            # Update UI
            self.position_label.config(text=f"Position: ({self.robot_x}, {self.robot_y})")
            self.direction_label.config(text=f"Direction: {self.get_direction_string()}")
            self.draw_grid()
            
            return True
            
        except Exception as e:
            # Revert on error
            self.robot_x, self.robot_y = old_x, old_y
            self.robot_direction = old_direction
            print(f"Error during move: {e}")
            return False
        
    def update_available_cells(self, possible_ways):
        """Update available cells based on possible ways"""
        self.available_cells = possible_ways.copy()
        
        # First, clear only the cells that are marked as available (green)
        # but aren't in our new possible ways
        for x in range(self.grid_cells):
            for y in range(self.grid_cells):
                # Only reset cells that are available (green) and not current position
                if self.grid[x][y] == 2 and (x, y) != (self.robot_x, self.robot_y):
                    # Check if this cell should remain available
                    is_forward = (x, y) == self.get_forward_position()
                    is_left = (x, y) == self.get_left_position()
                    is_right = (x, y) == self.get_right_position()
                    
                    should_remain = (
                        (is_forward and possible_ways.get("forward", 0)) or
                        (is_left and possible_ways.get("left", 0)) or
                        (is_right and possible_ways.get("right", 0))
                    )
                    
                    if not should_remain:
                        self.grid[x][y] = 0  # Reset to unvisited
        
        # Mark new available cells
        directions = {
            "forward": self.get_forward_position(),
            "left": self.get_left_position(),
            "right": self.get_right_position()
        }
        
        for direction, (x, y) in directions.items():
            if possible_ways.get(direction, 0) and 0 <= x < self.grid_cells and 0 <= y < self.grid_cells:
                # Only mark as available if not current position and not already visited
                if (x, y) != (self.robot_x, self.robot_y) and self.grid[x][y] != 1:
                    self.mark_position(x, y, 2)  # Mark as available
        
        # Update the available label
        available_text = ", ".join([f"{k}:{v}" for k, v in possible_ways.items()])
        self.available_label.config(text=f"Available: {available_text}")
        self.draw_grid()

    def send_manual_command(self, char):
        fifo_path = '/root/LegoRobotOutputFile/frontend_sending_command'
        ssh_command = [
            "ssh",
            "root@172.16.16.111",
            f"echo '{char}' > {fifo_path}"
        ]
        try:
            result = subprocess.run(ssh_command, check=True, capture_output=True, text=True)
            print(f"[DEBUG] Sent manual command: '{char}'")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to send command. Error: {e.stderr}")
        except Exception as e:
            print(f"[ERROR] Unexpected error: {str(e)}")

    def manual_move(self, direction):
        """Handle manual movement commands"""
        if self.mode_var.get() != "Manual Mode":
            return

        # Send single-character command to backend
        char_map = {
            "forward": "w",
            "left": "a",
            "right": "d",
            "backward": "s",
            "rotate_back": "b"  
        }
        if direction in char_map:
            self.send_manual_command(char_map[direction])

        if self.perform_move(direction):
            # Update UI only if move was successful
            self.position_label.config(text=f"Position: ({self.robot_x}, {self.robot_y})")
            self.direction_label.config(text=f"Direction: {self.get_direction_string()}")
            self.draw_grid()
        else:
            messagebox.showwarning("Invalid Move", f"Cannot {direction} - path not available")

    
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

    def on_close(self):
        """Clean up when closing the application"""
        print("Closing application...")
        stop_event.set()
        write_x()  # Send termination signal to robot
        self.reader_thread.join(timeout=1.0)
        if self.reader_thread.is_alive():
            print("Warning: Reader thread did not exit cleanly")
        self.root.quit()
        self.root.destroy()

def main():
    # First show the startup dialog
    startup_root = tk.Tk()
    startup_root.geometry("400x450")
    
    # Create a style for the selected direction button
    style = ttk.Style(startup_root)
    style.configure('Selected.TButton', background='#4CAF50', foreground='white')
    
    dialog = StartupDialog(startup_root)
    startup_root.mainloop()
    
    if not dialog.result:
        return  # User closed the window without setting position
    
    # Get the selected position and direction
    start_x, start_y, start_direction, start_mode = dialog.result
    
    # Then show the main window with these settings
    main_root = tk.Tk()
    main_root.geometry("800x600")

    def send_initial_command(mode):
        fifo_path = '/root/LegoRobotOutputFile/frontend_sending_command'
        command_char = 'a' if mode == "Auto Mode" else 'm'
        ssh_command = [
            "ssh",
            "root@172.16.16.111",
            f"echo '{command_char}' > {fifo_path}"
        ]
        try:
            result = subprocess.run(ssh_command, check=True, capture_output=True, text=True)
            print(f"Successfully sent '{command_char}' start command to backend")
        except subprocess.CalledProcessError as e:
            print(f"Failed to send start command. Error: {e.stderr}")
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
    
    send_initial_command(start_mode)


    
    # Create and run visualizer
    app = LabyrinthGridVisualizer(main_root, start_x, start_y, start_direction, start_mode)
    main_root.protocol("WM_DELETE_WINDOW", app.on_close)
    main_root.mainloop()

if __name__ == "__main__":
    main()