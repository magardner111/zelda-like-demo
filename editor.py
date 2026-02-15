#!/usr/bin/env python3
"""Tkinter-based map editor for the Zelda-like demo."""

import copy
import json
import os
import subprocess
import sys
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk

# ---------------------------------------------------------------------------
# Default data model
# ---------------------------------------------------------------------------

def new_map_data():
    return {
        "name": "NewMap",
        "width": 1024,
        "height": 1024,
        "layers": [
            {
                "elevation": 0,
                "bg_color": [72, 60, 50],
                "floor_regions": [],
                "wall_regions": [],
                "stairways": [],
            }
        ],
    }


# Which region types use which class in code generation
FLOOR_TYPES = {"grass", "stone"}
LIQUID_TYPES = {"water", "lava"}
OBJECT_TYPES = {"chest"}
ALL_FLOOR_TYPES = sorted(FLOOR_TYPES | LIQUID_TYPES | OBJECT_TYPES)

# Colors used for rendering regions in the editor (mirrors REGION_STATS)
REGION_COLORS = {
    "wall": (80, 80, 90),
    "grass": (50, 120, 50),
    "stone": (110, 105, 100),
    "water": (40, 80, 160),
    "lava": (200, 60, 20),
    "chest": (180, 140, 40),
}

STAIRWAY_COLOR = (200, 180, 100)


def rgb_to_hex(r, g, b):
    return f"#{r:02x}{g:02x}{b:02x}"


def hex_to_rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i+2], 16) for i in (0, 2, 4)]


# ---------------------------------------------------------------------------
# Code generation
# ---------------------------------------------------------------------------

def generate_map_code(data):
    """Generate a Python map class file from the editor's JSON data."""
    name = data.get("name", "EditorMap")
    class_name = name if name[0].isupper() else name.title()
    # Sanitise to valid Python identifier
    class_name = "".join(c for c in class_name if c.isalnum() or c == "_")
    if not class_name:
        class_name = "EditorMap"

    lines = [
        "from maps.map_base import MapBase",
        "from core.floor_layer import FloorLayer",
        "from core.stairway import Stairway, StairDirection",
        "from core.region_base import WallRegion, FloorRegion, LiquidRegion, ObjectRegion",
        "from data.region_stats import REGION_STATS",
        "",
        "",
        f"class {class_name}(MapBase):",
        "    def __init__(self):",
        f"        super().__init__(width={data['width']}, height={data['height']})",
        "",
    ]

    # Layers
    for layer in data["layers"]:
        elev = layer["elevation"]
        bg = tuple(layer["bg_color"])
        lines.append(f"        # --- Layer {elev} ---")
        lines.append(f"        layer{elev} = FloorLayer(elevation={elev}, bg_color={bg})")

        for wr in layer["wall_regions"]:
            rect = (wr["x"], wr["y"], wr["w"], wr["h"])
            lines.append(
                f'        layer{elev}.add_wall_region(WallRegion({rect}, REGION_STATS["wall"]))'
            )

        for fr in layer["floor_regions"]:
            rtype = fr["type"]
            rect = (fr["x"], fr["y"], fr["w"], fr["h"])
            if rtype in LIQUID_TYPES:
                cls = "LiquidRegion"
            elif rtype in OBJECT_TYPES:
                cls = "ObjectRegion"
            else:
                cls = "FloorRegion"
            lines.append(
                f'        layer{elev}.add_floor_region({cls}({rect}, "{rtype}", REGION_STATS["{rtype}"]))'
            )

        lines.append(f"        self.add_layer(layer{elev})")
        lines.append("")

    # Stairways (gathered from all layers)
    all_stairways = []
    for layer in data["layers"]:
        all_stairways.extend(layer.get("stairways", []))
    if all_stairways:
        lines.append("        # --- Stairways ---")
        for sw in all_stairways:
            rect = (sw["x"], sw["y"], sw["w"], sw["h"])
            direction = sw.get("direction", "left")
            lines.append(
                f"        self.add_stairway(Stairway({rect}, "
                f"from_layer={sw['from_layer']}, to_layer={sw['to_layer']}, "
                f"direction=StairDirection.{direction.upper()}))"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main editor application
# ---------------------------------------------------------------------------

class MapEditor:
    HANDLE_SIZE = 6  # pixels (in screen space)

    def __init__(self, root):
        self.root = root
        self.root.title("Map Editor")
        self.root.geometry("1280x960")

        self.data = new_map_data()
        self.filepath = None  # current JSON save path
        self.active_layer_idx = 0
        self.tool = "select"  # select | wall | floor | stairway
        self.floor_type = "grass"

        # Selection state — list of (kind, index, layer_idx) tuples
        self.selected_items = []
        self.clipboard = []  # for copy/paste

        # Drawing state
        self.drag_start = None  # map coords
        self.draw_rect = None   # (x, y, w, h) in map coords while dragging
        self.box_select_rect = None  # rubber-band rect for multi-select

        # Move / resize state
        self.move_start_mouse = None  # mouse position when move started
        self.move_start_positions = None  # original positions for multi-move
        self.resize_handle = None  # which handle is being dragged
        self.action = None  # "move" | "resize" | "draw" | "box_select" | None

        # Zoom / pan
        self.zoom = 0.7
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.pan_start = None  # (screen_x, screen_y, pan_x, pan_y)

        self._build_ui()
        self._refresh_layer_list()
        self._redraw_canvas()

    # -----------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------
    def _build_ui(self):
        # Menu bar
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New", command=self._file_new, accelerator="Ctrl+N")
        filemenu.add_command(label="Open...", command=self._file_open, accelerator="Ctrl+O")
        filemenu.add_command(label="Save", command=self._file_save, accelerator="Ctrl+S")
        filemenu.add_command(label="Save As...", command=self._file_save_as)
        filemenu.add_separator()
        filemenu.add_command(label="Export Python...", command=self._export_python)
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)

        self.root.bind("<Control-n>", lambda e: self._file_new())
        self.root.bind("<Control-o>", lambda e: self._file_open())
        self.root.bind("<Control-s>", lambda e: self._file_save())

        # Main pane
        paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # --- Left panel ---
        left = tk.Frame(paned, width=260)
        paned.add(left, minsize=260)

        # Map properties
        prop_frame = tk.LabelFrame(left, text="Map Properties", padx=4, pady=4)
        prop_frame.pack(fill=tk.X, padx=4, pady=4)

        tk.Label(prop_frame, text="Name:").grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar(value=self.data["name"])
        tk.Entry(prop_frame, textvariable=self.name_var, width=18).grid(row=0, column=1, sticky="ew")
        self.name_var.trace_add("write", lambda *_: self._on_name_change())

        tk.Label(prop_frame, text="Width:").grid(row=1, column=0, sticky="w")
        self.width_var = tk.IntVar(value=self.data["width"])
        tk.Entry(prop_frame, textvariable=self.width_var, width=18).grid(row=1, column=1, sticky="ew")
        self.width_var.trace_add("write", lambda *_: self._on_map_size_change())

        tk.Label(prop_frame, text="Height:").grid(row=2, column=0, sticky="w")
        self.height_var = tk.IntVar(value=self.data["height"])
        tk.Entry(prop_frame, textvariable=self.height_var, width=18).grid(row=2, column=1, sticky="ew")
        self.height_var.trace_add("write", lambda *_: self._on_map_size_change())

        prop_frame.columnconfigure(1, weight=1)

        # Layer selector
        layer_frame = tk.LabelFrame(left, text="Layers", padx=4, pady=4)
        layer_frame.pack(fill=tk.X, padx=4, pady=4)

        self.layer_listbox = tk.Listbox(layer_frame, height=5, exportselection=False)
        self.layer_listbox.pack(fill=tk.X)
        self.layer_listbox.bind("<<ListboxSelect>>", self._on_layer_select)

        btn_row = tk.Frame(layer_frame)
        btn_row.pack(fill=tk.X, pady=2)
        tk.Button(btn_row, text="Add", command=self._add_layer).pack(side=tk.LEFT, expand=True, fill=tk.X)
        tk.Button(btn_row, text="Remove", command=self._remove_layer).pack(side=tk.LEFT, expand=True, fill=tk.X)
        tk.Button(btn_row, text="BG Color", command=self._pick_layer_bg).pack(side=tk.LEFT, expand=True, fill=tk.X)

        # Tool selector
        self.tool_frame = tk.LabelFrame(left, text="Tool", padx=4, pady=4)
        tool_frame = self.tool_frame
        tool_frame.pack(fill=tk.X, padx=4, pady=4)

        self.tool_var = tk.StringVar(value="select")
        for t in ("select", "wall", "floor", "stairway"):
            tk.Radiobutton(tool_frame, text=t.title(), variable=self.tool_var,
                           value=t, command=self._on_tool_change).pack(anchor="w")

        # Floor type dropdown (only visible when floor tool is active)
        self.ftype_frame = tk.LabelFrame(left, text="Floor Region Type", padx=4, pady=4)

        self.ftype_var = tk.StringVar(value="grass")
        self.ftype_combo = ttk.Combobox(self.ftype_frame, textvariable=self.ftype_var,
                                        values=ALL_FLOOR_TYPES, state="readonly", width=16)
        self.ftype_combo.pack(fill=tk.X)
        self.ftype_combo.bind("<<ComboboxSelected>>", lambda e: self._on_floor_type_change())

        # Selection properties
        sel_frame = tk.LabelFrame(left, text="Selection", padx=4, pady=4)
        sel_frame.pack(fill=tk.X, padx=4, pady=4)
        self.sel_frame = sel_frame

        self.sel_x_var = tk.IntVar()
        self.sel_y_var = tk.IntVar()
        self.sel_w_var = tk.IntVar()
        self.sel_h_var = tk.IntVar()

        for i, (label, var) in enumerate([("X:", self.sel_x_var), ("Y:", self.sel_y_var),
                                           ("W:", self.sel_w_var), ("H:", self.sel_h_var)]):
            tk.Label(sel_frame, text=label).grid(row=i, column=0, sticky="w")
            e = tk.Entry(sel_frame, textvariable=var, width=10)
            e.grid(row=i, column=1, sticky="ew")
            e.bind("<Return>", lambda ev: self._apply_selection_props())
            e.bind("<FocusOut>", lambda ev: self._apply_selection_props())

        sel_frame.columnconfigure(1, weight=1)

        tk.Button(sel_frame, text="Apply", command=self._apply_selection_props).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        tk.Button(sel_frame, text="Delete", command=self._delete_selected).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=(2, 0))

        # Stairway properties (shown when stairway selected)
        stair_frame = tk.LabelFrame(left, text="Stairway Properties", padx=4, pady=4)
        stair_frame.pack(fill=tk.X, padx=4, pady=4)
        self.stair_frame = stair_frame

        tk.Label(stair_frame, text="From Layer:").grid(row=0, column=0, sticky="w")
        self.stair_from_var = tk.IntVar()
        tk.Entry(stair_frame, textvariable=self.stair_from_var, width=6).grid(row=0, column=1, sticky="ew")

        tk.Label(stair_frame, text="To Layer:").grid(row=1, column=0, sticky="w")
        self.stair_to_var = tk.IntVar()
        tk.Entry(stair_frame, textvariable=self.stair_to_var, width=6).grid(row=1, column=1, sticky="ew")

        tk.Label(stair_frame, text="Direction:").grid(row=2, column=0, sticky="w")
        self.stair_dir_var = tk.StringVar(value="left")
        ttk.Combobox(stair_frame, textvariable=self.stair_dir_var,
                     values=["left", "right", "up", "down"], state="readonly",
                     width=8).grid(row=2, column=1, sticky="ew")

        tk.Button(stair_frame, text="Apply", command=self._apply_stairway_props).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        stair_frame.columnconfigure(1, weight=1)

        # Test button
        tk.Button(left, text="Test Map", command=self._test_map,
                  bg="#4a7a4a", fg="white", font=("sans-serif", 11, "bold")).pack(
            fill=tk.X, padx=4, pady=8)

        # --- Canvas ---
        canvas_frame = tk.Frame(paned)
        paned.add(canvas_frame, minsize=400)

        self.canvas = tk.Canvas(canvas_frame, bg="#222222", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<ButtonPress-2>", self._on_pan_press)
        self.canvas.bind("<B2-Motion>", self._on_pan_drag)
        self.canvas.bind("<ButtonRelease-2>", self._on_pan_release)
        # Right-click always acts as select
        self.canvas.bind("<ButtonPress-3>", lambda e: self._on_canvas_press(e, override_tool="select"))
        self.canvas.bind("<B3-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-3>", self._on_canvas_release)
        self.canvas.bind("<MouseWheel>", self._on_scroll)
        # Linux scroll events
        self.canvas.bind("<Button-4>", self._on_scroll_linux)
        self.canvas.bind("<Button-5>", self._on_scroll_linux)
        self.canvas.bind("<Configure>", lambda e: self._redraw_canvas())

        # Keyboard shortcuts for tools
        self.root.bind("s", lambda e: self._set_tool("select"))
        self.root.bind("w", lambda e: self._set_tool("wall"))
        self.root.bind("f", lambda e: self._set_tool("floor"))
        self.root.bind("t", lambda e: self._set_tool("stairway"))
        self.root.bind("<Delete>", lambda e: self._delete_selected())
        self.root.bind("<Control-c>", lambda e: self._copy_selected())
        self.root.bind("<Control-x>", lambda e: self._cut_selected())
        self.root.bind("<Control-v>", lambda e: self._paste_clipboard())

    # -----------------------------------------------------------------
    # Coordinate transforms
    # -----------------------------------------------------------------
    def _map_to_screen(self, mx, my):
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        sx = mx * self.zoom + self.pan_x + cw / 2
        sy = my * self.zoom + self.pan_y + ch / 2
        return sx, sy

    def _screen_to_map(self, sx, sy):
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        mx = (sx - self.pan_x - cw / 2) / self.zoom
        my = (sy - self.pan_y - ch / 2) / self.zoom
        return mx, my

    def _snap(self, value, step=32):
        """Round value to nearest grid multiple."""
        return round(value / step) * step

    def _tint_for_layer(self, rgb, layer_idx):
        """Tint a color for an inactive layer below. 80% blend toward dark red."""
        r, g, b = rgb
        blend = 0.8
        # Layers below active layer — tint toward dark red
        tr, tg, tb = 140, 40, 40
        nr = int(r * (1 - blend) + tr * blend)
        ng = int(g * (1 - blend) + tg * blend)
        nb = int(b * (1 - blend) + tb * blend)
        return rgb_to_hex(min(255, nr), min(255, ng), min(255, nb))

    # -----------------------------------------------------------------
    # Canvas rendering
    # -----------------------------------------------------------------
    def _redraw_canvas(self):
        c = self.canvas
        c.delete("all")

        data = self.data
        mw, mh = data["width"], data["height"]

        # Draw map background
        x0, y0 = self._map_to_screen(0, 0)
        x1, y1 = self._map_to_screen(mw, mh)

        # Draw layers (only layers below active shown, tinted dark red)
        for li, layer in enumerate(data["layers"]):
            is_active = (li == self.active_layer_idx)

            # Skip layers above the active layer
            if li > self.active_layer_idx:
                continue

            if is_active:
                bg = rgb_to_hex(*layer["bg_color"])
                c.create_rectangle(x0, y0, x1, y1, fill=bg, outline="")

            stipple = "" if is_active else "gray25"
            outline_color = "#ffffff" if is_active else "#666666"

            # Floor regions
            for fi, fr in enumerate(layer["floor_regions"]):
                rx0, ry0 = self._map_to_screen(fr["x"], fr["y"])
                rx1, ry1 = self._map_to_screen(fr["x"] + fr["w"], fr["y"] + fr["h"])
                if is_active:
                    color = rgb_to_hex(*REGION_COLORS.get(fr["type"], (100, 100, 100)))
                else:
                    color = self._tint_for_layer(REGION_COLORS.get(fr["type"], (100, 100, 100)), li)
                c.create_rectangle(rx0, ry0, rx1, ry1, fill=color, outline=outline_color,
                                   width=1, stipple=stipple)
                if is_active:
                    # Label
                    cx, cy = (rx0 + rx1) / 2, (ry0 + ry1) / 2
                    c.create_text(cx, cy, text=fr["type"], fill="white",
                                  font=("sans-serif", 8))

            # Wall regions
            for wi, wr in enumerate(layer["wall_regions"]):
                rx0, ry0 = self._map_to_screen(wr["x"], wr["y"])
                rx1, ry1 = self._map_to_screen(wr["x"] + wr["w"], wr["y"] + wr["h"])
                if is_active:
                    color = rgb_to_hex(*REGION_COLORS["wall"])
                else:
                    color = self._tint_for_layer(REGION_COLORS["wall"], li)
                c.create_rectangle(rx0, ry0, rx1, ry1, fill=color, outline=outline_color,
                                   width=1, stipple=stipple)

            # Stairways (only on active layer)
            if is_active:
                for si, sw in enumerate(layer.get("stairways", [])):
                    rx0, ry0 = self._map_to_screen(sw["x"], sw["y"])
                    rx1, ry1 = self._map_to_screen(sw["x"] + sw["w"], sw["y"] + sw["h"])
                    color = rgb_to_hex(*STAIRWAY_COLOR)
                    c.create_rectangle(rx0, ry0, rx1, ry1, fill=color, outline="#ffffff", width=1)
                    cx, cy = (rx0 + rx1) / 2, (ry0 + ry1) / 2
                    label = f"S {sw['from_layer']}->{sw['to_layer']}"
                    c.create_text(cx, cy, text=label, fill="#333333", font=("sans-serif", 7))

        # Map border
        c.create_rectangle(x0, y0, x1, y1, outline="#aaaaaa", width=2)

        # Grid overlay
        grid_step = 32
        if self.zoom * grid_step >= 8:  # only draw grid when zoomed in enough
            for gx in range(0, mw + 1, grid_step):
                sx0, sy0 = self._map_to_screen(gx, 0)
                sx1, sy1 = self._map_to_screen(gx, mh)
                c.create_line(sx0, sy0, sx1, sy1, fill="#444444", width=1)
            for gy in range(0, mh + 1, grid_step):
                sx0, sy0 = self._map_to_screen(0, gy)
                sx1, sy1 = self._map_to_screen(mw, gy)
                c.create_line(sx0, sy0, sx1, sy1, fill="#444444", width=1)

        # Draw selection highlight for all selected items
        for si, (s_kind, s_idx, s_layer_idx) in enumerate(self.selected_items):
            s_rect = self._get_rect_for_item(s_kind, s_idx, s_layer_idx)
            if not s_rect:
                continue
            rx0, ry0 = self._map_to_screen(s_rect["x"], s_rect["y"])
            rx1, ry1 = self._map_to_screen(s_rect["x"] + s_rect["w"],
                                            s_rect["y"] + s_rect["h"])
            c.create_rectangle(rx0, ry0, rx1, ry1, outline="#ffff00", width=2, dash=(4, 4))
            # Resize handles only on first selected item
            if si == 0:
                hs = self.HANDLE_SIZE
                handles = self._get_handle_positions(s_rect)
                for hx, hy in handles.values():
                    c.create_rectangle(hx - hs, hy - hs, hx + hs, hy + hs,
                                       fill="#ffff00", outline="#000000")

        # Draw box-select rubber band
        if self.box_select_rect:
            br = self.box_select_rect
            bx0, by0 = self._map_to_screen(br[0], br[1])
            bx1, by1 = self._map_to_screen(br[0] + br[2], br[1] + br[3])
            c.create_rectangle(bx0, by0, bx1, by1, outline="#00ccff", width=1, dash=(3, 3))

        # Draw in-progress rectangle
        if self.draw_rect:
            dr = self.draw_rect
            rx0, ry0 = self._map_to_screen(dr[0], dr[1])
            rx1, ry1 = self._map_to_screen(dr[0] + dr[2], dr[1] + dr[3])
            if self.tool == "wall":
                color = rgb_to_hex(*REGION_COLORS["wall"])
            elif self.tool == "floor":
                color = rgb_to_hex(*REGION_COLORS.get(self.floor_type, (100, 100, 100)))
            else:
                color = rgb_to_hex(*STAIRWAY_COLOR)
            c.create_rectangle(rx0, ry0, rx1, ry1, fill=color, outline="#ffffff",
                               width=2, dash=(3, 3))

    def _get_handle_positions(self, rect):
        """Return screen-space handle positions for a map-coord rect dict."""
        x, y, w, h = rect["x"], rect["y"], rect["w"], rect["h"]
        positions = {}
        for name, (mx, my) in [("nw", (x, y)), ("ne", (x+w, y)),
                                 ("sw", (x, y+h)), ("se", (x+w, y+h)),
                                 ("n", (x+w/2, y)), ("s", (x+w/2, y+h)),
                                 ("w", (x, y+h/2)), ("e", (x+w, y+h/2))]:
            sx, sy = self._map_to_screen(mx, my)
            positions[name] = (sx, sy)
        return positions

    def _hit_test_handles(self, sx, sy, rect):
        """Test if screen point hits a resize handle. Returns handle name or None."""
        hs = self.HANDLE_SIZE + 2
        handles = self._get_handle_positions(rect)
        for name, (hx, hy) in handles.items():
            if abs(sx - hx) <= hs and abs(sy - hy) <= hs:
                return name
        return None

    def _get_rect_for_item(self, kind, index, layer_idx):
        """Return the region/stairway dict for a given selection tuple, or None."""
        if layer_idx is None or layer_idx >= len(self.data["layers"]):
            return None
        layer = self.data["layers"][layer_idx]
        if kind == "stairway":
            lst = layer.get("stairways", [])
        elif kind == "wall":
            lst = layer["wall_regions"]
        else:
            lst = layer["floor_regions"]
        if index < len(lst):
            return lst[index]
        return None

    def _get_selected_rect(self):
        """Return the first selected region/stairway dict or None."""
        if not self.selected_items:
            return None
        kind, index, layer_idx = self.selected_items[0]
        return self._get_rect_for_item(kind, index, layer_idx)

    # -----------------------------------------------------------------
    # Canvas interaction
    # -----------------------------------------------------------------
    def _on_canvas_press(self, event, override_tool=None):
        mx, my = self._screen_to_map(event.x, event.y)
        self.tool = override_tool or self.tool_var.get()
        self.floor_type = self.ftype_var.get()
        shift_held = event.state & 0x1

        if self.tool == "select":
            # Check if clicking a resize handle on current selection
            sel_rect = self._get_selected_rect()
            if sel_rect:
                handle = self._hit_test_handles(event.x, event.y, sel_rect)
                if handle:
                    self.action = "resize"
                    self.resize_handle = handle
                    return

            # Try to select a region at click point
            found = self._hit_test_region(mx, my)
            if found:
                kind, idx, layer_idx = found
                item = (kind, idx, layer_idx)

                if shift_held:
                    # Shift+click: toggle item in/out of selection
                    if item in self.selected_items:
                        self.selected_items.remove(item)
                    else:
                        self.selected_items.append(item)
                    self._update_selection_panel()
                    self._redraw_canvas()
                    return

                # If clicking an already-selected item, keep whole selection
                if item not in self.selected_items:
                    self.selected_items = [item]

                self._update_selection_panel()
                self._redraw_canvas()

                # Start move for all selected items
                if self.selected_items:
                    self.action = "move"
                    self.move_start_mouse = (mx, my)
                    self.move_start_positions = []
                    for s_kind, s_idx, s_layer_idx in self.selected_items:
                        r = self._get_rect_for_item(s_kind, s_idx, s_layer_idx)
                        if r:
                            self.move_start_positions.append((r["x"], r["y"]))
                        else:
                            self.move_start_positions.append((0, 0))
                return
            else:
                if not shift_held:
                    self._clear_selection()
                # Start box select
                self.action = "box_select"
                self.drag_start = (mx, my)
                self.box_select_rect = None
                self._redraw_canvas()
        else:
            # Drawing tool
            self.action = "draw"
            self.drag_start = (mx, my)
            self.draw_rect = None

    def _on_canvas_drag(self, event):
        mx, my = self._screen_to_map(event.x, event.y)
        snap = not (event.state & 0x1)  # snap on by default, Shift disables

        if self.action == "draw" and self.drag_start:
            x0, y0 = self.drag_start
            x = min(x0, mx)
            y = min(y0, my)
            w = abs(mx - x0)
            h = abs(my - y0)
            if snap:
                x, y = self._snap(x), self._snap(y)
                w, h = self._snap(w), self._snap(h)
            self.draw_rect = (int(x), int(y), max(1, int(w)), max(1, int(h)))
            self._redraw_canvas()

        elif self.action == "move" and self.move_start_mouse and self.move_start_positions:
            dx = mx - self.move_start_mouse[0]
            dy = my - self.move_start_mouse[1]
            for i, (s_kind, s_idx, s_layer_idx) in enumerate(self.selected_items):
                r = self._get_rect_for_item(s_kind, s_idx, s_layer_idx)
                if r and i < len(self.move_start_positions):
                    orig_x, orig_y = self.move_start_positions[i]
                    new_x = int(orig_x + dx)
                    new_y = int(orig_y + dy)
                    if snap:
                        new_x = self._snap(new_x)
                        new_y = self._snap(new_y)
                    r["x"] = new_x
                    r["y"] = new_y
            self._update_selection_panel()
            self._redraw_canvas()

        elif self.action == "resize":
            rect = self._get_selected_rect()
            if rect and self.resize_handle:
                rmx, rmy = mx, my
                if snap:
                    rmx = self._snap(rmx)
                    rmy = self._snap(rmy)
                self._apply_resize(rect, rmx, rmy)
                self._update_selection_panel()
                self._redraw_canvas()

        elif self.action == "box_select" and self.drag_start:
            x0, y0 = self.drag_start
            x = min(x0, mx)
            y = min(y0, my)
            w = abs(mx - x0)
            h = abs(my - y0)
            self.box_select_rect = (x, y, w, h)
            self._redraw_canvas()

    def _on_canvas_release(self, event):
        shift_held = event.state & 0x1

        if self.action == "draw" and self.draw_rect:
            x, y, w, h = self.draw_rect
            if w >= 2 and h >= 2:
                if self.tool == "wall":
                    self._add_wall_region(x, y, w, h)
                elif self.tool == "floor":
                    self._add_floor_region(x, y, w, h, self.floor_type)
                elif self.tool == "stairway":
                    self._add_stairway(x, y, w, h)
            self.draw_rect = None
            self._redraw_canvas()

        elif self.action == "box_select" and self.box_select_rect:
            bx, by, bw, bh = self.box_select_rect
            if bw > 2 or bh > 2:
                found = self._find_regions_in_box(bx, by, bw, bh)
                if shift_held:
                    for item in found:
                        if item in self.selected_items:
                            self.selected_items.remove(item)
                        else:
                            self.selected_items.append(item)
                else:
                    self.selected_items = found
                self._update_selection_panel()
            self.box_select_rect = None
            self._redraw_canvas()

        self.action = None
        self.drag_start = None
        self.move_start_mouse = None
        self.move_start_positions = None
        self.resize_handle = None

    def _apply_resize(self, rect, mx, my):
        """Resize a rect based on which handle is being dragged."""
        handle = self.resize_handle
        x, y, w, h = rect["x"], rect["y"], rect["w"], rect["h"]
        right = x + w
        bottom = y + h
        mx, my = int(mx), int(my)

        # East edge
        if handle in ("e", "ne", "se"):
            rect["w"] = max(4, mx - x)
        # West edge
        if handle in ("w", "nw", "sw"):
            new_x = min(mx, right - 4)
            rect["x"] = new_x
            rect["w"] = right - new_x
        # South edge
        if handle in ("s", "se", "sw"):
            rect["h"] = max(4, my - y)
        # North edge
        if handle in ("n", "ne", "nw"):
            new_y = min(my, bottom - 4)
            rect["y"] = new_y
            rect["h"] = bottom - new_y

    def _hit_test_region(self, mx, my):
        """Find region at map coords. Returns (kind, index, layer_idx) or None.
        Only checks the active layer."""
        al = self.active_layer_idx
        if al < len(self.data["layers"]):
            layer = self.data["layers"][al]
            # Check walls (reverse order so topmost drawn gets priority)
            for i in range(len(layer["wall_regions"]) - 1, -1, -1):
                wr = layer["wall_regions"][i]
                if wr["x"] <= mx <= wr["x"] + wr["w"] and wr["y"] <= my <= wr["y"] + wr["h"]:
                    return ("wall", i, al)
            for i in range(len(layer["floor_regions"]) - 1, -1, -1):
                fr = layer["floor_regions"][i]
                if fr["x"] <= mx <= fr["x"] + fr["w"] and fr["y"] <= my <= fr["y"] + fr["h"]:
                    return ("floor", i, al)
            # Check stairways on active layer
            stairways = layer.get("stairways", [])
            for i in range(len(stairways) - 1, -1, -1):
                sw = stairways[i]
                if sw["x"] <= mx <= sw["x"] + sw["w"] and sw["y"] <= my <= sw["y"] + sw["h"]:
                    return ("stairway", i, al)

        return None

    def _find_regions_in_box(self, bx, by, bw, bh):
        """Find all regions on active layer that intersect the box."""
        found = []
        al = self.active_layer_idx
        if al < len(self.data["layers"]):
            layer = self.data["layers"][al]
            for i, wr in enumerate(layer["wall_regions"]):
                if self._rects_overlap(bx, by, bw, bh, wr["x"], wr["y"], wr["w"], wr["h"]):
                    found.append(("wall", i, al))
            for i, fr in enumerate(layer["floor_regions"]):
                if self._rects_overlap(bx, by, bw, bh, fr["x"], fr["y"], fr["w"], fr["h"]):
                    found.append(("floor", i, al))
            for i, sw in enumerate(layer.get("stairways", [])):
                if self._rects_overlap(bx, by, bw, bh, sw["x"], sw["y"], sw["w"], sw["h"]):
                    found.append(("stairway", i, al))
        return found

    def _rects_overlap(self, x1, y1, w1, h1, x2, y2, w2, h2):
        """Test if two rectangles overlap."""
        return not (x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1)

    # Pan
    def _on_pan_press(self, event):
        self.pan_start = (event.x, event.y, self.pan_x, self.pan_y)
        self.canvas.config(cursor="fleur")

    def _on_pan_drag(self, event):
        if self.pan_start:
            sx0, sy0, px0, py0 = self.pan_start
            self.pan_x = px0 + (event.x - sx0)
            self.pan_y = py0 + (event.y - sy0)
            self._redraw_canvas()

    def _on_pan_release(self, event):
        self.pan_start = None
        self.canvas.config(cursor="")

    # Zoom
    def _on_scroll(self, event):
        factor = 1.1 if event.delta > 0 else 1 / 1.1
        self._apply_zoom(factor, event.x, event.y)

    def _on_scroll_linux(self, event):
        factor = 1.1 if event.num == 4 else 1 / 1.1
        self._apply_zoom(factor, event.x, event.y)

    def _apply_zoom(self, factor, sx, sy):
        old_zoom = self.zoom
        self.zoom = max(0.05, min(10.0, self.zoom * factor))
        # Adjust pan so that map point under cursor stays in place
        ratio = self.zoom / old_zoom
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        self.pan_x = sx - cw / 2 - ratio * (sx - cw / 2 - self.pan_x)
        self.pan_y = sy - ch / 2 - ratio * (sy - ch / 2 - self.pan_y)
        self._redraw_canvas()

    # -----------------------------------------------------------------
    # Region / stairway creation
    # -----------------------------------------------------------------
    def _add_wall_region(self, x, y, w, h):
        if self.active_layer_idx >= len(self.data["layers"]):
            return
        layer = self.data["layers"][self.active_layer_idx]
        layer["wall_regions"].append({"x": x, "y": y, "w": w, "h": h})

    def _add_floor_region(self, x, y, w, h, rtype):
        if self.active_layer_idx >= len(self.data["layers"]):
            return
        layer = self.data["layers"][self.active_layer_idx]
        layer["floor_regions"].append({"type": rtype, "x": x, "y": y, "w": w, "h": h})

    def _add_stairway(self, x, y, w, h):
        if self.active_layer_idx >= len(self.data["layers"]):
            return
        # Ask for stairway properties
        dlg = StairwayDialog(self.root, len(self.data["layers"]))
        if dlg.result:
            from_l, to_l, direction = dlg.result
            layer = self.data["layers"][self.active_layer_idx]
            layer.setdefault("stairways", []).append({
                "x": x, "y": y, "w": w, "h": h,
                "from_layer": from_l, "to_layer": to_l,
                "direction": direction,
            })

    # -----------------------------------------------------------------
    # Selection management
    # -----------------------------------------------------------------
    def _clear_selection(self):
        self.selected_items = []
        self._update_selection_panel()

    def _update_selection_panel(self):
        rect = self._get_selected_rect()
        if rect:
            self.sel_x_var.set(rect["x"])
            self.sel_y_var.set(rect["y"])
            self.sel_w_var.set(rect["w"])
            self.sel_h_var.set(rect["h"])
            if self.selected_items and self.selected_items[0][0] == "stairway":
                self.stair_from_var.set(rect.get("from_layer", 0))
                self.stair_to_var.set(rect.get("to_layer", 1))
                self.stair_dir_var.set(rect.get("direction", "left"))
        else:
            self.sel_x_var.set(0)
            self.sel_y_var.set(0)
            self.sel_w_var.set(0)
            self.sel_h_var.set(0)

    def _apply_selection_props(self):
        rect = self._get_selected_rect()
        if not rect:
            return
        try:
            rect["x"] = self.sel_x_var.get()
            rect["y"] = self.sel_y_var.get()
            rect["w"] = self.sel_w_var.get()
            rect["h"] = self.sel_h_var.get()
        except tk.TclError:
            pass
        self._redraw_canvas()

    def _apply_stairway_props(self):
        rect = self._get_selected_rect()
        if not rect or not self.selected_items or self.selected_items[0][0] != "stairway":
            return
        try:
            rect["from_layer"] = self.stair_from_var.get()
            rect["to_layer"] = self.stair_to_var.get()
            rect["direction"] = self.stair_dir_var.get()
        except tk.TclError:
            pass
        self._redraw_canvas()

    def _delete_selected(self):
        if not self.selected_items:
            return
        # Delete in reverse index order to avoid index shifting issues
        for kind, idx, layer_idx in sorted(self.selected_items, key=lambda t: t[1], reverse=True):
            if layer_idx is None or layer_idx >= len(self.data["layers"]):
                continue
            layer = self.data["layers"][layer_idx]
            if kind == "stairway":
                lst = layer.get("stairways", [])
            elif kind == "wall":
                lst = layer["wall_regions"]
            else:
                lst = layer["floor_regions"]
            if idx < len(lst):
                lst.pop(idx)
        self._clear_selection()
        self._redraw_canvas()

    def _copy_selected(self):
        """Copy selected regions to clipboard."""
        if not self.selected_items:
            return
        self.clipboard = []
        for kind, idx, layer_idx in self.selected_items:
            rect = self._get_rect_for_item(kind, idx, layer_idx)
            if rect:
                self.clipboard.append({
                    "kind": kind,
                    "layer_idx": layer_idx,
                    "data": copy.deepcopy(rect),
                })

    def _cut_selected(self):
        """Copy selected regions to clipboard, then delete them."""
        self._copy_selected()
        self._delete_selected()

    def _paste_clipboard(self):
        """Paste clipboard items into active layer, offset by 16px, then select them."""
        if not self.clipboard:
            return
        al = self.active_layer_idx
        if al >= len(self.data["layers"]):
            return
        layer = self.data["layers"][al]
        new_selection = []
        for entry in self.clipboard:
            kind = entry["kind"]
            rd = copy.deepcopy(entry["data"])
            rd["x"] += 16
            rd["y"] += 16
            if kind == "stairway":
                layer.setdefault("stairways", []).append(rd)
                new_idx = len(layer["stairways"]) - 1
            elif kind == "wall":
                layer["wall_regions"].append(rd)
                new_idx = len(layer["wall_regions"]) - 1
            else:
                layer["floor_regions"].append(rd)
                new_idx = len(layer["floor_regions"]) - 1
            new_selection.append((kind, new_idx, al))
        self.selected_items = new_selection
        self._update_selection_panel()
        self._redraw_canvas()

    # -----------------------------------------------------------------
    # Layer management
    # -----------------------------------------------------------------
    def _refresh_layer_list(self):
        self.layer_listbox.delete(0, tk.END)
        for i, layer in enumerate(self.data["layers"]):
            elev = layer["elevation"]
            n_floor = len(layer["floor_regions"])
            n_wall = len(layer["wall_regions"])
            n_stair = len(layer.get("stairways", []))
            self.layer_listbox.insert(tk.END, f"Layer {elev}  (F:{n_floor} W:{n_wall} S:{n_stair})")
        if self.active_layer_idx < self.layer_listbox.size():
            self.layer_listbox.selection_set(self.active_layer_idx)

    def _on_layer_select(self, event):
        sel = self.layer_listbox.curselection()
        if sel:
            self.active_layer_idx = sel[0]
            self._clear_selection()
            self._redraw_canvas()

    def _add_layer(self):
        elevations = [l["elevation"] for l in self.data["layers"]]
        new_elev = max(elevations) + 1 if elevations else 0
        self.data["layers"].append({
            "elevation": new_elev,
            "bg_color": [90, 85, 78],
            "floor_regions": [],
            "wall_regions": [],
            "stairways": [],
        })
        self._refresh_layer_list()
        self._redraw_canvas()

    def _remove_layer(self):
        if len(self.data["layers"]) <= 1:
            messagebox.showwarning("Cannot Remove", "Must have at least one layer.")
            return
        if self.active_layer_idx < len(self.data["layers"]):
            self.data["layers"].pop(self.active_layer_idx)
            self.active_layer_idx = max(0, self.active_layer_idx - 1)
            self._clear_selection()
            self._refresh_layer_list()
            self._redraw_canvas()

    def _pick_layer_bg(self):
        if self.active_layer_idx >= len(self.data["layers"]):
            return
        layer = self.data["layers"][self.active_layer_idx]
        initial = rgb_to_hex(*layer["bg_color"])
        result = colorchooser.askcolor(color=initial, title="Layer Background Color")
        if result and result[1]:
            layer["bg_color"] = list(hex_to_rgb(result[1]))
            self._redraw_canvas()

    # -----------------------------------------------------------------
    # Tool / property callbacks
    # -----------------------------------------------------------------
    def _on_tool_change(self):
        self.tool = self.tool_var.get()
        self._update_floor_type_visibility()

    def _set_tool(self, tool):
        self.tool_var.set(tool)
        self.tool = tool
        self._update_floor_type_visibility()

    def _update_floor_type_visibility(self):
        if self.tool_var.get() == "floor":
            self.ftype_frame.pack(fill=tk.X, padx=4, pady=4,
                                  after=self.tool_frame)
        else:
            self.ftype_frame.pack_forget()

    def _on_floor_type_change(self):
        self.floor_type = self.ftype_var.get()

    def _on_name_change(self):
        self.data["name"] = self.name_var.get()

    def _on_map_size_change(self):
        try:
            self.data["width"] = self.width_var.get()
            self.data["height"] = self.height_var.get()
            self._redraw_canvas()
        except tk.TclError:
            pass

    # -----------------------------------------------------------------
    # File operations
    # -----------------------------------------------------------------
    def _file_new(self):
        if not messagebox.askokcancel("New Map", "Discard current map?"):
            return
        self.data = new_map_data()
        self.filepath = None
        self.active_layer_idx = 0
        self._clear_selection()
        self.name_var.set(self.data["name"])
        self.width_var.set(self.data["width"])
        self.height_var.set(self.data["height"])
        self._refresh_layer_list()
        self._redraw_canvas()

    def _file_open(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON Map Files", "*.json"), ("All Files", "*.*")],
            initialdir=os.path.join(os.path.dirname(__file__), "maps"),
        )
        if not path:
            return
        with open(path, "r") as f:
            self.data = json.load(f)
        # Migrate old format: move top-level stairways into layers
        if "stairways" in self.data:
            for layer in self.data["layers"]:
                layer.setdefault("stairways", [])
            for sw in self.data.pop("stairways"):
                # Place stairway in its from_layer, or layer 0 as fallback
                target = sw.get("from_layer", 0)
                if target < len(self.data["layers"]):
                    self.data["layers"][target]["stairways"].append(sw)
                elif self.data["layers"]:
                    self.data["layers"][0]["stairways"].append(sw)
        else:
            for layer in self.data["layers"]:
                layer.setdefault("stairways", [])
        self.filepath = path
        self.active_layer_idx = 0
        self._clear_selection()
        self.name_var.set(self.data.get("name", "Unnamed"))
        self.width_var.set(self.data.get("width", 1024))
        self.height_var.set(self.data.get("height", 1024))
        self._refresh_layer_list()
        self._redraw_canvas()
        self.root.title(f"Map Editor — {os.path.basename(path)}")

    def _file_save(self):
        if self.filepath:
            self._save_to(self.filepath)
        else:
            self._file_save_as()

    def _file_save_as(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Map Files", "*.json"), ("All Files", "*.*")],
            initialdir=os.path.join(os.path.dirname(__file__), "maps"),
            initialfile=f"{self.data['name'].lower()}.json",
        )
        if not path:
            return
        self.filepath = path
        self._save_to(path)
        self.root.title(f"Map Editor — {os.path.basename(path)}")

    def _save_to(self, path):
        with open(path, "w") as f:
            json.dump(self.data, f, indent=2)

    def _export_python(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[("Python Files", "*.py"), ("All Files", "*.*")],
            initialdir=os.path.join(os.path.dirname(__file__), "maps"),
            initialfile=f"{self.data['name'].lower()}_map.py",
        )
        if not path:
            return
        code = generate_map_code(self.data)
        with open(path, "w") as f:
            f.write(code)
        messagebox.showinfo("Exported", f"Python map file written to:\n{path}")

    # -----------------------------------------------------------------
    # Test button
    # -----------------------------------------------------------------
    def _test_map(self):
        # Auto-save JSON
        if not self.filepath:
            maps_dir = os.path.join(os.path.dirname(__file__), "maps")
            self.filepath = os.path.join(maps_dir, f"{self.data['name'].lower()}.json")
        self._save_to(self.filepath)

        # Launch game with JSON path directly
        main_py = os.path.join(os.path.dirname(__file__), "main.py")
        subprocess.Popen([sys.executable, main_py, "--map", self.filepath])


# ---------------------------------------------------------------------------
# Stairway dialog
# ---------------------------------------------------------------------------

class StairwayDialog:
    def __init__(self, parent, num_layers):
        self.result = None
        dlg = tk.Toplevel(parent)
        dlg.title("Stairway Properties")
        dlg.transient(parent)
        dlg.grab_set()
        dlg.resizable(False, False)

        tk.Label(dlg, text="From Layer:").grid(row=0, column=0, padx=4, pady=4, sticky="w")
        from_var = tk.IntVar(value=0)
        tk.Spinbox(dlg, from_=0, to=max(0, num_layers - 1), textvariable=from_var,
                   width=6).grid(row=0, column=1, padx=4, pady=4)

        tk.Label(dlg, text="To Layer:").grid(row=1, column=0, padx=4, pady=4, sticky="w")
        to_var = tk.IntVar(value=min(1, num_layers - 1))
        tk.Spinbox(dlg, from_=0, to=max(0, num_layers - 1), textvariable=to_var,
                   width=6).grid(row=1, column=1, padx=4, pady=4)

        tk.Label(dlg, text="Direction:").grid(row=2, column=0, padx=4, pady=4, sticky="w")
        dir_var = tk.StringVar(value="left")
        ttk.Combobox(dlg, textvariable=dir_var, values=["left", "right", "up", "down"],
                     state="readonly", width=8).grid(row=2, column=1, padx=4, pady=4)

        def on_ok():
            self.result = (from_var.get(), to_var.get(), dir_var.get())
            dlg.destroy()

        def on_cancel():
            dlg.destroy()

        btn_row = tk.Frame(dlg)
        btn_row.grid(row=3, column=0, columnspan=2, pady=8)
        tk.Button(btn_row, text="OK", command=on_ok, width=8).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_row, text="Cancel", command=on_cancel, width=8).pack(side=tk.LEFT, padx=4)

        # Center dialog on parent
        dlg.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        dw = dlg.winfo_width()
        dh = dlg.winfo_height()
        dlg.geometry(f"+{px + (pw - dw) // 2}+{py + (ph - dh) // 2}")

        parent.wait_window(dlg)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    app = MapEditor(root)
    root.mainloop()
