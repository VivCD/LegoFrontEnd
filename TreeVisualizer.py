import json
import subprocess
import tkinter as tk
from tkinter import ttk
import os
from collections import defaultdict

class LabyrinthVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Labyrinth Robot Path Visualizer")
        
        # Create main container frame
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create left frame for canvas
        self.left_frame = ttk.Frame(self.main_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create canvas with scrollbars in the left frame
        self.canvas = tk.Canvas(self.left_frame, bg='white')
        
        # Add scrollbars
        self.hscroll = ttk.Scrollbar(self.left_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.vscroll = ttk.Scrollbar(self.left_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.hscroll.set, yscrollcommand=self.vscroll.set)
        
        # Grid layout for canvas and scrollbars
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vscroll.grid(row=0, column=1, sticky="ns")
        self.hscroll.grid(row=1, column=0, sticky="ew")
        
        self.left_frame.grid_rowconfigure(0, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)
        
        # Create right frame for information panel
        self.right_frame = ttk.Frame(self.main_frame, width=250)  # Fixed width for info panel
        self.right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        # Information display in the right frame
        ttk.Label(self.right_frame, text="Labyrinth Information", 
                font=('Arial', 12, 'bold')).pack(pady=10, anchor='w')
        
        # Current node info
        self.node_frame = ttk.LabelFrame(self.right_frame, text="Current Node")
        self.node_frame.pack(fill=tk.X, padx=5, pady=5)
        self.node_label = ttk.Label(self.node_frame, text="None")
        self.node_label.pack(pady=5, padx=5, anchor='w')
        
        # Distance info
        self.dist_frame = ttk.LabelFrame(self.right_frame, text="Distance")
        self.dist_frame.pack(fill=tk.X, padx=5, pady=5)
        self.distance_label = ttk.Label(self.dist_frame, text="-")
        self.distance_label.pack(pady=5, padx=5, anchor='w')
        
        # Directions info
        self.dir_frame = ttk.LabelFrame(self.right_frame, text="Possible Directions")
        self.dir_frame.pack(fill=tk.X, padx=5, pady=5)
        self.directions_label = ttk.Label(self.dir_frame, text="None")
        self.directions_label.pack(pady=5, padx=5, anchor='w')
        
        # Legend in the right frame
        ttk.Label(self.right_frame, text="Legend", 
                font=('Arial', 10, 'bold')).pack(pady=(20,5), anchor='w')
        
        legend_frame = ttk.Frame(self.right_frame)
        legend_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Canvas(legend_frame, width=30, height=30, bg="lightblue").pack(side=tk.LEFT, padx=5)
        ttk.Label(legend_frame, text="Visited Node").pack(side=tk.LEFT, anchor='w')
        
        legend_frame2 = ttk.Frame(self.right_frame)
        legend_frame2.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Canvas(legend_frame2, width=30, height=30, bg="green").pack(side=tk.LEFT, padx=5)
        ttk.Label(legend_frame2, text="Current Node").pack(side=tk.LEFT, anchor='w')
        
        # Tree data structure and other initialization remains the same...
        self.nodes = {}
        self.edges = []
        self.current_node = None
        
        # Zoom and scroll setup remains the same...
        self.zoom_level = 1.0
        self.canvas.bind("<MouseWheel>", self.zoom_handler)
        self.canvas.bind("<Button-4>", self.zoom_handler)
        self.canvas.bind("<Button-5>", self.zoom_handler)
        self.canvas.bind("<Configure>", lambda e: self.canvas.focus_set())
        
        # Start the file watcher
        self.watch_file()
    
    def zoom_handler(self, event):
        """Handle mouse wheel zooming"""
        if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
            # Zoom in
            zoom_factor = 1.1
        elif event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
            # Zoom out
            zoom_factor = 0.9
        else:
            return
        
        # Limit zoom levels
        if 0.2 < self.zoom_level * zoom_factor < 5.0:
            self.zoom_level *= zoom_factor
            
            # Get current scroll region
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            
            # Apply zoom
            self.canvas.scale("all", x, y, zoom_factor, zoom_factor)
            
            # Update scroll region
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def watch_file(self):
        """Read the output file locally with better error handling"""
        file_path = '/home/vivi/Desktop/LegoRobotOutputFile/outputFile.txt'
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    content = f.read().strip()
                    if content:
                        try:
                            data = json.loads(content)
                            self.process_data(data)
                        except json.JSONDecodeError:
                            print("Invalid JSON format")
            except IOError as e:
                print(f"Error reading file: {e}")
        else:
            print("Waiting for output file...")
        
        self.root.after(100, self.watch_file)
    
    def process_data(self, data):
        """Process new node data and update visualization"""
        node_id = data["node_id"]
        
        # Update information display
        self.node_label.config(text=f"Current Node: {node_id}")
        self.distance_label.config(text=f"Distance: {data['distance']}")
        directions = ", ".join(data["possible_ways"].keys())
        self.directions_label.config(text=f"Possible Directions: {directions}")
        
        # Build tree structure
        if node_id not in self.nodes:
            # Determine parent (all nodes except root have a parent)
            if node_id == "Rt_":
                parent_id = None
            else:
                # Remove only the last direction (1 character)
                parent_id = node_id[:-1]
                
                # Special case: if we're at root with just one direction (e.g., "Rt_F")
                if parent_id == "Rt" and node_id.startswith("Rt_"):
                    parent_id = "Rt_"
            
            # Add to tree structure
            self.nodes[node_id] = {"parent": parent_id}
            
            if parent_id is not None and parent_id in self.nodes:
                self.edges.append((parent_id, node_id))
        
        self.current_node = node_id
        self.draw_tree()
    
    def draw_tree(self):
        """Draw the tree visualization with directional placement"""
        self.canvas.delete("all")
        
        if not self.nodes:
            return
        
        # Calculate positions with directional placement
        node_positions = {}
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Position the root node
        root_x = canvas_width / 2
        root_y = 50
        node_positions["Rt_"] = (root_x, root_y)
        
        # Process nodes level by level
        processed_nodes = {"Rt_"}
        
        # We'll process nodes in BFS order to calculate positions
        queue = [("Rt_", root_x, root_y, canvas_width)]

        vertical_spacing = 100
        
        while queue:
            node_id, parent_x, parent_y, width = queue.pop(0)
            
            # Find all children of this node
            children = [child for (parent, child) in self.edges if parent == node_id]
            
            if not children:
                continue
                
            # Calculate base y position for children
            child_y = parent_y + vertical_spacing
            
            # Calculate x positions based on directions
            directions = [child_id[-1] for child_id in children]
            
            # Count how many of each direction we have
            f_count = directions.count('F')
            l_count = directions.count('L')
            r_count = directions.count('R')
            
            # Calculate spacing - we'll divide the available width proportionally
            total_directions = max(1, f_count + l_count + r_count)
            section_width = width / total_directions

            horizontal_spread = width / 6
            
            # Position each child based on its direction
            f_index = l_count  # Forward nodes start after L nodes
            l_index = 0
            r_index = l_count + f_count  # Right nodes come after L and F
            
            for child_id in children:
                direction = child_id[-1]
                
                if direction == 'F':
                    # Forward goes in the middle
                    child_x = parent_x
                elif direction == 'L':
                    # Left goes to the left side
                    child_x = parent_x - horizontal_spread + l_index * (section_width)
                    l_index += 1
                elif direction == 'R':
                    # Right goes to the right side
                    child_x = parent_x + horizontal_spread - (total_directions - r_index - 1) * (section_width)
                    r_index += 1
                
                node_positions[child_id] = (child_x, child_y)
                queue.append((child_id, child_x, child_y, width * 0.6))  # Reduce width for next level
                processed_nodes.add(child_id)
        
        # Draw edges first (so they're underneath nodes)
        for parent_id, child_id in self.edges:
            if parent_id in node_positions and child_id in node_positions:
                x1, y1 = node_positions[parent_id]
                x2, y2 = node_positions[child_id]
                
                # Draw shorter lines by moving the endpoints closer to the nodes
                # Calculate direction vector
                dx = x2 - x1
                dy = y2 - y1
                length = (dx**2 + dy**2)**0.5
                
                if length > 0:
                    # Shorten line by 15 pixels at both ends (adjust this value as needed)
                    shorten_by = 15
                    if length > 2*shorten_by:
                        x1 = x1 + dx*shorten_by/length
                        y1 = y1 + dy*shorten_by/length
                        x2 = x2 - dx*shorten_by/length
                        y2 = y2 - dy*shorten_by/length
                
                self.canvas.create_line(x1, y1, x2, y2, fill="black", width=2)
        
        # Draw nodes
        for node_id, (x, y) in node_positions.items():
            color = "green" if node_id == self.current_node else "lightblue"
            self.canvas.create_oval(x-15, y-15, x+15, y+15, fill=color, outline="black")
            
            # Display just the last direction (or 'Rt' for root)
            display_text = node_id.split('_')[-1] if node_id != "Rt_" else "Rt"
            self.canvas.create_text(x, y, text=display_text, font=('Arial', 10))
        
        # Add legend
        legend_x = 20
        legend_y = 20
        self.canvas.create_rectangle(legend_x, legend_y, legend_x+30, legend_y+30, fill="lightblue")
        self.canvas.create_text(legend_x+50, legend_y+15, text="Visited Node", anchor=tk.W)
        
        self.canvas.create_rectangle(legend_x, legend_y+40, legend_x+30, legend_y+70, fill="green")
        self.canvas.create_text(legend_x+50, legend_y+55, text="Current Node", anchor=tk.W)
        
        # Update scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # Auto-zoom to fit if needed
        self.auto_zoom_to_fit()
    
    def auto_zoom_to_fit(self):
        """Automatically adjust zoom to fit the tree in the visible area"""
        # Get the bounding box of all items
        bbox = self.canvas.bbox("all")
        if not bbox:
            return
            
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Calculate required scaling
        tree_width = bbox[2] - bbox[0]
        tree_height = bbox[3] - bbox[1]
        
        # Add some padding
        padding = 50
        scale_x = (canvas_width - 2*padding) / max(1, tree_width)
        scale_y = (canvas_height - 2*padding) / max(1, tree_height)
        new_scale = min(scale_x, scale_y, 1.0)  # Don't scale up beyond 1.0
        
        # Only zoom out if needed, never zoom in automatically
        if new_scale < self.zoom_level:
            self.zoom_level = new_scale
            self.canvas.scale("all", 0, 0, new_scale/self.zoom_level, new_scale/self.zoom_level)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

def main():
    root = tk.Tk()
    root.geometry("1000x700")  # Slightly larger default window
    app = LabyrinthVisualizer(root)
    root.mainloop()

if __name__ == "__main__":
    main()