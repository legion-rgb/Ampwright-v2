"""Schematic design over COM: find, place, wire, inspect. Callers work in element IDs and pins ('R1:2')."""
import helpers as h
from connection import awr, find

_models = None  # (name, description, category) of every AWR model, read once


def _sch(schematic):
    return find(awr().Project.Schematics, schematic)


def _refs(sch):
    """(ref, element) pairs. ref is the ID ('R1'); parts without one (GND) get 'GND#2' when repeated."""
    els = list(sch.Elements)
    names = [e.Name for e in els]
    return [(f"{n}#{names[:i + 1].count(n)}" if names.count(n) > 1 else n.split(".", 1)[-1], e)
            for i, (n, e) in enumerate(zip(names, els))]


def _elem(sch, ref):
    refs = _refs(sch)
    hits = [e for r, e in refs if ref in (r, e.Name)]
    if len(hits) != 1:
        raise ValueError(f"Element '{ref}' {'is ambiguous' if hits else 'not found'} in '{sch.Name}'. Use one of: {[r for r, _ in refs]}")
    return hits[0]


def _new_ref(sch, e):
    return [r for r, x in _refs(sch) if x.Name == e.Name][-1]  # a just-added part is the last of its name


def _pin(sch, ref):
    eid, num = h.parse_pin(ref)
    e = _elem(sch, eid)
    if num > e.Nodes.Count:
        raise ValueError(f"{e.Name} has {e.Nodes.Count} pin(s), no pin {num}")
    return e, num


def _xy(e, num):
    n = e.Nodes(num)
    return n.x, n.y


def _same_net(sch, a, b):
    """True if pins a and b, each (element, pin), share a net after AWR recomputes connectivity."""
    sch.UpdateConnectivity()  # NodeNumber is stale until this runs
    return a[0].Nodes(a[1]).NodeNumber == b[0].Nodes(b[1]).NodeNumber


def _params(e):
    return [{"name": p.Name, "value": p.ValueAsString, "unit": p.UnitString} for p in e.Parameters]


def _info(ref, e):
    return {"name": e.Name, "id": ref, "model": e.Name.split(".")[0], "parameters": _params(e),
            "pins": [{"pin": i, "net": n.NodeNumber, "connected": bool(n.Connected), "x": n.x, "y": n.y}
                     for i, n in enumerate(e.Nodes, 1)]}


def _set_param(e, name, value):
    p = find(e.Parameters, name)
    if isinstance(value, str) and name != "ID":
        try:  # agents' tool calls turn numbers into text and back; any plain number means SI, whatever its type
            value = float(value)
        except ValueError:
            pass
    if isinstance(value, (int, float)):
        p.ValueAsDouble = value  # numbers are SI (F, H, Ohm, m, Hz)
    else:
        p.ValueAsString = str(value)  # an expression or variable name, read in display units ('2*500' pF)


def get_parameters_sync(schematic, element):
    e = _elem(_sch(schematic), element)
    return {"element": e.Name, "parameters": _params(e)}


def set_parameter_sync(schematic, element, parameter, value):
    e = _elem(_sch(schematic), element)
    p = find(e.Parameters, parameter)
    old = p.ValueAsString
    _set_param(e, parameter, value)
    return {"element": e.Name, "parameter": parameter, "old": old, "new": p.ValueAsString, "unit": p.UnitString}


def list_elements_sync(schematic):
    sch = _sch(schematic)
    sch.UpdateConnectivity()
    return [_info(r, e) for r, e in _refs(sch)]


def list_wires_sync(schematic):
    out = []
    for w in _sch(schematic).Wires:
        try:
            net = w.ParentNet.ElectNetName
        except Exception:
            net = None
        out.append({"x1": w.x1, "y1": w.y1, "x2": w.x2, "y2": w.y2, "net": net})
    return out


def search_models_sync(query, limit=20):
    global _models
    app = awr()
    if _models is None:  # ~15 s for ~1700 models over COM, so read once per server run
        _models = [(m.Name, m.Description, m.CategoryPath) for m in app.Models]
    words = query.lower().split()
    q = query.strip().upper()
    hits = [row for row in _models if all(w in " ".join(row).lower() for w in words)]
    hits.sort(key=lambda r: (r[0].upper() != q, not r[0].upper().startswith(q), r[0]))
    out = []
    for name, desc, cat in hits[:limit]:
        m = app.Models(name)
        out.append({"name": name, "description": desc, "category": cat, "pins": m.NodeCount,
                    "parameters": list(m.ParameterNames or [])})
    return {"total_matches": len(hits), "models": out}


def create_schematic_sync(name):
    return {"schematic": awr().Project.Schematics.Add(name).Name}


def add_element_sync(schematic, model, params, id=None, rotation=0, near=None):
    sch = _sch(schematic)
    boxes = [(e.Left, e.Top, e.Left + e.Width, e.Top + e.Height) for e in sch.Elements]
    anchor = _elem(sch, near) if near else None
    x, y = h.free_spot(boxes, (anchor.x, anchor.y) if anchor else None)
    params = dict(params or {})
    if model == "SUBCKT":  # Elements.Add cannot make a subcircuit; NET names a netlist or schematic in the project
        e = sch.Elements.AddSubcircuit(params.pop("NET"), x, y, rotation, False, "", 0)
    else:
        e = sch.Elements.Add(model, x, y, rotation, False, "")
    try:
        if id:
            _set_param(e, "ID", id)
        for k, v in params.items():
            _set_param(e, k, v)
    except Exception:
        e.Delete()  # don't leave a half-configured part behind
        raise
    sch.UpdateConnectivity()
    return _info(_new_ref(sch, e), e)


def _wire(sch, a, b, what, b_must_be_free=False):
    """Draw a route a -> b that touches no other pin or wire end; refuse rather than short something."""
    obstacles = [(n.x, n.y) for e in sch.Elements for n in e.Nodes]
    obstacles += [p for w in sch.Wires for p in ((w.x1, w.y1), (w.x2, w.y2))]
    wires = [(w.x1, w.y1, w.x2, w.y2) for w in sch.Wires]
    segs = None if b_must_be_free and b in obstacles else h.route(a, b, obstacles, wires)
    if segs is None:
        raise ValueError(f"Every simple route for {what} would touch another pin or wire. Move a part "
                         "(delete_element, then add_element with near=...) or connect through another pin.")
    for s in segs:
        sch.Wires.Add(*s)
    return segs


def connect_sync(schematic, from_pin, to_pin):
    sch = _sch(schematic)
    a, b = _pin(sch, from_pin), _pin(sch, to_pin)
    segs = _wire(sch, _xy(*a), _xy(*b), f"{from_pin} -> {to_pin}")
    return {"from": from_pin, "to": to_pin, "wires": segs, "connected": _same_net(sch, a, b)}


def _attach(schematic, pin, model, body, length, params):
    """Place a 1-pin part (PORT, GND) `length` away from `pin`, on the side the pin faces, and wire it."""
    sch = _sch(schematic)
    e, num = _pin(sch, pin)
    px, py = _xy(e, num)
    side = h.pin_side((px, py), (e.Left + e.Width / 2, e.Top + e.Height / 2))
    x, y = h.offset((px, py), side, length)
    _wire(sch, (px, py), (x, y), f"the {model} stub on {pin}", True)  # before placing, so a refusal leaves nothing
    new = sch.Elements.Add(model, x, y, h.rotation(body, side), False, "")
    for k, v in params.items():
        _set_param(new, k, v)
    ok = _same_net(sch, (e, num), (new, 1))
    return {**_info(_new_ref(sch, new), new), "attached_to": pin, "connected": ok}


def add_port_sync(schematic, pin, number=None, z0=50):
    params = {"Z": z0} if number is None else {"P": number, "Z": z0}
    return _attach(schematic, pin, "PORT", "left", 1000, params)


def add_ground_sync(schematic, pin):
    return _attach(schematic, pin, "GND", "down", 500, {})


def delete_element_sync(schematic, element):
    sch = _sch(schematic)
    e = _elem(sch, element)
    name = e.Name
    pins = {_xy(e, i) for i in range(1, e.Nodes.Count + 1)}
    e.Delete()
    others = {(n.x, n.y) for x in sch.Elements for n in x.Nodes}
    wires = [(w.x1, w.y1, w.x2, w.y2) for w in sch.Wires]
    kill, frontier = set(), pins - others  # pins touching another part's pin have no wire of their own
    while frontier:  # follow each wire from the deleted pins through plain corners (L routes are 2 segments)
        nxt = set()
        for i, w in enumerate(wires):
            if i in kill:
                continue
            for p, q in (((w[0], w[1]), (w[2], w[3])), ((w[2], w[3]), (w[0], w[1]))):
                if p in frontier:
                    kill.add(i)
                    # shortcut: stops at junctions and mid-wire T joins are not seen; the far end stays if 2+ wires meet there
                    if q not in others and sum(q in ((v[0], v[1]), (v[2], v[3])) for j, v in enumerate(wires) if j != i and j not in kill) == 1:
                        nxt.add(q)
                    break
        frontier = nxt
    for i in sorted(kill, reverse=True):  # high index first: Remove shifts later indices down
        sch.Wires.Remove(i + 1)
    return {"deleted": name, "wires_removed": len(kill)}


def delete_schematic_sync(name):
    awr().Project.Schematics.Remove(find(awr().Project.Schematics, name).Name)
    return {"deleted": name}


def add_shunt_sync(schematic, pin, model, params=None, id=None):
    sch = _sch(schematic)
    e, num = _pin(sch, pin)
    px, py = _xy(e, num)
    _wire(sch, (px, py), (px, py + 1000), f"the {model} shunt on {pin}", True)  # before placing, so a refusal leaves nothing
    for rot in (270, 0, 90, 180):  # which rotation hangs pin 2 straight below pin 1 depends on the symbol (RES: 270, DCVS: 0)
        new = sch.Elements.Add(model, px, py + 1000, rot, False, "")
        if new.Nodes.Count == 2 and _xy(new, 2)[0] == px and _xy(new, 2)[1] > py + 1000:
            break
        new.Delete()
    else:
        sch.Wires.Remove(sch.Wires.Count)  # the stub wire drawn above is the last one
        raise ValueError(f"No rotation of {model} puts pin 2 straight below pin 1; use add_element and connect")
    try:
        if id:
            _set_param(new, "ID", id)
        for k, v in (params or {}).items():
            _set_param(new, k, v)
    except Exception:
        delete_element_sync(schematic, _new_ref(sch, new))  # part and its stub wire
        raise
    ref = _new_ref(sch, new)
    gnd = add_ground_sync(schematic, f"{ref}:2")  # shortcut: refused (part stays) if the ground stub would touch another pin
    return {"part": _info(ref, new), "ground": gnd["id"], "connected": _same_net(sch, (e, num), (new, 1))}


def add_equation_sync(expression, document=None):
    p = awr().Project
    if document:
        names = [s.Name for s in p.Schematics]
        doc = p.Schematics(document) if document in names else find(p.GlobalDefinitionDocuments, document)
    else:
        doc = p.GlobalDefinitionDocuments(1)
    eqs = doc.Equations
    # shortcut: stacks equations in a column left of the placement grid; they may overlap hand-placed text
    eq = eqs.Add(expression, -6000, 400 * eqs.Count)
    return {"document": doc.Name, "expression": eq.Expression}


def import_netlist_sync(name, text):
    nl = awr().Project.Netlists.Add(name)
    nl.Text = text
    return {"netlist": nl.Name, "lines": len(text.splitlines()), "note": "syntax errors show in status_messages after simulate"}
