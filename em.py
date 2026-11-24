"""EM layout over COM: AXIEM (planar) and Analyst (3D FEM) structures, stackup, shapes, ports.
The API works in metres; every tool here takes and returns millimetres.

Stackup, as found in the v17 type library and checked live:
  dielectrics  em.MaterialLayers      top to bottom, read-only here: the COM setters make the material anisotropic, so set_em_stackup rewrites the exported XML instead
  EM layer k   the interface above dielectric k (1 = the lid); a conductor on EM layer 2 sits on dielectric 1's floor
  conductors   Project.Conductors (named: Thickness, Conductivity) or the built-in 'Perfect Conductor'
  mapping      <em PD>.LayerSetup.EMLayerMappings(1).Entries(drawing layer): EMLayer + Material
  enclosure    em.Enclosure XDimension / YDimension / XDivisions / YDivisions, EnclosureTop / EnclosureBottom .Type
  Analyst boundary  a KLayoutBoundary drawing object (em.DrawingObjects.AddBoundary(points, 0, "")) on layer EMBoundary: without it
                    the structure has no simulation boundary ('No boundary shape defined') and ExportEmInputDataXML fails. Its four
                    edges each carry a material (Approx Open by default), editable only in the exported XML (<BOUNDARY><EDGE Material>)
Each EM structure owns a derived process definition '+<name>'; shapes resolve drawing layers in the default one.
"""
import re

import helpers as h
from connection import awr, find

MM = 1e-3
SIM = {"AXIEM": 0, "Analyst": 4}  # mwEmSimulator; Simulator=1/2 read back as 0, EMSight is 3 (the AWR default)
SIM_NAME = {0: "AXIEM", 1: "AXIEM", 2: "AXIEM", 3: "EMSight", 4: "Analyst"}
# IBoundaryModel.Type (mwBoundaryModelType). PML (8) and the rest are silently ignored by the setter in v17.
BOUND = {"perfect_conductor": 0, "real_conductor": 1, "approx_open": 2, "infinite_waveguide": 3}
BOUND_NAME = {v: k for k, v in BOUND.items()}
EDGE_MAT = {"perfect_conductor": "Perfect Conductor", "approx_open": "Approx Open", "infinite_waveguide": "Inf WG"}  # Analyst side materials (XML names)
EDGE_MAT_NAME = {v: k for k, v in EDGE_MAT.items()}
SHAPE_TYPE = {0: "rect", 1: "polygon", 2: "path", 3: "ellipse", 9: "pin"}
EDGE_TYPE = {2: "left", 3: "bottom", 4: "right", 5: "top"}  # mwEMPortType for edge ports
FLAGS = {"edge": None, "lumped_down": 5, "lumped_diff": 256, "wave": 64, "wave_custom": 192}  # IEMPort.Flags, decoded via InfoText
MAX_LAYERS = 3  # shortcut: MaterialLayers.Add / StackupUtil corrupt the structure (Access Violation), Remove is fake, and importing a stackup XML with more layers than AWR's 3 leaves the COM view incoherent


def _p():
    return awr().Project


def _em(name):
    return find(_p().EMStructures, name)


def _default_pd():
    return next(pd for pd in _p().ProcessDefinitions if pd.IsDefaultProcess)


def _layers(em):
    """Dielectric layers top to bottom (COM view; the solver view is _solver_stackup)."""
    ml = em.MaterialLayers
    return [ml(k) for k in range(1, ml.Count + 1)]


def _export_xml(em):
    """Parsed ExportEmInputDataXML of the structure: the solver's own input, the one view that cannot disagree with the solver."""
    import os
    import tempfile
    import xml.etree.ElementTree as ET
    path = os.path.join(tempfile.gettempdir(), f"AWRMWO_mcp_{os.getpid()}_stackup.xml")
    em.ExportEmInputDataXML(path)
    try:
        return ET.parse(path)
    finally:
        os.remove(path)


def _dval(mat, tag):
    e = mat.find(f"{tag}/Double")
    return None if e is None else float(e.text)


def _solver_stackup(em):
    """Per dielectric layer, as the solver sees it: {thickness_m, er: (x, y, z), tand: (x, y, z)}. The COM read-back can
    disagree (a removed layer stayed in the solver input; DielectricConstant makes the material anisotropic)."""
    root = _export_xml(em).getroot()
    mats = {m.get("Name"): m for m in root.iter("Material")}
    out = []
    for l in root.find(".//ELayers/Dielectrics"):
        m = mats[l.get("Material")]
        ax = lambda base, sfx: tuple(_dval(m, f"{base}_{a}") if _dval(m, f"{base}_{a}") is not None else _dval(m, base) for a in sfx)
        out.append({"thickness_m": float(l.get("Thickness")), "er": ax("Permittivity", "xyz"), "tand": ax("DielectricLossTangent", "xyz")})
    return out


def _write_stackup(em, layers):
    """Set isotropic dielectrics by export / rewrite / ImportEmInputData. IMaterialLayer.DielectricConstant and .LossTangent
    set only the z properties (the material turns anisotropic: x/y keep AWR's defaults), and the API has no isotropic
    setter. Layers k > len(layers) are dropped; materials keep AWR's names (Air, Diel_1, Diel_2)."""
    import os
    import tempfile
    import xml.etree.ElementTree as ET
    tree = _export_xml(em)
    root = tree.getroot()
    mats = {m.get("Name"): m for m in root.iter("Material")}
    diel = root.find(".//ELayers/Dielectrics")
    for l in list(diel)[len(layers):]:
        diel.remove(l)
    for l, d in zip(diel, layers):
        l.set("Thickness", f"{d['thickness_mm'] * MM:.10f}")
        m = mats[l.get("Material")]
        for c in list(m):
            if c.tag.startswith(("Permittivity", "DielectricLossTangent")):
                m.remove(c)
        for tag, v in (("Permittivity", d["er"]), ("DielectricLossTangent", d.get("tand", 0.0))):
            e = ET.SubElement(m, tag)
            ET.SubElement(e, "Double").text = f"{float(v):.10f}"
    total = f"{sum(float(l.get('Thickness')) for l in diel):.10f}"
    for l in root.find(".//ELayers/Layers"):
        if l.get("Name") == "EMBoundary":
            l.set("Thickness", total)
        elif l.get("Name") == "EMTop":
            l.set("Elevation", total)
    ET.register_namespace("mwo", "http://www.awr.com/mwo_link")
    path = os.path.join(tempfile.gettempdir(), f"AWRMWO_mcp_{os.getpid()}_stackup_in.xml")
    tree.write(path, encoding="UTF-8", xml_declaration=True)
    try:
        if not em.ImportEmInputData(path):
            raise RuntimeError("AWR refused the rewritten stackup (ImportEmInputData returned False; it also refuses once the structure has shapes or ports: set the dielectrics before drawing)")
    finally:
        os.remove(path)


def _mapping(em):
    pd = _p().ProcessDefinitions(em.ProcessDefinition)
    return pd.LayerSetup.EMLayerMappings(1).Entries


def _boundary_objs(em):
    return [o for o in em.DrawingObjects if o.InfoText.startswith("Boundary:")]


def _draw_boundary(em, x=None, y=None):
    """(Re)draw the Analyst simulation boundary as a rectangle 0..x, 0..y metres (default: the enclosure). Edge materials reset to Approx Open."""
    for o in _boundary_objs(em):  # a second boundary object makes the XML export fail
        o.Delete()
    x, y = x or em.Enclosure.XDimension, y or em.Enclosure.YDimension
    em.DrawingObjects.AddBoundary([0, 0, x, 0, x, y, 0, y], 0, "")  # extractGroup "" is accepted


def _edges(root):
    """{bbox_mm, n_edges, edges: {bottom|right|top|left: side name}} of the exported <BOUNDARY>, or None."""
    b = root.find(".//BOUNDARY")
    if b is None:
        return None
    es = [([(float(p.get("x")), float(p.get("y"))) for p in e.findall("POINT")], e) for e in b.findall("EDGE")]
    xs, ys = [p[0] for pts, _ in es for p in pts], [p[1] for pts, _ in es for p in pts]
    bb = [min(xs), min(ys), max(xs), max(ys)]
    out = {}
    for pts, e in es:
        (x1, y1), (x2, y2) = pts[0], pts[-1]
        name = ("bottom" if y1 == bb[1] else "top") if y1 == y2 else ("left" if x1 == bb[0] else "right") if x1 == x2 else None
        if name:
            out[name] = (e, EDGE_MAT_NAME.get(e.get("Material"), e.get("Material")))
    return {"bbox_mm": [v / MM for v in bb], "n_edges": len(es), "edges": out}


def _set_sides(em, want):
    """Set Analyst boundary edge materials {left|right|top|bottom: condition} by export / rewrite / ImportEmInputData."""
    for side, v in want.items():
        if v not in EDGE_MAT or side not in ("left", "right", "top", "bottom"):
            raise ValueError(f"sides: edges left/right/top/bottom with values {list(EDGE_MAT)} (real_conductor and pml are not available for Analyst side edges)")
    import os
    import tempfile
    import xml.etree.ElementTree as ET
    tree = _export_xml(em)
    info = _edges(tree.getroot())
    if info["n_edges"] != 4:
        raise ValueError("The Analyst boundary is not a 4-edge rectangle; redraw it with set_em_stackup(enclosure=...)")
    for side, v in want.items():
        info["edges"][side][0].set("Material", EDGE_MAT[v])
    ET.register_namespace("mwo", "http://www.awr.com/mwo_link")
    path = os.path.join(tempfile.gettempdir(), f"AWRMWO_mcp_{os.getpid()}_sides_in.xml")
    tree.write(path, encoding="UTF-8", xml_declaration=True)
    try:
        if not em.ImportEmInputData(path):
            raise RuntimeError("AWR refused the rewritten boundary (ImportEmInputData returned False)")
    finally:
        os.remove(path)
    got = {k: v[1] for k, v in _edges(_export_xml(em).getroot())["edges"].items()}
    if any(got.get(k) != v for k, v in want.items()):
        raise RuntimeError(f"Boundary edges read back {got}, asked for {want}")


def _boundary(b):
    t = int(b.Type)
    return BOUND_NAME.get(t, f"type_{t}")


def _user_shapes(em):
    """Drawn shapes only. AWR inserts port symbols (layer EMSymbols, type polygon/text/port) in front of them, so
    raw Shapes indices move when ports are added; the id used by these tools is the position in this list."""
    return [sh for sh in em.Shapes if int(sh.Type) not in (4, 6) and sh.DrawingLayer.Name != "EMSymbols"]


def _verts(s):
    return [(v.x / MM, v.y / MM) for v in s.Vertices]


def _bbox(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return [min(xs), min(ys), max(xs), max(ys)]


def _resolve_layer(em, layer):
    """Exact drawing layer name, or '<em_layer>:<material>' (e.g. '2:Perfect Conductor') looked up in the mapping."""
    if _p().ProcessDefinitions(1).LayerSetup.DrawingLayers.Exists(layer):
        return layer
    m = re.fullmatch(r"(\d+):(.+)", layer)
    entries = [(e.DrawingLayer, e.EMLayer, e.Material) for e in _mapping(em) if e.EMLayer]
    hits = [n for n, k, mat in entries if m and k == int(m.group(1)) and mat == m.group(2)]
    if len(hits) != 1:
        raise ValueError(f"Layer '{layer}' {'is ambiguous' if hits else 'not found'}. Mapped layers (name, EM layer, material): {entries}")
    return hits[0]


# ---- create / delete ----

def create_em_structure_sync(name, simulator="AXIEM"):
    if simulator not in SIM:
        raise ValueError(f"simulator must be one of {list(SIM)}")
    em = _p().EMStructures.AddEx(name, SIM[simulator])
    if simulator == "Analyst":
        _draw_boundary(em)
    return {"em": em.Name, "simulator": SIM_NAME[int(em.Simulator)], "process_definition": em.ProcessDefinition,
            "note": "AWR starts with 3 dielectric layers (Air 0.5 mm, Diel_1, Diel_2) in a 0.8 x 0.8 mm box; set_em_stackup changes them"
            + ("; Analyst structures start with a rectangular Approx Open simulation boundary the size of the box (set_em_stackup enclosure redraws it)" if simulator == "Analyst" else "")}


def delete_em_structure_sync(name):
    _p().EMStructures.Remove(find(_p().EMStructures, name).Name)
    return {"deleted": name}


# ---- stackup ----

def _set_conductor(em, cond, default_layer):
    name = cond["name"]
    sigma = cond.get("sigma", "perfect")
    if sigma == "perfect":
        material = "Perfect Conductor"
    else:
        cs = _p().Conductors
        t, sig = cond["thickness_mm"] * MM, float(sigma)
        if cs.Exists(name):  # shared by every EM structure in the project: never change it silently
            c = cs(name)
            if abs(c.Thickness - t) > 1e-12 or abs(c.Conductivity - sig) > 1e-6 * sig:
                raise ValueError(f"Conductor '{name}' already exists with other values (used project-wide); pick a new name")
        else:
            c = cs.Add(name)
            c.Thickness, c.Conductivity = t, sig
        material = name
    # Shapes look the drawing layer up in the default PD, so add it there, then push it to this structure's PD.
    dpd = _default_pd()
    if not dpd.LayerSetup.DrawingLayers.Exists(name):
        dpd.LayerSetup.DrawingLayers.Add(name, 255, 0, True, 255, 0, 0.0, 0.0, False, False)
    dpd.UpdateDependentProcessDefinition(em.ProcessDefinition, False, False, False, True, False)
    e = _mapping(em)(name)
    e.EMLayer = int(cond.get("em_layer", default_layer))
    e.Material = material
    return {"drawing_layer": name, "em_layer": e.EMLayer, "material": material}


def set_em_stackup_sync(em, dielectrics=None, conductors=None, enclosure=None, boundaries=None):
    s = _em(em)
    out = {"em": s.Name}
    if dielectrics:
        if len(dielectrics) > MAX_LAYERS:
            raise ValueError(f"At most {MAX_LAYERS} dielectric layers: the COM API cannot add layers safely (Add/StackupUtil corrupt the structure). Build more in the GUI.")
        have = _layers(s)
        if len(dielectrics) > len(have):
            raise ValueError(f"The structure has {len(have)} layer(s) and layers cannot be added; delete_em_structure and create it again")
        # shortcut: names ignored (d['name']): the materials keep AWR's names
        _write_stackup(s, dielectrics)
        got = _solver_stackup(s)
        close = lambda a, b: abs(a - b) <= 1e-9
        bad = len(got) != len(dielectrics) or any(
            not close(g["thickness_m"], d["thickness_mm"] * MM) or not all(close(x, d["er"]) for x in g["er"])
            or not all(close(x, d.get("tand", 0.0)) for x in g["tand"]) for g, d in zip(got, dielectrics))
        if bad:
            raise RuntimeError(f"Solver stackup does not match the request: solver sees {got}, asked for {dielectrics}")
        out["solver_stackup"] = [{"thickness_mm": g["thickness_m"] / MM, "er_xyz": g["er"], "tand_xyz": g["tand"]} for g in got]
    if conductors:
        out["conductors"] = [_set_conductor(s, c, 2) for c in conductors]
    anl = int(s.Simulator) == SIM["Analyst"]
    carry = {}
    if enclosure:
        if anl:
            carry = {k: v[1] for k, v in _edges(_export_xml(s).getroot())["edges"].items()}  # sides survive the redraw
        e = s.Enclosure
        e.XDimension, e.YDimension = enclosure["x_mm"] * MM, enclosure["y_mm"] * MM
        g = enclosure.get("grid_mm")
        if g and not anl:  # shortcut: Analyst meshes itself; the divisions would only distort the box size
            e.XDivisions, e.YDivisions = round(enclosure["x_mm"] / g), round(enclosure["y_mm"] / g)
        if anl:
            _draw_boundary(s, enclosure["x_mm"] * MM, enclosure["y_mm"] * MM)
    sides = (boundaries or {}).get("sides")
    if anl and (sides or carry):
        sides = {k: sides for k in ("left", "right", "top", "bottom")} if isinstance(sides, str) else sides or {}
        want = {**carry, **sides}
        if sides or any(v != "approx_open" for v in want.values()):
            _set_sides(s, want)
    for side, want in (boundaries or {}).items():
        if side == "sides":
            # shortcut: AXIEM walls are always perfect conductor (Analyst sides are handled above)
            if not anl and want != "perfect_conductor":
                raise ValueError("'sides' can only be perfect_conductor for AXIEM (its box walls)")
            continue
        if side not in ("top", "bottom") or want not in BOUND:
            raise ValueError(f"boundaries: top/bottom/sides with values {list(BOUND)} (pml and others are not settable via COM in v17)")
        b = s.Enclosure.EnclosureTop if side == "top" else s.Enclosure.EnclosureBottom
        b.Type = BOUND[want]
        if _boundary(b) != want:
            raise RuntimeError(f"AWR did not accept {side}={want} (reads back {_boundary(b)})")
    out["info"] = em_info_sync(em)
    return out


def set_em_option_sync(em, name, value):
    """Set one solver option of this structure by name (em.Options: Em3DP_AMR_Tolerance, Em3DP_AMR_MaxIterations, Em3DP_RelativeMeshSize, Mesh_meshDensity...)."""
    s = _em(em)
    o = next((o for o in s.Options if o.Name == name), None)
    if o is None:
        raise ValueError(f"No option '{name}'. Analyst: {[o.Name for o in s.Options if o.Name.startswith(('Em3DP', 'Mesh'))]}")
    old, o.Value = o.Value, value
    return {"em": s.Name, "option": name, "old": old, "new": o.Value, "uses_project_options": bool(s.UseProjectOptions)}


# ---- shapes ----

def add_em_shape_sync(em, kind, layer, x=None, y=None, w=None, h_=None, points=None, width=None):
    s = _em(em)
    ln = _resolve_layer(s, layer)
    sh = s.Shapes
    if kind in ("rect", "ellipse", "via"):
        if None in (x, y, w, h_):
            raise ValueError(f"{kind} needs x, y, w, h (mm; x, y = lower-left corner of the bounding box)")
        a = (x * MM, y * MM, w * MM, h_ * MM)
        shape = sh.AddRectangle(*a, ln) if kind == "rect" else sh.AddEllipse(*a, ln) if kind == "ellipse" else sh.AddVia(*a, ln, False)
    elif kind in ("polygon", "path"):
        if not points or len(points) < (3 if kind == "polygon" else 2):
            raise ValueError(f"{kind} needs points [[x, y], ...] in mm")
        flat = [c * MM for p in points for c in p]
        if kind == "polygon":
            shape = sh.AddPolygon(flat, ln)
        elif not width:
            raise ValueError("path needs width (mm)")
        else:
            shape = sh.AddPath(flat, width * MM, ln, 2, 1, 0.0)  # flush ends, mitred corners
    else:
        raise ValueError("kind must be rect, polygon, path, ellipse or via")
    mine = _user_shapes(s)
    ln = shape.DrawingLayer.Name
    row = _shape_row(len(mine), shape, kind)
    # AWR keeps shapes sorted by layer, so the id of a shape can change when later shapes are added; layer + n is stable
    return {**row, "id": next(i for i, m in enumerate(mine, 1) if m.DrawingLayer.Name == ln and _verts(m) == _verts(shape)),
            "n_on_layer": sum(m.DrawingLayer.Name == ln for m in mine)}


def _shape_row(i, shape, kind=None):
    pts = _verts(shape)
    return {"id": i, "kind": kind or SHAPE_TYPE.get(int(shape.Type), int(shape.Type)), "layer": shape.DrawingLayer.Name, "bbox_mm": _bbox(pts)}


# ---- ports ----

def _port_row(pt):
    pts = [(v.x / MM, v.y / MM) for v in pt.Vertices]
    flags = int(pt.Flags)
    return {"number": int(pt.Number), "kind": h.PORT_KIND.get(flags, f"flags_{flags}"), "flags": flags,
            "edge": EDGE_TYPE.get(int(pt.Type)), "em_layer": int(pt.Layer), "segment_mm": [pts[0], pts[1]],
            "impedance_ohm": [pt.Impedance.Real, pt.Impedance.Imaginary], "excited": bool(pt.Termination.ExcitationPort),
            "deembed": bool(pt.Deembed), "associated": bool(pt.IsAssociated), "info": pt.InfoText}


def add_em_port_sync(em, type, at, number=None, impedance=50, excitation=None, negative_of=None, extent_mm=None, deembed=None):
    s = _em(em)
    if type not in FLAGS:
        raise ValueError(f"type must be one of {list(FLAGS)}")
    sim = SIM_NAME[int(s.Simulator)]
    if sim == "AXIEM" and type != "edge":
        raise ValueError("AXIEM has only edge ports; lumped and wave ports need simulator='Analyst'")
    if "shape" in at or "layer" in at:
        mine = _user_shapes(s)
        if "layer" in at:  # ids shift when a shape lands on a layer that sorts earlier, so a layer + n-th shape is the stable form
            ln = _resolve_layer(s, at["layer"])
            mine = [m for m in mine if m.DrawingLayer.Name == ln]
            at = {**at, "shape": at.get("n", 1)}
        if not 1 <= int(at["shape"]) <= len(mine):
            raise ValueError(f"No shape {at['shape']}; found {len(mine)}")
        sh = mine[int(at["shape"]) - 1]
        p1, p2 = h.edge_segment(_verts(sh), at["edge"])
    else:
        p1, p2 = at["p1"], at["p2"]
    existing = [int(p.Number) for p in s.Ports]
    if negative_of is not None:
        if type != "lumped_diff":
            raise ValueError("negative_of only goes with lumped_diff")
        number = -abs(int(negative_of))
    elif number is None:
        number = max([abs(n) for n in existing] + [0]) + 1
    if int(number) in existing:
        raise ValueError(f"Port {number} already exists")
    s.Shapes.AddPort(p1[0] * MM, p1[1] * MM, p2[0] * MM, p2[1] * MM, int(number))
    pt = next(p for p in s.Ports if int(p.Number) == int(number))
    if FLAGS[type] is not None:
        pt.Flags = FLAGS[type]
    if type == "wave_custom" and extent_mm:
        pt.PhysicalThickness = extent_mm * MM  # shortcut: only the height is settable; the lateral box is not exposed
    if impedance != 50:
        pt.Termination.Impedance.Real = float(impedance)
    if excitation is not None:
        pt.Termination.ExcitationPort = bool(excitation)
    if deembed is not None:
        pt.Deembed = bool(deembed)
    return _port_row(pt)


# ---- inspect + lint ----

def em_info_sync(em):
    p = _p()
    s = _em(em)
    sim = SIM_NAME.get(int(s.Simulator), int(s.Simulator))
    e = s.Enclosure
    layers = _layers(s)
    thick = [m.Thickness / MM for m in layers]
    height = sum(thick)
    z = lambda k: sum(thick[k - 1:])  # height of EM layer k (interface above dielectric k) over the bottom wall
    mapped = {en.DrawingLayer: (int(en.EMLayer), en.Material, bool(en.IsVia)) for en in _mapping(s) if en.EMLayer}
    shapes = []
    for i, sh in enumerate(_user_shapes(s), 1):
        row = _shape_row(i, sh)
        k = mapped.get(row["layer"], (0, "", False))[0]
        if row["layer"] == "EMBoundary":
            continue
        shapes.append({**row, "em_layer": k, "z_mm": z(k) if k else None})
    fsrc = p.Frequencies if s.UseProjectFrequencies else s.Frequencies
    ports = sorted((_port_row(pt) for pt in s.Ports), key=lambda r: (abs(r["number"]), -r["number"]))
    try:
        top, bot = _boundary(e.EnclosureTop), _boundary(e.EnclosureBottom)
    except Exception as ex:  # reading .Type is fine; kept defensive because a corrupt structure raises Access Violation
        raise RuntimeError(f"Cannot read the enclosure of '{em}': {ex}") from None
    boundary = None
    if sim == "Analyst" and _boundary_objs(s):  # without one the export fails
        boundary = _edges(_export_xml(s).getroot())
        boundary["edges"] = {k: v[1] for k, v in boundary["edges"].items()}
    return {
        "em": s.Name, "simulator": sim, "process_definition": s.ProcessDefinition,
        "dielectrics": [{"layer": k, "name": m.Name, "thickness_mm": t, "er": m.DielectricConstant, "tand": m.LossTangent}
                        for k, (m, t) in enumerate(zip(layers, thick), 1)],
        "enclosure": {"x_mm": e.XDimension / MM, "y_mm": e.YDimension / MM, "height_mm": height,
                      "x_div": e.XDivisions, "y_div": e.YDivisions, "cell_mm": e.XCellSize / MM},
        "z_top_mm": height,
        "boundaries": {"top": top, "bottom": bot, "sides": "perfect_conductor (box walls)" if sim == "AXIEM" else (boundary or {}).get("edges", "no boundary")},
        "boundary": boundary,
        "layers": [{"drawing_layer": n, "em_layer": k, "material": m, "via": v} for n, (k, m, v) in mapped.items()],
        "frequencies_hz": [f.Value for f in fsrc], "uses_project_frequencies": bool(s.UseProjectFrequencies),
        "shapes": shapes, "ports": ports,
    }


def check_em_setup_sync(em, radiating=False):
    return h.lint_em({**em_info_sync(em), "radiating": radiating})
