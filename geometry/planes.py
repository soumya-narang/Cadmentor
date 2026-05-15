# ── PLANE PROJECTION ENGINE ──
# This module implements the 3-stage Change of Position method for 2D laminas.
#
# Textbook procedure for a plane inclined to both HP and VP:
#
#   Stage 1  –  Plane parallel to HP (true shape in Top View)
#               Front View = single horizontal line ON the XY line
#               Top View   = true shape polygon below XY
#
#   Stage 2  –  Tilt the plane so its surface makes angle θ with HP
#               Front View = the Stage 1 FV line tilted at θ, pinned at
#                            the resting edge/corner on XY
#               Top View   = foreshortened polygon obtained by projecting
#                            Stage 2 FV points DOWN and Stage 1 TV points ACROSS
#
#   Stage 3  –  Rotate the resting edge/corner so it makes angle φ with VP
#               Top View   = Stage 2 TV rotated so the resting element
#                            is at angle φ to XY
#               Front View = project Stage 3 TV points UP and Stage 2 FV
#                            points ACROSS; connect intersections
#
# Coordinate system:
#   y > 0   = above XY line (Front View space)
#   y < 0   = below XY line (Top View space)
#   y = 0   = XY reference line
#
# All three stages are laid out side-by-side along the X-axis with a gap
# between them so the student can see the construction clearly.

import math
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def plane_projection(parsed_data: dict[str, Any]) -> dict[str, Any]:
    """
    Compute front and top views for a 2D plane (lamina).
    Returns a dict with 'points' and 'steps' suitable for DrawingExecutor.
    """
    position    = parsed_data.get("position", {})
    dimensions  = parsed_data.get("dimensions", {})
    inclination = parsed_data.get("inclination", {})
    extra       = parsed_data.get("extra", {})

    # ── 1. Determine shape type ──────────────────────────────────────────
    plane_type = (
        parsed_data.get("shape_type", "")
        or extra.get("type", "")
        or extra.get("shape_type", "")
        or dimensions.get("type", "")
        or _infer_plane_type(dimensions)
    ).lower().strip()

    # Fallback: scan raw text for shape keywords
    if not plane_type or plane_type in ("rectangle", "lamina", ""):
        raw_str = str(parsed_data).lower()
        for kw, st in [("pentagon", "pentagon"), ("hexagon", "hexagon"),
                        ("triangle", "triangle"), ("square", "square")]:
            if kw in raw_str:
                plane_type = st
                break

    side  = float(dimensions.get("side") or dimensions.get("side_length") or dimensions.get("edge")
                  or dimensions.get("length") or dimensions.get("base") or 40.0)
    width = float(dimensions.get("width") or dimensions.get("breadth") or side)


    # ── 2. Inclination angles ────────────────────────────────────────────
    theta = math.radians(float(
        inclination.get("angle_to_hp")
        or extra.get("surface_inclination_to_hp")
        or 0.0
    ))

    raw_phi = inclination.get("angle_to_vp")
    if raw_phi is None:
        raw_phi = (extra.get("resting_edge_inclination_to_vp")
                   or extra.get("angle_to_vp") or 0.0)
    phi = math.radians(float(raw_phi))

    # ── 3. Resting element ───────────────────────────────────────────────
    resting_element = (inclination.get("resting_element") or "edge").lower()
    rests_on_corner = "corner" in resting_element

    # ── 4. Generate true-shape vertices ──────────────────────────────────
    #    Oriented so the resting element is at the LEFT (minimum X).
    #    Vertices are centred around the Y-axis.
    local_verts = _generate_shape_vertices(plane_type, side, width, rests_on_corner)
    n = len(local_verts)
    if n < 3:
        return {"points": {}, "steps": []}

    # Shift so that the resting element sits at x = 0
    min_x = min(v[0] for v in local_verts)
    local_verts = [(v[0] - min_x, v[1]) for v in local_verts]

    labels = [chr(ord("a") + i) for i in range(n)]  # lowercase for TV

    # ── 5. STAGE 1 — Plane parallel to HP ────────────────────────────────
    # TV = true shape polygon;  FV = single line ON XY (y = 0)
    s1_tv = [{"x": v[0], "y": -abs(v[1])-10} for v in local_verts]
    # ↑ shift all TV Y downward so polygon sits comfortably below XY

    # For Stage 1 TV, we want the true shape.  local_verts Y-coords are
    # symmetric about 0.  Let's centre the polygon below XY:
    poly_height = max(v[1] for v in local_verts) - min(v[1] for v in local_verts)
    poly_cy     = -(poly_height / 2 + 10)          # centre of polygon in TV
    s1_tv = []
    for v in local_verts:
        s1_tv.append({"x": v[0], "y": poly_cy + v[1]})

    # FV: all vertices project to a single horizontal line on XY (y = 0)
    s1_fv = [{"x": v[0], "y": 0.0} for v in local_verts]

    # ── 6. STAGE 2 — Surface inclined at θ to HP ────────────────────────
    # FV: tilt the Stage 1 FV line about the resting point (x=0, y=0)
    # Each vertex's FV y-coordinate becomes  x_original * sin(θ)
    # Each vertex's FV x-coordinate becomes  x_original * cos(θ)
    s2_fv = []
    s2_tv = []
    for i in range(n):
        x_orig = s1_fv[i]["x"]   # = local_verts[i][0] shifted
        fv_x = x_orig * math.cos(theta)
        fv_y = x_orig * math.sin(theta)
        s2_fv.append({"x": fv_x, "y": fv_y})

        # TV: x comes from Stage 2 FV (projection down), y from Stage 1 TV
        s2_tv.append({"x": fv_x, "y": s1_tv[i]["y"]})

    # ── 7. STAGE 3 — Resting edge inclined at φ to VP ───────────────────
    s3_fv = []
    s3_tv = []

    if theta == 0 and phi == 0:
        s3_fv = [dict(p) for p in s1_fv]
        s3_tv = [dict(p) for p in s1_tv]
    elif phi == 0:
        s3_fv = [dict(p) for p in s2_fv]
        s3_tv = [dict(p) for p in s2_tv]
    else:
        # Rotate Stage 2 TV about the resting point so the resting element
        # makes angle φ with XY.
        #
        # If resting on EDGE:
        #   The resting edge in Stage 2 TV is vertical (along Y-axis).
        #   Its current angle to XY = 90°.  We need it at φ.
        #   Rotation needed = -(90° - φ)  (clockwise).
        #
        # If resting on CORNER:
        #   The diagonal through the corner is along the X-axis.
        #   Its current angle to XY = 0°.  We need it at φ.
        #   Rotation needed = φ  (counter-clockwise).

        if rests_on_corner:
            rot = phi
        else:
            rot = -(math.pi / 2 - phi)

        # Pivot is the resting point in Stage 2 TV
        px = s2_tv[0]["x"]
        py = s2_tv[0]["y"]

        for i in range(n):
            dx = s2_tv[i]["x"] - px
            dy = s2_tv[i]["y"] - py
            rx = dx * math.cos(rot) - dy * math.sin(rot)
            ry = dx * math.sin(rot) + dy * math.cos(rot)
            t3x = px + rx
            t3y = py + ry
            s3_tv.append({"x": t3x, "y": t3y})

            # FV: x from Stage 3 TV, y from Stage 2 FV
            s3_fv.append({"x": t3x, "y": s2_fv[i]["y"]})

    # ── 8. Offset stages horizontally ────────────────────────────────────
    gap = 30.0  # horizontal gap between stages

    # Stage 1 stays at its current X positions (starts near x = 0)
    s1_max_x = max(max(p["x"] for p in s1_fv), max(p["x"] for p in s1_tv))

    if theta > 0:
        s2_offset = s1_max_x + gap
        for p in s2_fv: p["x"] += s2_offset
        for p in s2_tv: p["x"] += s2_offset
        s2_max_x = max(max(p["x"] for p in s2_fv), max(p["x"] for p in s2_tv))
    else:
        s2_offset = 0
        s2_max_x = s1_max_x

    if phi > 0 and theta > 0:
        s3_offset = s2_max_x + gap
        for p in s3_fv: p["x"] += s3_offset
        for p in s3_tv: p["x"] += s3_offset

    # ── 9. Build drawing steps ───────────────────────────────────────────
    steps = _generate_plane_steps(
        labels, n,
        s1_fv, s1_tv,
        s2_fv, s2_tv,
        s3_fv, s3_tv,
        theta, phi
    )

    # ── 10. Build points dict for response ───────────────────────────────
    points = {}
    final_fv = s3_fv if (theta > 0 and phi > 0) else (s2_fv if theta > 0 else s1_fv)
    final_tv = s3_tv if (theta > 0 and phi > 0) else (s2_tv if theta > 0 else s1_tv)
    for i, lbl in enumerate(labels):
        points[f"{lbl}_front"] = final_fv[i]
        points[f"{lbl}_top"]   = final_tv[i]

    return {"points": points, "steps": steps}


# ─────────────────────────────────────────────────────────────────────────────
# STEP GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def _generate_plane_steps(labels, n, f1, t1, f2, t2, f3, t3, theta, phi):
    """
    Build the ordered list of drawing primitives for the 3-stage method.

    Drawing order within each stage follows the textbook drafting sequence:
      1. Draw the view that you KNOW (true shape in Stage 1)
      2. Project to the other view
      3. Mark vertices
    """
    steps = []
    sid = 0

    def _s(stype, desc, params, layer="CONSTRUCTION"):
        nonlocal sid
        sid += 1
        steps.append({
            "step_id": sid,
            "type": stype,
            "description": desc,
            "parameters": params,
            "layer": layer,
        })

    # ── XY reference line ────────────────────────────────────────────────
    all_x = [p["x"] for p in f1 + t1 + f2 + t2 + f3 + t3]
    xy_left  = min(all_x) - 20
    xy_right = max(all_x) + 20
    _s("line", "Draw XY reference line",
       {"x1": xy_left, "y1": 0.0, "x2": xy_right, "y2": 0.0})

    # ══════════════════════════════════════════════════════════════════════
    # STAGE 1:  Plane parallel to HP
    # ══════════════════════════════════════════════════════════════════════

    # 1a. Draw true-shape polygon in Top View
    for i in range(n):
        j = (i + 1) % n
        _s("line", f"Stage 1 TV: edge {labels[i]}{labels[j]}",
           {"x1": t1[i]["x"], "y1": t1[i]["y"],
            "x2": t1[j]["x"], "y2": t1[j]["y"]}, "OBJECT")

    # 1b. Mark TV vertices
    for i in range(n):
        _s("circle", f"Mark {labels[i]} (Stage 1 TV)",
           {"cx": t1[i]["x"], "cy": t1[i]["y"], "radius": 1.0}, "OBJECT")

    # 1c. Draw FV — single horizontal line ON XY (y = 0)
    fv_xs = [p["x"] for p in f1]
    _s("line", "Stage 1 FV: edge-on line on XY",
       {"x1": min(fv_xs), "y1": 0.0, "x2": max(fv_xs), "y2": 0.0}, "OBJECT")

    # 1d. Mark FV vertices on the XY line
    for i in range(n):
        _s("circle", f"Mark {labels[i]}' (Stage 1 FV)",
           {"cx": f1[i]["x"], "cy": 0.0, "radius": 1.0}, "OBJECT")

    # 1e. Projectors: thin dashed lines from each TV vertex straight up to XY
    for i in range(n):
        _s("line", f"Projector {labels[i]} to {labels[i]}'",
           {"x1": t1[i]["x"], "y1": t1[i]["y"],
            "x2": f1[i]["x"], "y2": 0.0}, "PROJECTION")

    # ══════════════════════════════════════════════════════════════════════
    # STAGE 2:  Surface inclined at θ to HP
    # ══════════════════════════════════════════════════════════════════════

    if theta > 0:
        # 2a. Draw tilted FV line (single line from resting point,
        #     tilted at θ).  The resting point stays on XY.
        #     Find the vertex with min y (resting end) and max y (far end).
        fv_min = min(f2, key=lambda p: p["y"])
        fv_max = max(f2, key=lambda p: p["y"])
        _s("line", f"Stage 2 FV: tilt at {math.degrees(theta):.0f} deg to XY",
           {"x1": fv_min["x"], "y1": fv_min["y"],
            "x2": fv_max["x"], "y2": fv_max["y"]}, "OBJECT")

        # 2b. Mark all FV vertices on the tilted line
        for i in range(n):
            _s("circle", f"Mark {labels[i]}' (Stage 2 FV)",
               {"cx": f2[i]["x"], "cy": f2[i]["y"], "radius": 1.0}, "OBJECT")

        # 2c. Vertical projectors: FV down to XY, then XY down to TV
        for i in range(n):
            # FV point down to XY
            if abs(f2[i]["y"]) > 0.1:
                _s("line", f"Projector {labels[i]}' down to XY",
                   {"x1": f2[i]["x"], "y1": f2[i]["y"],
                    "x2": f2[i]["x"], "y2": 0.0}, "PROJECTION")
            # XY down to TV point
            _s("line", f"Projector {labels[i]} down to TV",
               {"x1": t2[i]["x"], "y1": 0.0,
                "x2": t2[i]["x"], "y2": t2[i]["y"]}, "PROJECTION")

        # 2d. Horizontal locus lines from Stage 1 TV across to Stage 2 TV
        for i in range(n):
            _s("line", f"Locus {labels[i]} across",
               {"x1": t1[i]["x"], "y1": t1[i]["y"],
                "x2": t2[i]["x"], "y2": t2[i]["y"]}, "PROJECTION")

        # 2e. Draw foreshortened polygon in Stage 2 TV
        for i in range(n):
            j = (i + 1) % n
            _s("line", f"Stage 2 TV: edge {labels[i]}{labels[j]}",
               {"x1": t2[i]["x"], "y1": t2[i]["y"],
                "x2": t2[j]["x"], "y2": t2[j]["y"]}, "OBJECT")

        # 2f. Mark Stage 2 TV vertices
        for i in range(n):
            _s("circle", f"Mark {labels[i]} (Stage 2 TV)",
               {"cx": t2[i]["x"], "cy": t2[i]["y"], "radius": 1.0}, "OBJECT")

    # ══════════════════════════════════════════════════════════════════════
    # STAGE 3:  Resting edge inclined at φ to VP
    # ══════════════════════════════════════════════════════════════════════

    if phi > 0 and theta > 0:
        # 3a. Draw rotated polygon in Stage 3 TV
        for i in range(n):
            j = (i + 1) % n
            _s("line", f"Stage 3 TV: edge {labels[i]}{labels[j]}",
               {"x1": t3[i]["x"], "y1": t3[i]["y"],
                "x2": t3[j]["x"], "y2": t3[j]["y"]}, "OBJECT")

        # 3b. Mark Stage 3 TV vertices
        for i in range(n):
            _s("circle", f"Mark {labels[i]} (Stage 3 TV)",
               {"cx": t3[i]["x"], "cy": t3[i]["y"], "radius": 1.0}, "OBJECT")

        # 3c. Vertical projectors from Stage 3 TV up to XY line ONLY
        #     (stopping at XY prevents them from cutting through the FV polygon)
        for i in range(n):
            _s("line", f"Projector {labels[i]} up to XY",
               {"x1": t3[i]["x"], "y1": t3[i]["y"],
                "x2": t3[i]["x"], "y2": 0.0}, "PROJECTION")

        # 3c2. Short vertical ticks from XY up to each FV point
        for i in range(n):
            if abs(f3[i]["y"]) > 0.1:  # only if FV point is above XY
                _s("line", f"Projector {labels[i]}' tick up",
                   {"x1": f3[i]["x"], "y1": 0.0,
                    "x2": f3[i]["x"], "y2": f3[i]["y"]}, "PROJECTION")

        # 3d. Horizontal locus lines from Stage 2 FV across to Stage 3 FV
        for i in range(n):
            _s("line", f"Locus {labels[i]}' across",
               {"x1": f2[i]["x"], "y1": f2[i]["y"],
                "x2": f3[i]["x"], "y2": f3[i]["y"]}, "PROJECTION")

        # 3e. Draw final apparent FV polygon
        for i in range(n):
            j = (i + 1) % n
            _s("line", f"Stage 3 FV: edge {labels[i]}'{labels[j]}'",
               {"x1": f3[i]["x"], "y1": f3[i]["y"],
                "x2": f3[j]["x"], "y2": f3[j]["y"]}, "OBJECT")

        # 3f. Mark Stage 3 FV vertices
        for i in range(n):
            _s("circle", f"Mark {labels[i]}' (Stage 3 FV)",
               {"cx": f3[i]["x"], "cy": f3[i]["y"], "radius": 1.0}, "OBJECT")

    return steps


# ─────────────────────────────────────────────────────────────────────────────
# SHAPE GENERATORS
# ─────────────────────────────────────────────────────────────────────────────

def _infer_plane_type(dimensions: dict) -> str:
    """Guess the plane type from dimension keys."""
    keys = set(dimensions.keys())
    if "base" in keys and "height" in keys:
        return "triangle"
    if "width" in keys or "breadth" in keys:
        return "rectangle"
    if "sides" in keys:
        try:
            return {3: "triangle", 4: "square", 5: "pentagon", 6: "hexagon"
                    }.get(int(dimensions["sides"]), "hexagon")
        except (ValueError, TypeError):
            pass
    return "rectangle"


def _generate_shape_vertices(shape_type: str, side: float, width: float,
                              rests_on_corner: bool) -> list[tuple[float, float]]:
    """
    Generate 2D vertices of a regular polygon so that the RESTING ELEMENT
    is at the LEFT (minimum X).

    For resting on EDGE:  the left-most edge is vertical (parallel to Y-axis).
    For resting on CORNER: the left-most vertex is at the leftmost point.

    Returns: list of (x, y) tuples.
    """
    if shape_type in ("square",):
        if rests_on_corner:
            d = side * math.sqrt(2) / 2
            return [(-d, 0), (0, -d), (d, 0), (0, d)]
        else:
            hs = side / 2
            return [(0, -hs), (side, -hs), (side, hs), (0, hs)]

    elif shape_type in ("rectangle", "rectangular"):
        hw = width / 2
        return [(0, -hw), (side, -hw), (side, hw), (0, hw)]

    elif shape_type in ("triangle", "triangular"):
        h = side * math.sqrt(3) / 2
        if rests_on_corner:
            return [(-2 * h / 3, 0), (h / 3, -side / 2), (h / 3, side / 2)]
        else:
            return [(0, -side / 2), (0, side / 2), (h, 0)]

    elif shape_type in ("pentagon", "pentagonal"):
        return _regular_polygon_verts(5, side, rests_on_corner)

    elif shape_type in ("hexagon", "hexagonal"):
        return _regular_polygon_verts(6, side, rests_on_corner)

    else:
        # Unknown → treat as rectangle
        return _generate_shape_vertices("rectangle", side, width, rests_on_corner)


def _regular_polygon_verts(num_sides: int, side: float,
                            rests_on_corner: bool) -> list[tuple[float, float]]:
    """
    Generate vertices of a regular polygon with given side length.

    The polygon is oriented so that:
      - rests_on_corner=False → the left-most EDGE is vertical
      - rests_on_corner=True  → the left-most VERTEX is at the far left

    All vertices are then shifted so that min(x) = 0.
    """
    R = side / (2 * math.sin(math.pi / num_sides))  # circumradius

    if rests_on_corner:
        start_angle = math.pi  # vertex pointing left
    else:
        # Midpoint of left edge should be at angle π,
        # so first vertex is at π + π/n  (half-edge above midpoint)
        start_angle = math.pi + math.pi / num_sides

    verts = []
    for i in range(num_sides):
        angle = start_angle - 2 * math.pi * i / num_sides
        verts.append((R * math.cos(angle), R * math.sin(angle)))

    # Normalise so min X = 0
    min_x = min(v[0] for v in verts)
    verts = [(v[0] - min_x, v[1]) for v in verts]
    return verts
