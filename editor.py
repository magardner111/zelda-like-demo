#!/usr/bin/env python3
"""Tkinter-based map editor for the Zelda-like demo."""

import copy
import json
import os
import subprocess
import sys
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk

from data.enemy_stats import ENEMY_STATS
from data.pattern_registry import PATTERN_REGISTRY

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
                "enemies": [],
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

# Enemy rendering
ALL_ENEMY_TYPES = sorted(ENEMY_STATS.keys())
ENEMY_DRAW_RADIUS = 12  # map-space radius for rendering/hit-testing
ALL_PATTERN_TYPES = ["none"] + sorted(PATTERN_REGISTRY.keys())
ALL_FACING_DIRECTIONS = ["down", "up", "left", "right"]
FACING_VECTORS = {
    "down": (0, 1), "up": (0, -1), "left": (-1, 0), "right": (1, 0),
}


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

    # Check if any enemies exist
    has_enemies = any(layer.get("enemies") for layer in data["layers"])

    lines = [
        "from maps.map_base import MapBase",
        "from core.floor_layer import FloorLayer",
        "from core.stairway import Stairway, StairDirection",
        "from core.region_base import WallRegion, FloorRegion, LiquidRegion, ObjectRegion",
        "from data.region_stats import REGION_STATS",
    ]
    has_facing = any(
        e.get("facing", "down") != "down"
        for layer in data["layers"]
        for e in layer.get("enemies", [])
    )
    if has_enemies:
        imports = [
            "from core.enemy_base import Enemy",
            "from data.enemy_stats import ENEMY_STATS",
            "from data.pattern_registry import get_pattern_class",
        ]
        if has_facing:
            imports.insert(0, "import pygame")
        lines += imports
    lines += [
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

    # Enemies (gathered from all layers)
    all_enemies = []
    for layer in data["layers"]:
        for e in layer.get("enemies", []):
            all_enemies.append((layer["elevation"], e))
    if all_enemies:
        lines.append("        # --- Enemies ---")
        for elev, e in all_enemies:
            etype = e["type"]
            lines.append(
                f'        _e = Enemy(({e["x"]}, {e["y"]}), ENEMY_STATS["{etype}"])'
            )
            lines.append(f"        _e.current_layer = {elev}")
            facing = e.get("facing", "down")
            if facing != "down":
                facing_map = {"up": "(0, -1)", "left": "(-1, 0)", "right": "(1, 0)"}
                lines.append(
                    f"        _e.facing = pygame.Vector2{facing_map[facing]}"
                )
            pdata = e.get("pattern")
            if pdata and pdata.get("type"):
                ptype = pdata["type"]
                params = {k: v for k, v in pdata.items() if k != "type"}
                param_str = ", ".join(f"{k}={v!r}" for k, v in params.items())
                lines.append(
                    f'        _e.pattern = get_pattern_class("{ptype}")({param_str})'
                )
            lines.append("        self.enemies.append(_e)")
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
        self.tool = "select"  # select | wall | floor | stairway | enemy
        self.floor_type = "grass"
        self.enemy_type = ALL_ENEMY_TYPES[0] if ALL_ENEMY_TYPES else "lvl1enemy"
        self.enemy_pattern = "none"
        self.enemy_pattern_params = {}  # current parameter values for placement

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

        # --- Tabbed panel: Tools & Enemies ---
        self.notebook = ttk.Notebook(left)
        self.notebook.pack(fill=tk.X, padx=4, pady=4)

        # --- Tools tab ---
        self.tools_tab = tk.Frame(self.notebook)
        self.notebook.add(self.tools_tab, text="Tools")

        self.tool_var = tk.StringVar(value="select")
        for t in ("select", "wall", "floor", "stairway", "enemy"):
            tk.Radiobutton(self.tools_tab, text=t.title(), variable=self.tool_var,
                           value=t, command=self._on_tool_change).pack(anchor="w")

        # Floor type dropdown (only visible when floor tool is active)
        self.ftype_frame = tk.LabelFrame(self.tools_tab, text="Floor Region Type", padx=4, pady=4)
        self.ftype_var = tk.StringVar(value="grass")
        self.ftype_combo = ttk.Combobox(self.ftype_frame, textvariable=self.ftype_var,
                                        values=ALL_FLOOR_TYPES, state="readonly", width=16)
        self.ftype_combo.pack(fill=tk.X)
        self.ftype_combo.bind("<<ComboboxSelected>>", lambda e: self._on_floor_type_change())

        # --- Enemies tab ---
        self.enemies_tab = tk.Frame(self.notebook)
        self.notebook.add(self.enemies_tab, text="Enemies")

        # Placement section
        self.placement_frame = tk.LabelFrame(self.enemies_tab, text="Placement", padx=4, pady=4)
        self.placement_frame.pack(fill=tk.X, padx=4, pady=4)
        placement_frame = self.placement_frame

        tk.Label(placement_frame, text="Type:").grid(row=0, column=0, sticky="w")
        self.etype_var = tk.StringVar(value=self.enemy_type)
        ttk.Combobox(placement_frame, textvariable=self.etype_var,
                     values=ALL_ENEMY_TYPES, state="readonly", width=16).grid(row=0, column=1, sticky="ew")

        tk.Label(placement_frame, text="Facing:").grid(row=1, column=0, sticky="w")
        self.efacing_var = tk.StringVar(value="down")
        ttk.Combobox(placement_frame, textvariable=self.efacing_var,
                     values=ALL_FACING_DIRECTIONS, state="readonly", width=16).grid(row=1, column=1, sticky="ew")

        tk.Label(placement_frame, text="Pattern:").grid(row=2, column=0, sticky="w")
        self.epattern_var = tk.StringVar(value="none")
        self.epattern_combo = ttk.Combobox(placement_frame, textvariable=self.epattern_var,
                                           values=ALL_PATTERN_TYPES, state="readonly", width=16)
        self.epattern_combo.grid(row=2, column=1, sticky="ew")
        self.epattern_combo.bind("<<ComboboxSelected>>", lambda e: self._rebuild_enemy_param_fields())

        # Container for dynamic pattern param fields
        self.eparam_frame = tk.Frame(placement_frame)
        self.eparam_frame.grid(row=3, column=0, columnspan=2, sticky="ew")
        self.eparam_widgets = {}  # name -> (label, entry, var)

        placement_frame.columnconfigure(1, weight=1)

        # Selected Enemy section (shown when an enemy is selected on canvas)
        self.sel_enemy_frame = tk.LabelFrame(self.enemies_tab, text="Selected Enemy", padx=4, pady=4)
        # Not packed until an enemy is selected

        # Stats display area (read-only)
        self.enemy_stats_frame = tk.Frame(self.sel_enemy_frame)
        self.enemy_stats_frame.pack(fill=tk.X)
        self.enemy_stats_labels = {}

        ttk.Separator(self.sel_enemy_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=4)

        # Editable fields
        edit_frame = tk.Frame(self.sel_enemy_frame)
        edit_frame.pack(fill=tk.X)

        tk.Label(edit_frame, text="Type:").grid(row=0, column=0, sticky="w")
        self.eprop_type_var = tk.StringVar()
        self.eprop_type_combo = ttk.Combobox(edit_frame, textvariable=self.eprop_type_var,
                     values=ALL_ENEMY_TYPES, state="readonly", width=16)
        self.eprop_type_combo.grid(row=0, column=1, sticky="ew")
        self.eprop_type_combo.bind("<<ComboboxSelected>>",
                                    lambda e: self._on_sel_enemy_type_change())

        tk.Label(edit_frame, text="Facing:").grid(row=1, column=0, sticky="w")
        self.eprop_facing_var = tk.StringVar(value="down")
        self.eprop_facing_combo = ttk.Combobox(edit_frame, textvariable=self.eprop_facing_var,
                     values=ALL_FACING_DIRECTIONS, state="readonly", width=16)
        self.eprop_facing_combo.grid(row=1, column=1, sticky="ew")
        self.eprop_facing_combo.bind("<<ComboboxSelected>>",
                                      lambda e: self._on_sel_enemy_facing_change())

        tk.Label(edit_frame, text="Pattern:").grid(row=2, column=0, sticky="w")
        self.eprop_pattern_var = tk.StringVar(value="none")
        self.eprop_pattern_combo = ttk.Combobox(edit_frame, textvariable=self.eprop_pattern_var,
                                                values=ALL_PATTERN_TYPES, state="readonly", width=16)
        self.eprop_pattern_combo.grid(row=2, column=1, sticky="ew")
        self.eprop_pattern_combo.bind("<<ComboboxSelected>>",
                                      lambda e: self._rebuild_enemy_prop_param_fields())

        # Container for dynamic pattern param fields in properties
        self.eprop_param_frame = tk.Frame(edit_frame)
        self.eprop_param_frame.grid(row=3, column=0, columnspan=2, sticky="ew")
        self.eprop_param_widgets = {}

        tk.Button(edit_frame, text="Apply", command=self._apply_enemy_props).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        edit_frame.columnconfigure(1, weight=1)

        # Stairway properties (inside tools tab, shown when stairway selected)
        self.stair_frame = tk.LabelFrame(self.tools_tab, text="Stairway Properties", padx=4, pady=4)
        # Not packed until a stairway is selected

        tk.Label(self.stair_frame, text="From Layer:").grid(row=0, column=0, sticky="w")
        self.stair_from_var = tk.IntVar()
        tk.Entry(self.stair_frame, textvariable=self.stair_from_var, width=6).grid(row=0, column=1, sticky="ew")

        tk.Label(self.stair_frame, text="To Layer:").grid(row=1, column=0, sticky="w")
        self.stair_to_var = tk.IntVar()
        tk.Entry(self.stair_frame, textvariable=self.stair_to_var, width=6).grid(row=1, column=1, sticky="ew")

        tk.Label(self.stair_frame, text="Direction:").grid(row=2, column=0, sticky="w")
        self.stair_dir_var = tk.StringVar(value="left")
        ttk.Combobox(self.stair_frame, textvariable=self.stair_dir_var,
                     values=["left", "right", "up", "down"], state="readonly",
                     width=8).grid(row=2, column=1, sticky="ew")

        tk.Button(self.stair_frame, text="Apply", command=self._apply_stairway_props).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        self.stair_frame.columnconfigure(1, weight=1)

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
        self.root.bind("e", lambda e: self._set_tool("enemy"))
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

            # Enemies (only on active layer)
            if is_active:
                for ei, en in enumerate(layer.get("enemies", [])):
                    ecx, ecy = self._map_to_screen(en["x"], en["y"])
                    r = ENEMY_DRAW_RADIUS * self.zoom
                    ecolor = ENEMY_STATS.get(en["type"], {}).get("color", (200, 40, 40))
                    c.create_oval(ecx - r, ecy - r, ecx + r, ecy + r,
                                  fill=rgb_to_hex(*ecolor), outline="#ffffff", width=1)
                    c.create_text(ecx, ecy, text=en["type"], fill="white",
                                  font=("sans-serif", 7))
                    # Facing direction indicator
                    fdx, fdy = self._get_enemy_facing(en)
                    esize = ENEMY_STATS.get(en["type"], {}).get("size", 20)
                    line_len = esize * self.zoom
                    c.create_line(ecx, ecy, ecx + fdx * line_len, ecy + fdy * line_len,
                                  fill="#ff0000", width=2)

        # Map border
        c.create_rectangle(x0, y0, x1, y1, outline="#aaaaaa", width=2)

        # Grid overlay
        grid_step = 32
        if self.zoom * grid_step >= 8:  # only draw grid when zoomed in enough
            for gx in range(0, mw + 1, grid_step):
                sx0, sy0 = self._map_to_screen(gx, 0)
                sx1, sy1 = self._map_to_screen(gx, mh)
                c.create_line(sx0, sy0, sx1, sy1, fill="#444444", width=1, stipple="gray50")
            for gy in range(0, mh + 1, grid_step):
                sx0, sy0 = self._map_to_screen(0, gy)
                sx1, sy1 = self._map_to_screen(mw, gy)
                c.create_line(sx0, sy0, sx1, sy1, fill="#444444", width=1, stipple="gray50")

        # Draw selection highlight for all selected items
        for si, (s_kind, s_idx, s_layer_idx) in enumerate(self.selected_items):
            s_item = self._get_rect_for_item(s_kind, s_idx, s_layer_idx)
            if not s_item:
                continue
            if s_kind == "enemy":
                # Circle highlight for enemies
                ecx, ecy = self._map_to_screen(s_item["x"], s_item["y"])
                r = (ENEMY_DRAW_RADIUS + 4) * self.zoom
                c.create_oval(ecx - r, ecy - r, ecx + r, ecy + r,
                              outline="#ffff00", width=2, dash=(4, 4))
            else:
                rx0, ry0 = self._map_to_screen(s_item["x"], s_item["y"])
                rx1, ry1 = self._map_to_screen(s_item["x"] + s_item["w"],
                                                s_item["y"] + s_item["h"])
                c.create_rectangle(rx0, ry0, rx1, ry1, outline="#ffff00", width=2, dash=(4, 4))
                # Resize handles only on first selected item (not for enemies)
                if si == 0:
                    hs = self.HANDLE_SIZE
                    handles = self._get_handle_positions(s_item)
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
        """Return the region/stairway/enemy dict for a given selection tuple, or None."""
        if layer_idx is None or layer_idx >= len(self.data["layers"]):
            return None
        layer = self.data["layers"][layer_idx]
        if kind == "enemy":
            lst = layer.get("enemies", [])
        elif kind == "stairway":
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

    def _is_enemies_tab_active(self):
        return self.notebook.select() == str(self.enemies_tab)

    # -----------------------------------------------------------------
    # Canvas interaction
    # -----------------------------------------------------------------
    def _on_canvas_press(self, event, override_tool=None):
        mx, my = self._screen_to_map(event.x, event.y)
        self.tool = override_tool or self.tool_var.get()
        self.floor_type = self.ftype_var.get()
        shift_held = event.state & 0x1

        # Enemies tab: click enemy to select, click empty space to place
        if self._is_enemies_tab_active() and not override_tool:
            found = self._hit_test_region(mx, my)
            if found and found[0] == "enemy":
                self.tool = "select"
            else:
                self.tool = "enemy"

        if self.tool == "enemy":
            # Single click places an enemy at grid-snapped position
            snap = not shift_held
            ex = self._snap(mx) if snap else int(mx)
            ey = self._snap(my) if snap else int(my)
            self._add_enemy(ex, ey)
            self._refresh_layer_list()
            self._redraw_canvas()
            return

        if self.tool == "select":
            # Check if clicking a resize handle on current selection
            sel_rect = self._get_selected_rect()
            if sel_rect and self.selected_items[0][0] != "enemy":
                handle = self._hit_test_handles(event.x, event.y, sel_rect)
                if handle:
                    self.action = "resize"
                    self.resize_handle = handle
                    return

            # Try to select a region at click point
            found = self._hit_test_region(mx, my)
            if found and self._is_enemies_tab_active() and found[0] != "enemy":
                found = None
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
            # Drawing tool (wall/floor/stairway)
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
                if self._is_enemies_tab_active():
                    found = [f for f in found if f[0] == "enemy"]
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
        Only checks the active layer. Enemies checked first (they are drawn on top)."""
        al = self.active_layer_idx
        if al < len(self.data["layers"]):
            layer = self.data["layers"][al]
            # Check enemies first (distance-based, drawn on top)
            enemies = layer.get("enemies", [])
            for i in range(len(enemies) - 1, -1, -1):
                en = enemies[i]
                dx = mx - en["x"]
                dy = my - en["y"]
                if dx * dx + dy * dy <= ENEMY_DRAW_RADIUS * ENEMY_DRAW_RADIUS:
                    return ("enemy", i, al)
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
            for i, en in enumerate(layer.get("enemies", [])):
                if bx <= en["x"] <= bx + bw and by <= en["y"] <= by + bh:
                    found.append(("enemy", i, al))
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

    def _add_enemy(self, x, y):
        if self.active_layer_idx >= len(self.data["layers"]):
            return
        layer = self.data["layers"][self.active_layer_idx]
        etype = self.etype_var.get()
        ptype = self.epattern_var.get()
        pattern = None
        if ptype != "none" and ptype in PATTERN_REGISTRY:
            defaults = PATTERN_REGISTRY[ptype]["params"]
            params = dict(defaults)
            for name, (_, _, var) in self.eparam_widgets.items():
                try:
                    params[name] = float(var.get())
                except (ValueError, tk.TclError):
                    pass
            pattern = {"type": ptype}
            pattern.update(params)
        facing = self.efacing_var.get()
        layer.setdefault("enemies", []).append({
            "type": etype,
            "x": x,
            "y": y,
            "facing": facing,
            "pattern": pattern,
        })
        # Auto-select the new enemy
        new_idx = len(layer["enemies"]) - 1
        self.selected_items = [("enemy", new_idx, self.active_layer_idx)]
        self._update_selection_panel()

    # -----------------------------------------------------------------
    # Selection management
    # -----------------------------------------------------------------
    def _clear_selection(self):
        self.selected_items = []
        self._update_selection_panel()

    def _update_selection_panel(self):
        item = self._get_selected_rect()
        is_enemy = self.selected_items and self.selected_items[0][0] == "enemy"
        is_stairway = self.selected_items and self.selected_items[0][0] == "stairway"

        # Enemies tab: toggle placement vs selected enemy
        if is_enemy and item:
            self.placement_frame.pack_forget()
            self.sel_enemy_frame.pack(fill=tk.X, padx=4, pady=4)
            self.notebook.select(self.enemies_tab)
            self.eprop_type_var.set(item.get("type", ""))
            self.eprop_facing_var.set(item.get("facing", "down"))
            self._refresh_enemy_stats_display(item.get("type", ""))
            pdata = item.get("pattern")
            if pdata and pdata.get("type"):
                self.eprop_pattern_var.set(pdata["type"])
            else:
                self.eprop_pattern_var.set("none")
            self._rebuild_enemy_prop_param_fields()
        else:
            self.sel_enemy_frame.pack_forget()
            self.placement_frame.pack(fill=tk.X, padx=4, pady=4)

        # Tools tab: stairway properties
        if is_stairway and item:
            self.stair_frame.pack(fill=tk.X, padx=4, pady=4)
            self.stair_from_var.set(item.get("from_layer", 0))
            self.stair_to_var.set(item.get("to_layer", 1))
            self.stair_dir_var.set(item.get("direction", "left"))
        else:
            self.stair_frame.pack_forget()

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
            if kind == "enemy":
                lst = layer.get("enemies", [])
            elif kind == "stairway":
                lst = layer.get("stairways", [])
            elif kind == "wall":
                lst = layer["wall_regions"]
            else:
                lst = layer["floor_regions"]
            if idx < len(lst):
                lst.pop(idx)
        self._clear_selection()
        self._refresh_layer_list()
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
            if kind == "enemy":
                layer.setdefault("enemies", []).append(rd)
                new_idx = len(layer["enemies"]) - 1
            elif kind == "stairway":
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
        self._refresh_layer_list()
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
            n_enemy = len(layer.get("enemies", []))
            label = f"Layer {elev}  (F:{n_floor} W:{n_wall} S:{n_stair} E:{n_enemy})"
            self.layer_listbox.insert(tk.END, label)
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
            "enemies": [],
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
        tool = self.tool_var.get()
        if tool == "floor":
            self.ftype_frame.pack(fill=tk.X, padx=4, pady=4)
        else:
            self.ftype_frame.pack_forget()
        if tool == "enemy":
            self.notebook.select(self.enemies_tab)

    def _on_floor_type_change(self):
        self.floor_type = self.ftype_var.get()

    # -----------------------------------------------------------------
    # Enemy tool helpers
    # -----------------------------------------------------------------
    def _get_enemy_facing(self, enemy_data):
        """Return (dx, dy) unit vector for the enemy's facing direction."""
        return FACING_VECTORS.get(enemy_data.get("facing", "down"), (0, 1))

    def _rebuild_enemy_param_fields(self):
        """Rebuild dynamic pattern parameter fields in the enemy options panel."""
        for widget in self.eparam_frame.winfo_children():
            widget.destroy()
        self.eparam_widgets.clear()

        ptype = self.epattern_var.get()
        if ptype == "none" or ptype not in PATTERN_REGISTRY:
            return
        defaults = PATTERN_REGISTRY[ptype]["params"]
        for i, (name, default) in enumerate(sorted(defaults.items())):
            lbl = tk.Label(self.eparam_frame, text=f"{name}:")
            lbl.grid(row=i, column=0, sticky="w")
            var = tk.StringVar(value=str(default))
            ent = tk.Entry(self.eparam_frame, textvariable=var, width=10)
            ent.grid(row=i, column=1, sticky="ew")
            self.eparam_widgets[name] = (lbl, ent, var)
        self.eparam_frame.columnconfigure(1, weight=1)

    def _rebuild_enemy_prop_param_fields(self):
        """Rebuild dynamic pattern parameter fields in the enemy properties panel."""
        for widget in self.eprop_param_frame.winfo_children():
            widget.destroy()
        self.eprop_param_widgets.clear()

        ptype = self.eprop_pattern_var.get()
        if ptype == "none" or ptype not in PATTERN_REGISTRY:
            return

        # Get current values from the selected enemy's pattern data
        enemy_data = self._get_selected_rect()
        pdata = enemy_data.get("pattern") if enemy_data else None
        defaults = PATTERN_REGISTRY[ptype]["params"]

        for i, (name, default) in enumerate(sorted(defaults.items())):
            lbl = tk.Label(self.eprop_param_frame, text=f"{name}:")
            lbl.grid(row=i, column=0, sticky="w")
            # Use existing value from enemy data if available
            val = default
            if pdata and name in pdata:
                val = pdata[name]
            var = tk.StringVar(value=str(val))
            ent = tk.Entry(self.eprop_param_frame, textvariable=var, width=10)
            ent.grid(row=i, column=1, sticky="ew")
            self.eprop_param_widgets[name] = (lbl, ent, var)
        self.eprop_param_frame.columnconfigure(1, weight=1)

    def _refresh_enemy_stats_display(self, etype):
        """Update the read-only stats labels for the selected enemy type."""
        for widget in self.enemy_stats_frame.winfo_children():
            widget.destroy()
        self.enemy_stats_labels.clear()
        stats = ENEMY_STATS.get(etype, {})
        for i, (key, val) in enumerate(sorted(stats.items())):
            tk.Label(self.enemy_stats_frame, text=f"{key}:", anchor="w").grid(
                row=i, column=0, sticky="w")
            lbl = tk.Label(self.enemy_stats_frame, text=str(val), anchor="w", fg="#666666")
            lbl.grid(row=i, column=1, sticky="w", padx=(4, 0))
            self.enemy_stats_labels[key] = lbl
        self.enemy_stats_frame.columnconfigure(1, weight=1)

    def _on_sel_enemy_type_change(self):
        """When the enemy type combo in Selected Enemy changes, update immediately."""
        enemy = self._get_selected_rect()
        if enemy:
            enemy["type"] = self.eprop_type_var.get()
        self._refresh_enemy_stats_display(self.eprop_type_var.get())
        self._redraw_canvas()

    def _on_sel_enemy_facing_change(self):
        """When the facing combo in Selected Enemy changes, update immediately."""
        enemy = self._get_selected_rect()
        if enemy:
            enemy["facing"] = self.eprop_facing_var.get()
        self._redraw_canvas()

    def _apply_enemy_props(self):
        """Apply enemy properties panel values to the selected enemy."""
        if not self.selected_items or self.selected_items[0][0] != "enemy":
            return
        enemy = self._get_selected_rect()
        if not enemy:
            return
        enemy["type"] = self.eprop_type_var.get()
        enemy["facing"] = self.eprop_facing_var.get()
        ptype = self.eprop_pattern_var.get()
        if ptype == "none" or ptype not in PATTERN_REGISTRY:
            enemy["pattern"] = None
        else:
            defaults = PATTERN_REGISTRY[ptype]["params"]
            params = {"type": ptype}
            for name, default in defaults.items():
                if name in self.eprop_param_widgets:
                    _, _, var = self.eprop_param_widgets[name]
                    try:
                        params[name] = float(var.get())
                    except (ValueError, tk.TclError):
                        params[name] = default
                else:
                    params[name] = default
            enemy["pattern"] = params
        self._redraw_canvas()

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
        # Ensure enemies list exists on all layers
        for layer in self.data["layers"]:
            layer.setdefault("enemies", [])
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
