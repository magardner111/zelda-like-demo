import random

import networkx as nx


class Layout:
    """Logical representation of a dungeon as a networkx graph.

    Rooms are nodes with a relative (x, y) grid position.
    Corridors are edges with an unlock_criteria placeholder for future gating
    logic (e.g. requires a key, enemy defeat, or puzzle solve).
    """

    def __init__(self):
        self._graph = nx.Graph()

    # --- mutation ---

    def add_room(self, room_id, pos):
        """Add a room node at relative grid position (x, y)."""
        self._graph.add_node(room_id, pos=pos)

    def add_corridor(self, room_a, room_b, unlock_criteria=None):
        """Connect two rooms with a corridor edge.

        unlock_criteria defaults to None (always passable).  Set it to any
        value to indicate a condition that must be met to traverse the corridor.
        """
        self._graph.add_edge(room_a, room_b, unlock_criteria=unlock_criteria)

    def set_unlock_criteria(self, room_a, room_b, criteria):
        """Assign (or update) the unlock criteria for a corridor."""
        self._graph.edges[room_a, room_b]["unlock_criteria"] = criteria

    # --- accessors ---

    def get_pos(self, room_id):
        """Return the relative grid position of a room."""
        return self._graph.nodes[room_id]["pos"]

    def get_unlock_criteria(self, room_a, room_b):
        """Return the unlock criteria for a corridor (None if open)."""
        return self._graph.edges[room_a, room_b].get("unlock_criteria")

    def rooms(self):
        """NodeView of all room IDs."""
        return self._graph.nodes

    def corridors(self):
        """EdgeView of all (room_a, room_b) corridor pairs."""
        return self._graph.edges

    def neighbors(self, room_id):
        """Return rooms directly connected to room_id by a corridor."""
        return self._graph.neighbors(room_id)

    @property
    def graph(self):
        """The underlying networkx graph."""
        return self._graph


# ============================================================
# Grid-Based Level Generator
# ============================================================
def generate_grid_level(n_nodes=15, min_chain=5):
    G = nx.Graph()
    occupied = set()

    x, y = 0, 0
    G.add_node(0, pos=(x, y))
    occupied.add((x, y))
    nodes = [0]

    directions = [(1,0), (-1,0), (0,1), (0,-1)]

    # backbone seed
    for i in range(1, min_chain):
        valid = [(x+dx,y+dy) for dx,dy in directions if (x+dx,y+dy) not in occupied]
        if not valid:
            break
        x,y = random.choice(valid)
        G.add_node(i, pos=(x,y))
        G.add_edge(i-1,i)
        nodes.append(i)
        occupied.add((x,y))

    # branches
    for i in range(min_chain, n_nodes):
        parent = random.choice(nodes)
        px,py = G.nodes[parent]["pos"]
        valid = [(px+dx,py+dy) for dx,dy in directions if (px+dx,py+dy) not in occupied]
        if not valid:
            continue
        x,y = random.choice(valid)
        G.add_node(i, pos=(x,y))
        G.add_edge(parent,i)
        nodes.append(i)
        occupied.add((x,y))

    return G


# ============================================================
# Backbone (Longest Path)
# ============================================================
def longest_path_tree(G):
    leaves = [n for n in G.nodes if G.degree(n)==1]
    max_path = []
    for a in leaves:
        for b in leaves:
            if a!=b:
                for p in nx.all_simple_paths(G,a,b):
                    if len(p)>len(max_path):
                        max_path=p
    return max_path


# ============================================================
# Geometry helpers
# ============================================================
def get_direction(p1,p2):
    x1,y1 = p1
    x2,y2 = p2
    dx = x2-x1
    dy = y2-y1
    if dx==1 and dy==0: return "east"
    if dx==-1 and dy==0: return "west"
    if dx==0 and dy==1: return "north"
    if dx==0 and dy==-1: return "south"
    return None

def opposite(d):
    return {"north":"south","south":"north","east":"west","west":"east"}[d]


# ============================================================
# Auto-connect adjacency (grid realism)
# ============================================================
def connect_adjacent_nodes(G,boss=None,treasure=None):
    pos = nx.get_node_attributes(G,"pos")
    nodes=list(G.nodes)
    blocked=set()
    if boss: blocked.add(boss)
    if treasure: blocked.add(treasure)

    for i in range(len(nodes)):
        n1=nodes[i]
        if n1 in blocked: continue
        x1,y1=pos[n1]
        for j in range(i+1,len(nodes)):
            n2=nodes[j]
            if n2 in blocked: continue
            x2,y2=pos[n2]
            if abs(x1-x2)+abs(y1-y2)==1:
                if not G.has_edge(n1,n2):
                    G.add_edge(n1,n2)


# ============================================================
# Room topology classification
# ============================================================
def classify_room(doors):
    open_doors=[d for d,v in doors.items() if v is not None]
    if len(open_doors)==1: return "dead_end"
    if len(open_doors)==2:
        if {"north","south"}<=set(open_doors) or {"east","west"}<=set(open_doors):
            return "corridor_straight"
        return "corridor_corner"
    if len(open_doors)==3: return "t_junction"
    if len(open_doors)==4: return "cross"
    return "isolated"


# ============================================================
# Rotation system
# ============================================================
rotation_map={
    0:{"north":"north","east":"east","south":"south","west":"west"},
    90:{"north":"east","east":"south","south":"west","west":"north"},
    180:{"north":"south","east":"west","south":"north","west":"east"},
    270:{"north":"west","east":"north","south":"east","west":"south"}
}


# ============================================================
# Layout generator
# ============================================================
def generate_layout(n_nodes=15, min_chain=5):
    """Generate a Layout using the grid-based algorithm.

    Builds a random spanning tree on a 2-D grid.  The longest leaf-to-leaf
    path becomes the backbone: entrance → main path → boss → treasure.
    Side branches off the backbone provide keys that lock the next corridor
    along the backbone (max 2 branches per backbone node; boss and treasure
    nodes get no branches).

    Extra node attributes set on the returned Layout's graph:
        role     – "entrance" | "treasure" | "boss" | "main_path" |
                   "pre_boss_key" | "side_loot" | "side_path" | "normal"
        topology – "dead_end" | "corridor_straight" | "corridor_corner" |
                   "t_junction" | "cross" | "isolated"

    Extra edge attributes:
        direction       – cardinal direction ("north"/"south"/"east"/"west")
                          from the lower-numbered node's perspective
        unlock_criteria – None (open) or the room_id whose key unlocks it
    """
    G = generate_grid_level(n_nodes, min_chain)

    # --- backbone ---
    backbone = longest_path_tree(G)
    backbone_set = set(backbone)

    entrance = backbone[0]
    treasure = backbone[-1]
    boss = backbone[-2] if len(backbone) >= 2 else None

    # --- branch extraction (max 2 per backbone node) ---
    branches = []
    branch_count = {n: 0 for n in backbone}

    for node in backbone:
        for nbr in list(G.neighbors(node)):
            if nbr in backbone_set:
                continue
            if node in (boss, treasure):
                G.remove_node(nbr)
                continue
            if branch_count[node] >= 2:
                G.remove_node(nbr)
                continue
            # Walk the full branch chain to its tip
            branch = [node]
            prev, curr = node, nbr
            while True:
                branch.append(curr)
                nxt = [n for n in G.neighbors(curr) if n != prev]
                if not nxt:
                    break
                prev, curr = curr, nxt[0]
            branches.append(branch)
            branch_count[node] += 1

    # --- room roles ---
    room_roles = {n: "normal" for n in G.nodes}
    room_roles[entrance] = "entrance"
    room_roles[treasure] = "treasure"
    if boss:
        room_roles[boss] = "boss"
    for n in backbone[1:-2]:
        room_roles[n] = "main_path"
    for branch in branches:
        for i, n in enumerate(branch):
            if i == 0:
                continue
            elif i == len(branch) - 1:
                room_roles[n] = "side_loot"
            else:
                room_roles[n] = "side_path"
    for n in G.nodes:
        if boss and G.has_edge(n, boss) and n != boss and n != treasure:
            room_roles[n] = "pre_boss_key"

    # --- populate Layout ---
    layout = Layout()

    for n, data in G.nodes(data=True):
        layout.add_room(n, data["pos"])
        layout.graph.nodes[n]["role"] = room_roles[n]

    # Track per-room door connections so topology can be classified
    doors = {n: {"north": None, "south": None, "east": None, "west": None}
             for n in G.nodes}

    for u, v in G.edges():
        d = get_direction(layout.get_pos(u), layout.get_pos(v))
        if not d:
            continue
        doors[u][d] = v
        doors[v][opposite(d)] = u
        layout.add_corridor(u, v)
        layout.graph.edges[u, v]["direction"] = d

    # --- topology classification ---
    for n in layout.rooms():
        layout.graph.nodes[n]["topology"] = classify_room(doors[n])

    # --- key gating: first branch room off each backbone node provides a key
    #     that locks the corridor to the next backbone room ---
    for branch in branches:
        if len(branch) < 2:
            continue
        backbone_node = branch[0]
        key_room = branch[1]
        if backbone_node not in backbone_set:
            continue
        idx = backbone.index(backbone_node)
        if idx + 1 >= len(backbone):
            continue
        gated = backbone[idx + 1]
        if layout.graph.has_edge(backbone_node, gated):
            layout.set_unlock_criteria(backbone_node, gated, key_room)

    return layout
