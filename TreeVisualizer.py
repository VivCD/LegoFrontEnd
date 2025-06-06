import json
import tkinter as tk
from tkinter import ttk
import queue
import threading
import subprocess
from FileProcessor import read_pipe_forever, write_x, stop_event

class LabyrinthVisualizer:
    def __init__(self, root):
        print("[DEBUG] Visualizer starting up")
        self.root = root
        self.root.title("Labyrinth Robot Path Visualizer")

        # --- UI SETUP (unchanged) ---
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.left_frame = ttk.Frame(self.main_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.left_frame, bg='white')
        self.hscroll = ttk.Scrollbar(self.left_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.vscroll = ttk.Scrollbar(self.left_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.hscroll.set, yscrollcommand=self.vscroll.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vscroll.grid(row=0, column=1, sticky="ns")
        self.hscroll.grid(row=1, column=0, sticky="ew")
        self.left_frame.grid_rowconfigure(0, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)

        self.right_frame = ttk.Frame(self.main_frame, width=250)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

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

        ttk.Label(self.right_frame, text="Legend", font=('Arial', 10, 'bold')).pack(pady=(20,5), anchor='w')
        legend_frame = ttk.Frame(self.right_frame)
        legend_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Canvas(legend_frame, width=30, height=30, bg="lightblue").pack(side=tk.LEFT, padx=5)
        ttk.Label(legend_frame, text="Visited Node").pack(side=tk.LEFT, anchor='w')
        legend_frame2 = ttk.Frame(self.right_frame)
        legend_frame2.pack(fill=tk.X, padx=5, pady=5)
        tk.Canvas(legend_frame2, width=30, height=30, bg="green").pack(side=tk.LEFT, padx=5)
        ttk.Label(legend_frame2, text="Current Node").pack(side=tk.LEFT, anchor='w')

        # --- State setup ---
        self.nodes = {}
        self.edges = []
        self.current_node = None
        self.zoom_level = 1.0
        self.data_queue = queue.Queue()

        self.canvas.bind("<MouseWheel>", self.zoom_handler)
        self.canvas.bind("<Button-4>", self.zoom_handler)
        self.canvas.bind("<Button-5>", self.zoom_handler)
        self.canvas.bind("<Configure>", lambda e: self.canvas.focus_set())

        # Start the data stream
        self.start_data_stream()
        self.keep_running = True

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
                    data = json.loads(line)
                    print(f"[DEBUG] Parsed JSON: {data}")
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

    def process_data(self, data):
        print(f"[DEBUG] Processing node data: {data}")
        
        if "node_id" in data:
            node_id = data["node_id"]
            self.node_label.config(text=f"Current Node: {node_id}")
        else:
            self.node_label.config(text="Node: unknown")
        
        if "current_direction" in data:
            self.directions_label.config(text=f"Current Direction: {data['current_direction']}")

        if "distance" in data:
            self.distance_label.config(text=f"Distance: {data['distance']}")
        else:
            self.distance_label.config(text="Distance: -")

        if "node_id" in data:
            node_id = data["node_id"]
            if node_id not in self.nodes:
                parent_id = node_id[:-1] if node_id != "Rt_" else None
                if parent_id == "Rt" and node_id.startswith("Rt_"):
                    parent_id = "Rt_"
                self.nodes[node_id] = {"parent": parent_id}
                if parent_id:
                    self.edges.append((parent_id, node_id))

            self.current_node = node_id
            self.draw_tree()
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
        
 
def main():
    root = tk.Tk()
    root.geometry("1000x700")

    def send_initial_command():
        fifo_path = '/root/LegoRobotOutputFile/frontend_sending_command'
        ssh_command = [
            "ssh",
            "root@172.16.16.111",
            f"echo 'a' > {fifo_path}"
        ]
        try:
            subprocess.run(ssh_command, check=True)
            print("[INFO] Successfully sent 'a' to backend")
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to send 'a' to backend: {e}")
            
    send_initial_command()

    app = LabyrinthVisualizer(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

if __name__ == "__main__":
    main() 