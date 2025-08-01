import json
import tkinter as tk
from tkinter import ttk
import queue
import threading
import subprocess
from tkinter import messagebox
from FileProcessor import read_pipe_forever, write_x, stop_event

class LabyrinthVisualizer:
    def __init__(self, root, mode='auto'):
        print("[DEBUG] Visualizer starting up")
        self.root = root
        self.root.title("Labyrinth Robot Path Visualizer")
        self.mode = mode  # 'auto' or 'manual'
        
        # Initialize UI based on mode
        self.setup_ui()
        
        # --- State setup ---
        self.nodes = {}
        self.edges = []
        self.current_node = None
        self.zoom_level = 1.0
        self.data_queue = queue.Queue()

        if self.mode == 'auto':
            self.canvas.bind("<MouseWheel>", self.zoom_handler)
            self.canvas.bind("<Button-4>", self.zoom_handler)
            self.canvas.bind("<Button-5>", self.zoom_handler)
            self.canvas.bind("<Configure>", lambda e: self.canvas.focus_set())

        # Start the data stream
        self.start_data_stream()
        self.keep_running = True

    def setup_ui(self):
        """Setup UI based on current mode"""
        # Create main containers first
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.left_frame = ttk.Frame(self.main_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.right_frame = ttk.Frame(self.main_frame, width=250)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

        # Common UI elements
        ttk.Label(self.right_frame, text="Labyrinth Information", font=('Arial', 12, 'bold')).pack(pady=10, anchor='w')

        self.node_frame = ttk.LabelFrame(self.right_frame, text="Current Node")
        self.node_frame.pack(fill=tk.X, padx=5, pady=5)
        self.node_label = ttk.Label(self.node_frame, text="None")
        self.node_label.pack(pady=5, padx=5, anchor='w')

        self.dist_frame = ttk.LabelFrame(self.right_frame, text="Distance")
        self.dist_frame.pack(fill=tk.X, padx=5, pady=5)
        self.distance_label = ttk.Label(self.dist_frame, text="-")
        self.distance_label.pack(pady=5, padx=5, anchor='w')

        self.dir_frame = ttk.LabelFrame(self.right_frame, text="Possible Directions")
        self.dir_frame.pack(fill=tk.X, padx=5, pady=5)
        self.directions_label = ttk.Label(self.dir_frame, text="None")
        self.directions_label.pack(pady=5, padx=5, anchor='w')

        # Create mode-specific UI
        if self.mode == 'auto':
            self.setup_auto_ui()
        else:
            self.setup_manual_ui()

    def setup_auto_ui(self):
        """Setup UI for auto mode"""
        self.canvas = tk.Canvas(self.left_frame, bg='white')
        self.hscroll = ttk.Scrollbar(self.left_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.vscroll = ttk.Scrollbar(self.left_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.hscroll.set, yscrollcommand=self.vscroll.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vscroll.grid(row=0, column=1, sticky="ns")
        self.hscroll.grid(row=1, column=0, sticky="ew")
        self.left_frame.grid_rowconfigure(0, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)

        # Legend for auto mode
        ttk.Label(self.right_frame, text="Legend", font=('Arial', 10, 'bold')).pack(pady=(20,5), anchor='w')
        legend_frame = ttk.Frame(self.right_frame)
        legend_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Canvas(legend_frame, width=30, height=30, bg="lightblue").pack(side=tk.LEFT, padx=5)
        ttk.Label(legend_frame, text="Visited Node").pack(side=tk.LEFT, anchor='w')
        legend_frame2 = ttk.Frame(self.right_frame)
        legend_frame2.pack(fill=tk.X, padx=5, pady=5)
        tk.Canvas(legend_frame2, width=30, height=30, bg="green").pack(side=tk.LEFT, padx=5)
        ttk.Label(legend_frame2, text="Current Node").pack(side=tk.LEFT, anchor='w')
        
        # After Mapping Commands for auto mode
        ttk.Label(self.right_frame, text="After Mapping Commands", 
                font=('Arial', 10, 'bold')).pack(pady=(20,5), anchor='w')
        

        button_frame = ttk.Frame(self.right_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        

        self.labyrinth_button = ttk.Button(button_frame, text="Show Labyrinth", 
                                        command=self.show_labyrinth)
        self.labyrinth_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        

        self.part_button = ttk.Button(button_frame, text="Path from A to B",
                                    command=self.show_part_path)
        self.part_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

    def setup_manual_ui(self):
        """Setup UI for manual mode"""
        # Remove canvas if it exists (from previous auto mode)
        if hasattr(self, 'canvas'):
            self.canvas.destroy()
            del self.canvas
        
        # Create control buttons
        control_frame = ttk.Frame(self.left_frame)
        control_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Movement buttons
        btn_size = 8
        btn_style = {'width': btn_size, 'padding': 10}
        
        self.btn_forward = ttk.Button(control_frame, text="↑ Forward (W)", 
                                    command=lambda: self.send_manual_command('W'), **btn_style)
        self.btn_forward.grid(row=0, column=1, pady=5)
        
        self.btn_left = ttk.Button(control_frame, text="← Left (A)", 
                                command=lambda: self.send_manual_command('A'), **btn_style)
        self.btn_left.grid(row=1, column=0, padx=5)
        
        self.btn_right = ttk.Button(control_frame, text="→ Right (D)", 
                                command=lambda: self.send_manual_command('D'), **btn_style)
        self.btn_right.grid(row=1, column=2, padx=5)
        
        self.btn_backward = ttk.Button(control_frame, text="↓ Backward (S)", 
                                    command=lambda: self.send_manual_command('S'), **btn_style)
        self.btn_backward.grid(row=2, column=1, pady=5)
        
        self.btn_rotate_back = ttk.Button(control_frame, text="↻ Rotate Back (B)", 
                                        command=lambda: self.send_manual_command('B'), 
                                        style='Special.TButton')
        self.btn_rotate_back.grid(row=3, column=0, columnspan=3, pady=10, sticky='ew')

        # Configure style for special buttons
        style = ttk.Style()
        style.configure('Special.TButton', foreground='white', background='blue', 
                    font=('Arial', 10, 'bold'))
        
        # Make buttons expand evenly
        for i in range(3):
            control_frame.columnconfigure(i, weight=1)
        for i in range(4):
            control_frame.rowconfigure(i, weight=1)

        # Add Switch to Auto button in the legend section
        legend_frame = ttk.Frame(self.right_frame)
        legend_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.switch_auto_btn = ttk.Button(legend_frame, text="Switch to Auto Mode",
                                        command=self.switch_to_auto,
                                        style='Switch.TButton')
        self.switch_auto_btn.pack(fill=tk.X, pady=5)
        
        style.configure('Switch.TButton', foreground='white', background='green',
                    font=('Arial', 10, 'bold'))

    def switch_to_auto(self):
        """Switch from manual to auto mode"""
        try:
            # Send 'a' command to backend
            fifo_path = '/root/LegoRobotOutputFile/frontend_sending_command'
            ssh_command = [
                "ssh",
                "root@172.16.16.111",
                f"echo 'a' > {fifo_path}"
            ]
            subprocess.run(ssh_command, check=True, timeout=5)
            print("[INFO] Sent 'a' command to switch to auto mode")
            
            # Clear current UI
            for widget in self.main_frame.winfo_children():
                widget.destroy()
            
            # Reinitialize as auto mode
            self.mode = 'auto'
            self.setup_ui()
            self.draw_tree()  # Initial draw if needed
            
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to switch to auto mode: {e}")
            messagebox.showerror("Error", f"Failed to switch to auto mode: {e}")

    def send_manual_command(self, command):
        """Send manual movement command to backend"""
        try:
            fifo_path = '/root/LegoRobotOutputFile/frontend_sending_command'
            ssh_command = [
                "ssh",
                "root@172.16.16.111",
                f"echo '{command}' > {fifo_path}"
            ]
            subprocess.run(ssh_command, check=True, timeout=5)
            print(f"[INFO] Sent manual command: {command}")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to send manual command: {e}")
            messagebox.showerror("Error", f"Failed to send command: {e}")

    def start_data_stream(self):
        """Start the thread to read data from the pipe"""
        print("[PIPE DEBUG] Starting data stream thread")
        self.reader_thread = threading.Thread(
            target=read_pipe_forever,
            args=(self.data_queue,),
            daemon=True
        )
        self.reader_thread.start()
        self.root.after(100, self.process_queue)

    def process_queue(self):
        """Process messages from the queue"""
        try:
            while not self.data_queue.empty():
                line = self.data_queue.get_nowait()
                print(f"[RAW RECEIVED] {line}")
                
                if line == 'x':
                    print("Received stop signal")
                    self.on_close()
                    return
                
                try:
                    print(f"[DEBUG] Attempting to parse: {repr(line)}")
                    data = json.loads(line)
                    print(f"[DEBUG] Parsed JSON: {data}")
                    # Check for finished labyrinth message
                    if data.get("finishedLabyrinth") == "true":
                        print("[INFO] Received labyrinth completion signal")
                        self.handle_labyrinth_completion()
                        continue
                    self.process_data(data)
                except json.JSONDecodeError:
                    print(f"[INFO] Plain message received: {line}")
                    self.node_label.config(text=f"Message: {line}")
                except Exception as e:
                    print(f"[CRITICAL] Unexpected error: {str(e)}")
                    raise

        except queue.Empty:
            pass

        if not stop_event.is_set():
            self.root.after(100, self.process_queue)

    def handle_labyrinth_completion(self):
        """Handle the labyrinth completion signal"""
        print("[INFO] Labyrinth mapping completed")
        # Update UI to show completion
        self.node_label.config(text="Mapping Complete!")
        # Stop the data stream
        stop_event.set()
        # Show completion message
        messagebox.showinfo("Mapping Complete", "The robot has finished mapping the labyrinth")

    def process_data(self, data):
        print(f"[DEBUG] Processing node data: {data}")
        
        node_id = data.get("node_id")
        if node_id:
            self.node_label.config(text=f"Current Node: {node_id}")
            self.current_node = node_id

            parent_id = node_id[:-1] if node_id != "Rt_" else None
            if parent_id == "Rt" and node_id.startswith("Rt_"):
                parent_id = "Rt_"

            if node_id not in self.nodes:
                self.nodes[node_id] = {"parent": parent_id}

            # Only add edge and redraw if this is a new edge
            if parent_id and (parent_id, node_id) not in self.edges:
                self.edges.append((parent_id, node_id))
                self.draw_tree()

        else:
            self.node_label.config(text="Node: unknown")

        if "current_direction" in data:
            self.directions_label.config(text=f"Current Direction: {data['current_direction']}")

        if "distance" in data:
            self.distance_label.config(text=f"Distance: {data['distance']}")
        else:
            self.distance_label.config(text="Distance: -")

        self.root.update_idletasks()


    def zoom_handler(self, event):
        """Handle mouse wheel zooming"""
        if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
            zoom_factor = 1.1
        elif event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
            zoom_factor = 0.9
        else:
            return

        if 0.2 < self.zoom_level * zoom_factor < 5.0:
            self.zoom_level *= zoom_factor
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            self.canvas.scale("all", x, y, zoom_factor, zoom_factor)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def draw_tree(self):
        print(f"[DEBUG] Canvas size: {self.canvas.winfo_width()}x{self.canvas.winfo_height()}")
        print(f"[DEBUG] Drawing tree with nodes: {self.nodes.keys()} and edges: {self.edges}")

        # Check canvas size
        if self.canvas.winfo_width() < 10 or self.canvas.winfo_height() < 10:
            print("[WARNING] Canvas too small, rescheduling draw")
            self.root.after(100, self.draw_tree)
            return
        
        print(f"[DEBUG] All nodes: {list(self.nodes.keys())}")
        print(f"[DEBUG] All edges: {self.edges}")

        """Draw the tree visualization"""
        self.canvas.delete("all")
        if not self.nodes:
            return

        node_positions = {}
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        root_x, root_y = canvas_width / 2, 50
        node_positions["Rt_"] = (root_x, root_y)
        queue = [("Rt_", root_x, root_y, canvas_width)]
        vertical_spacing = 100

        while queue:
            node_id, parent_x, parent_y, width = queue.pop(0)
            children = [child for (parent, child) in self.edges if parent == node_id]
            if not children:
                continue

            child_y = parent_y + vertical_spacing
            directions = [child_id[-1] for child_id in children]
            f_count, l_count, r_count = directions.count('F'), directions.count('L'), directions.count('R')
            total_directions = max(1, f_count + l_count + r_count)
            section_width = width / total_directions
            horizontal_spread = width / 6
            f_index, l_index, r_index = l_count, 0, l_count + f_count

            for child_id in children:
                direction = child_id[-1]
                if direction == 'F':
                    child_x = parent_x
                elif direction == 'L':
                    child_x = parent_x - horizontal_spread + l_index * section_width
                    l_index += 1
                elif direction == 'R':
                    child_x = parent_x + horizontal_spread - (total_directions - r_index - 1) * section_width
                    r_index += 1
                node_positions[child_id] = (child_x, child_y)
                queue.append((child_id, child_x, child_y, width * 0.6))

        for parent_id, child_id in self.edges:
            if parent_id in node_positions and child_id in node_positions:
                x1, y1 = node_positions[parent_id]
                x2, y2 = node_positions[child_id]
                dx, dy = x2 - x1, y2 - y1
                length = (dx**2 + dy**2)**0.5
                if length > 0:
                    shorten_by = 15
                    if length > 2 * shorten_by:
                        x1 += dx * shorten_by / length
                        y1 += dy * shorten_by / length
                        x2 -= dx * shorten_by / length
                        y2 -= dy * shorten_by / length
                self.canvas.create_line(x1, y1, x2, y2, fill="black", width=2)

        for node_id, (x, y) in node_positions.items():
            color = "green" if node_id == self.current_node else "lightblue"
            self.canvas.create_oval(x-15, y-15, x+15, y+15, fill=color, outline="black")
            display_text = node_id.split('_')[-1] if node_id != "Rt_" else "Rt"
            self.canvas.create_text(x, y, text=display_text, font=('Arial', 10))

        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        print("[DEBUG] Finished drawing tree")
        self.auto_zoom_to_fit()

    def auto_zoom_to_fit(self):
        """Zoom to fit all nodes if necessary"""
        bbox = self.canvas.bbox("all")
        if not bbox:
            return
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        tree_width = bbox[2] - bbox[0]
        tree_height = bbox[3] - bbox[1]
        padding = 50
        scale_x = (canvas_width - 2 * padding) / max(1, tree_width)
        scale_y = (canvas_height - 2 * padding) / max(1, tree_height)
        new_scale = min(scale_x, scale_y, 1.0)
        if new_scale < self.zoom_level:
            self.canvas.scale("all", 0, 0, new_scale / self.zoom_level, new_scale / self.zoom_level)
            self.zoom_level = new_scale
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))


    def on_close(self):
        print("[INFO] Closing application...")
        print("[PIPE DEBUG] Sending 'x' termination signal to backend")
        write_x()  # Send the termination signal to the backend

        print("[PIPE DEBUG] Setting stop_event and closing pipe")
        stop_event.set()

        # Give the pipe reader thread a moment to close
        print("[PIPE DEBUG] Waiting for reader thread to finish...")
        self.reader_thread.join(timeout=1.0)
        if self.reader_thread.is_alive():
            print("[PIPE WARNING] Reader thread did not exit cleanly")
        else:
            print("[PIPE DEBUG] Reader thread exited successfully")

        self.root.quit()
        self.root.destroy()
        print("[PIPE DEBUG] Application fully closed")

    def show_labyrinth(self):
        """Switch to labyrinth visualization"""
        self.draw_labyrinth()
        
        # Add a back button to return to tree view
        back_button = ttk.Button(self.right_frame, 
                            text="Back to Tree",
                            command=self.show_tree_view)
        back_button.pack(pady=10)

    def show_tree_view(self):
        """Switch back to tree visualization"""
        # Clear any existing back button
        for widget in self.right_frame.winfo_children():
            if isinstance(widget, ttk.Button) and widget["text"] == "Back to Tree":
                widget.destroy()
        
        # Redraw the tree
        self.draw_tree()

    def draw_labyrinth(self):
        """Draw a grid showing the robot's complete path from start"""
        self.canvas.delete("all")
        if not self.nodes:
            return

        # Movement directions (N=0, E=1, S=2, W=3)
        directions = [(0, -1), (1, 0), (0, 1), (-1, 0)]
        
        # Starting position and direction
        x, y = 0, 0
        current_dir = 2  # Initial direction (South)
        visited = {(x, y): 'Start'}  # Cells and their labels
        path = [(x, y, 'Start')]  # Full path history
        
        # Process all nodes to build the path
        for node_id in sorted(self.nodes.keys(), key=lambda x: len(x)):
            if node_id == "Rt_":
                continue
                
            # Reset to start for each node's path calculation
            cx, cy = 0, 0
            dir = current_dir
            moves = node_id.split('_')[-1]
            
            # Execute each movement in sequence
            for move in moves:
                if move == 'F':
                    dx, dy = directions[dir]
                    cx += dx
                    cy += dy
                elif move == 'R':
                    dir = (dir + 1) % 4  # Turn right first
                    dx, dy = directions[dir]
                    cx += dx
                    cy += dy
                elif move == 'L':
                    dir = (dir - 1) % 4  # Turn left first
                    dx, dy = directions[dir]
                    cx += dx
                    cy += dy
            
            # Record final position
            visited[(cx, cy)] = moves
            path.append((cx, cy, moves))

        # Calculate grid dimensions
        all_x = [x for x,y in visited.keys()]
        all_y = [y for x,y in visited.keys()]
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        
        # Add padding
        min_x -= 1
        max_x += 1
        min_y -= 1
        max_y += 1

        # Calculate drawing parameters
        grid_width = max_x - min_x + 1
        grid_height = max_y - min_y + 1
        cell_size = min(
            self.canvas.winfo_width() // grid_width,
            self.canvas.winfo_height() // grid_height,
            40
        )
        start_x = (self.canvas.winfo_width() - grid_width * cell_size) // 2
        start_y = (self.canvas.winfo_height() - grid_height * cell_size) // 2

        # Draw all cells
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                x1 = start_x + (x - min_x) * cell_size
                y1 = start_y + (y - min_y) * cell_size
                x2 = x1 + cell_size
                y2 = y1 + cell_size
                
                if (x, y) in visited:
                    label = visited[(x, y)]
                    color = "red" if label == "Start" else "lightblue"
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black")
                    self.canvas.create_text((x1+x2)//2, (y1+y2)//2, text=label, font=('Arial', 10))
                else:
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill="gray", outline="black")


        self.canvas.configure(scrollregion=self.canvas.bbox("all"))



    def show_part_path(self):
        """Show dialog to select both start and end points"""
        if not self.nodes:
            messagebox.showwarning("Warning", "No nodes available to select")
            return

        # First check if pipes exist
        try:
            # Check if command pipe exists
            check_pipe_cmd = [
                "ssh",
                "root@172.16.16.111",
                "[ -p /root/LegoRobotOutputFile/frontend_sending_command ] && echo exists || echo missing"
            ]
            result = subprocess.run(check_pipe_cmd, check=True, capture_output=True, text=True, timeout=5)
            if "missing" in result.stdout:
                messagebox.showerror("Error", "Command pipe not found on backend")
                return

            # Check if points pipe exists
            check_points_pipe = [
                "ssh",
                "root@172.16.16.111",
                "[ -p /root/LegoRobotOutputFile/frontend_sending_a_and_b ] && echo exists || echo missing"
            ]
            result = subprocess.run(check_points_pipe, check=True, capture_output=True, text=True, timeout=5)
            if "missing" in result.stdout:
                messagebox.showerror("Error", "Points pipe not found on backend")
                return

            # Send 'y' to backend to initiate path selection mode
            ssh_command = [
                "ssh",
                "root@172.16.16.111",
                "echo 'y' > /root/LegoRobotOutputFile/frontend_sending_command"
            ]
            subprocess.run(ssh_command, check=True, timeout=5)
            print("[INFO] Successfully sent 'y' to backend")

        except subprocess.TimeoutExpired:
            print("[ERROR] Timeout while checking pipes")
            messagebox.showerror("Error", "Timeout while checking backend pipes")
            return
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to check pipes: {e}")
            messagebox.showerror("Error", f"Failed to check backend pipes: {e}")
            return

        # Rest of the method remains the same...
        self.dialog = tk.Toplevel(self.root)
        self.dialog.title("Select Path Points")
        self.dialog.geometry("400x300")
        
        self.node_list = sorted(self.nodes.keys(), key=lambda x: len(x))
        
        ttk.Label(self.dialog, text="Select Start Point (A):").pack(pady=(10,0))
        self.point_a_var = tk.StringVar()
        point_a_combo = ttk.Combobox(self.dialog, textvariable=self.point_a_var, 
                                values=self.node_list)
        point_a_combo.pack(pady=5)
        point_a_combo.current(0)
        
        ttk.Label(self.dialog, text="Select End Point (B):").pack(pady=(10,0))
        self.point_b_var = tk.StringVar()
        point_b_combo = ttk.Combobox(self.dialog, textvariable=self.point_b_var,
                                values=self.node_list)
        point_b_combo.pack(pady=5)
        if len(self.node_list) > 1:
            point_b_combo.current(1)
        
        send_button = ttk.Button(self.dialog, text="Send Points", command=self.send_points)
        send_button.pack(pady=20)
        

    def send_points(self):
        """Send the selected points to the backend"""
        point_a = self.point_a_var.get()
        point_b = self.point_b_var.get()
        
        if not point_a or not point_b:
            messagebox.showerror("Error", "Please select both points")
            return
        if point_a == point_b:
            messagebox.showerror("Error", "Start and end points must be different")
            return
            
        try:
            # Send the points to the readingPipePathAandB pipe
            a_and_b_pipe = '/root/LegoRobotOutputFile/frontend_sending_a_and_b'
            command = f"{point_a} {point_b}"
            
            ssh_command = [
                "ssh",
                "root@172.16.16.111",
                f"echo '{command}' > {a_and_b_pipe}"
            ]
            
            # Increase timeout to 10 seconds
            subprocess.run(ssh_command, check=True, timeout=10)
            print(f"[INFO] Successfully sent path from {point_a} to {point_b}")
            
            # Show success message and ask for confirmation
            confirm = messagebox.askyesno(
                "Confirmation", 
                f"Sent path from {point_a} to {point_b} to backend.\n"
                "Is the robot in the correct starting position?"
            )
            
            if confirm:
                # Send 'y' command to start the movement
                cmd_pipe = '/root/LegoRobotOutputFile/frontend_sending_command'
                ssh_command = [
                    "ssh",
                    "root@172.16.16.111",
                    f"echo 'y' > {cmd_pipe}"
                ]
                subprocess.run(ssh_command, check=True, timeout=5)
                print("[INFO] Sent 'y' command to start movement")
                messagebox.showinfo("Success", "Robot movement command sent")
            
            self.dialog.destroy()
            
        except subprocess.TimeoutExpired:
            print("[ERROR] Timeout while sending path points")
            messagebox.showerror("Error", 
                "Timeout while sending points to backend. Is the backend listening?")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to send path points: {e}")
            messagebox.showerror("Error", 
                f"Failed to send path points. Pipe might not exist.\nError: {e}")
            
def show_mode_selection():
    """Show initial mode selection dialog"""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    # Create mode selection dialog
    choice = messagebox.askquestion("Mode Selection", 
                                   "Choose robot operation mode:",
                                   detail="Yes for Auto mode, No for Manual mode",
                                   icon='question')
    
    mode = 'auto' if choice == 'yes' else 'manual'
    command = 'a' if choice == 'yes' else 'm'
    
    # Send the mode command to backend
    try:
        fifo_path = '/root/LegoRobotOutputFile/frontend_sending_command'
        ssh_command = [
            "ssh",
            "root@172.16.16.111",
            f"echo '{command}' > {fifo_path}"
        ]
        subprocess.run(ssh_command, check=True)
        print(f"[INFO] Successfully sent '{command}' to backend")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to send mode command: {e}")
        messagebox.showerror("Error", f"Failed to initialize mode: {e}")
        root.destroy()
        return
    
    root.destroy()
    return mode

def main():
    # Show mode selection first
    mode = show_mode_selection()
    if not mode:
        return  # Exit if mode selection failed
    
    # Create main window
    root = tk.Tk()
    root.geometry("1000x700")
    
    # Create visualizer with selected mode
    app = LabyrinthVisualizer(root, mode)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

if __name__ == "__main__":
    main()