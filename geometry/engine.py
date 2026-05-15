"""
CADMentor Geometry Engine — Deterministic Projection Module

This module contains pure-math geometry computation functions for
descriptive geometry (orthographic projections).

ALL functions are deterministic:
  - Same input → always same output
  - NO AI, NO randomness
  - Pure coordinate geometry only

Coordinate system:
  - XY reference line sits at y = 0
  - Front view (elevation) is drawn ABOVE or BELOW the XY line
  - Top view (plan) is drawn BELOW or ABOVE the XY line
  - x = 0 is the default projection axis (can be offset)

Projection rules (first-angle projection):
  - Distance ABOVE HP  → front view y is POSITIVE (above XY)
  - Distance BELOW HP  → front view y is NEGATIVE (below XY)
  - Distance IN FRONT OF VP → top view y is NEGATIVE (below XY)
  - Distance BEHIND VP → top view y is POSITIVE (above XY)
"""

from typing import Any


# ── POINT PROJECTION (FULLY IMPLEMENTED) ──


def point_projection(parsed_data: dict[str, Any]) -> dict[str, Any]:
    """
    Compute the front view and top view coordinates for a point,
    given parsed position data from Gemini.

    This is the base case for all projection geometry.

    Args:
        parsed_data: The validated 'parsed' dict from the /parse response.
            Expected keys:
                - shape: must be "point"
                - position: {
                    above_hp, below_hp, infront_vp, behind_vp,
                    on_hp, on_vp
                  }

    Returns:
        dict with:
            - "points": {
                "front_view": { "x": float, "y": float },
                "top_view":   { "x": float, "y": float }
              }
            - "steps": list of drawing steps for AutoCAD

    Geometry rules:
        XY line = y = 0 (reference axis)

        Front view (elevation):
            above HP  →  y = +distance  (above XY)
            below HP  →  y = -distance  (below XY)
            on HP     →  y = 0

        Top view (plan):
            in front of VP  →  y = -distance  (below XY)
            behind VP        →  y = +distance  (above XY)
            on VP            →  y = 0
    """
    position = parsed_data.get("position", {})

    # ── Compute front view y-coordinate ──
    front_y = 0.0

    if position.get("on_hp"):
        front_y = 0.0
    elif position.get("above_hp") is not None:
        front_y = float(position["above_hp"])
    elif position.get("below_hp") is not None:
        front_y = -float(position["below_hp"])

    # ── Compute top view y-coordinate ──
    top_y = 0.0

    if position.get("on_vp"):
        top_y = 0.0
    elif position.get("infront_vp") is not None:
        top_y = -float(position["infront_vp"])
    elif position.get("behind_vp") is not None:
        top_y = float(position["behind_vp"])

    # ── Use x = 0 as the default projection axis ──
    point_x = 0.0

    # ── Build result ──
    points = {
        "front_view": {"x": point_x, "y": front_y},
        "top_view": {"x": point_x, "y": top_y},
    }

    # ── Generate drawing steps ──
    steps = _generate_point_steps(point_x, front_y, top_y)

    return {
        "points": points,
        "steps": steps,
    }


def _generate_point_steps(
    point_x: float,
    front_y: float,
    top_y: float,
    xy_line_extent: float = 100.0,
) -> list[dict]:
    """
    Generate the ordered drawing steps for a point projection.

    The sequence follows how a human would construct this on paper:
    1. Draw the XY reference line
    2. Draw a vertical projection line through the point's x-position
    3. Mark the front view (elevation)
    4. Mark the top view (plan)
    5. Draw projection lines from the XY line to each view

    Args:
        point_x: x-coordinate for both views
        front_y: y-coordinate of front view (above/below XY)
        top_y: y-coordinate of top view (above/below XY)
        xy_line_extent: how far the XY reference line extends from center
    """
    steps = []

    # Step 1: Draw XY reference line (horizontal axis)
    steps.append({
        "step_id": 1,
        "type": "line",
        "description": "Draw XY reference line",
        "parameters": {
            "x1": -xy_line_extent,
            "y1": 0.0,
            "x2": xy_line_extent,
            "y2": 0.0,
        },
        "layer": "CONSTRUCTION",
    })

    # Step 2: Draw vertical projection line through point's x-position
    # Extends from the lowest point to the highest point
    proj_line_top = max(front_y, top_y, 10.0) + 10.0
    proj_line_bottom = min(front_y, top_y, -10.0) - 10.0

    steps.append({
        "step_id": 2,
        "type": "line",
        "description": "Draw vertical projection line",
        "parameters": {
            "x1": point_x,
            "y1": proj_line_bottom,
            "x2": point_x,
            "y2": proj_line_top,
        },
        "layer": "CONSTRUCTION",
    })

    # Step 3: Mark front view (elevation)
    front_label = "a'" if front_y >= 0 else "a'"
    steps.append({
        "step_id": 3,
        "type": "circle",
        "description": f"Mark front view (elevation) at y={front_y}",
        "parameters": {
            "cx": point_x,
            "cy": front_y,
            "radius": 1.5,
        },
        "layer": "OBJECT",
    })

    # Step 4: Mark top view (plan)
    steps.append({
        "step_id": 4,
        "type": "circle",
        "description": f"Mark top view (plan) at y={top_y}",
        "parameters": {
            "cx": point_x,
            "cy": top_y,
            "radius": 1.5,
        },
        "layer": "OBJECT",
    })

    # Step 5: Draw projection line from XY to front view
    if abs(front_y) > 0.001:
        steps.append({
            "step_id": 5,
            "type": "line",
            "description": "Draw projection line from XY to front view",
            "parameters": {
                "x1": point_x,
                "y1": 0.0,
                "x2": point_x,
                "y2": front_y,
            },
            "layer": "PROJECTION",
        })

    # Step 6: Draw projection line from XY to top view
    if abs(top_y) > 0.001:
        next_id = len(steps) + 1
        steps.append({
            "step_id": next_id,
            "type": "line",
            "description": "Draw projection line from XY to top view",
            "parameters": {
                "x1": point_x,
                "y1": 0.0,
                "x2": point_x,
                "y2": top_y,
            },
            "layer": "PROJECTION",
        })

    return steps


# ── LINE PROJECTION ──

def line_projection(parsed_data: dict[str, Any]) -> dict[str, Any]:
    import math

    position = parsed_data.get("position", {})
    dimensions = parsed_data.get("dimensions", {})
    inclination = parsed_data.get("inclination", {})

    length = float(dimensions.get("length") or dimensions.get("true_length") or 50.0)
    angle_to_hp = float(inclination.get("angle_to_hp") or 0.0)
    angle_to_vp = float(inclination.get("angle_to_vp") or 0.0)

    # Endpoint A
    a_front_y = float(position.get("above_hp", 0)) if "above_hp" in position else -float(position.get("below_hp", 0)) if "below_hp" in position else 0.0
    a_top_y = -float(position.get("infront_vp", 0)) if "infront_vp" in position else float(position.get("behind_vp", 0)) if "behind_vp" in position else 0.0

    a_x = 0.0
    a_front = {"x": a_x, "y": a_front_y}
    a_top = {"x": a_x, "y": a_top_y}

    has_hp_angle = angle_to_hp != 0
    has_vp_angle = angle_to_vp != 0

    if has_hp_angle and has_vp_angle:
        theta = math.radians(angle_to_hp)
        phi = math.radians(angle_to_vp)

        # Stage 1: TL in front view
        b1_front = {"x": a_x + length * math.cos(theta), "y": a_front_y + length * math.sin(theta)}
        b1_top = {"x": b1_front["x"], "y": a_top_y} # horizontal line in top view

        # Stage 2: TL in top view
        b2_top = {"x": a_x + length * math.cos(phi), "y": a_top_y - length * math.sin(phi)}
        b2_front = {"x": b2_top["x"], "y": a_front_y} # horizontal line in front view

        # Final positions
        x_final = length * math.sqrt(abs(math.cos(theta)**2 - math.sin(phi)**2))
        b_front = {"x": a_x + x_final, "y": b1_front["y"]}
        b_top = {"x": a_x + x_final, "y": b2_top["y"]}

        stage_data = {
            "b1_front": b1_front, "b1_top": b1_top,
            "b2_front": b2_front, "b2_top": b2_top,
            "true_length": length, "theta": angle_to_hp, "phi": angle_to_vp
        }
    elif has_hp_angle:
        theta = math.radians(angle_to_hp)
        b_front = {"x": a_x + length * math.cos(theta), "y": a_front_y + length * math.sin(theta)}
        b_top = {"x": b_front["x"], "y": a_top_y}
        stage_data = None
    elif has_vp_angle:
        phi = math.radians(angle_to_vp)
        b_top = {"x": a_x + length * math.cos(phi), "y": a_top_y - length * math.sin(phi)}
        b_front = {"x": b_top["x"], "y": a_front_y}
        stage_data = None
    else:
        b_front = {"x": a_x + length, "y": a_front_y}
        b_top = {"x": a_x + length, "y": a_top_y}
        stage_data = None

    points = {"A_front": a_front, "A_top": a_top, "B_front": b_front, "B_top": b_top}
    steps = _generate_line_steps(a_front, a_top, b_front, b_top, stage_data=stage_data)
    return {"points": points, "steps": steps}


def _generate_line_steps(a_front, a_top, b_front, b_top, xy_line_extent=100.0, stage_data=None):
    import math
    steps = []
    sid = 0

    def _step(stype, desc, params, layer="CONSTRUCTION"):
        nonlocal sid
        sid += 1
        steps.append({"step_id": sid, "type": stype, "description": desc, "parameters": params, "layer": layer})

    all_x = [a_front["x"], a_top["x"], b_front["x"], b_top["x"]]
    all_y = [a_front["y"], a_top["y"], b_front["y"], b_top["y"]]
    if stage_data:
        all_x += [stage_data["b1_front"]["x"], stage_data["b2_top"]["x"]]
        all_y += [stage_data["b1_front"]["y"], stage_data["b2_top"]["y"]]

    max_x = max(abs(x) for x in all_x)
    xy_ext = max(xy_line_extent, max_x + 30)

    _step("line", "Draw XY reference line", {"x1": -xy_ext, "y1": 0.0, "x2": xy_ext, "y2": 0.0})
    y_lo, y_hi = min(all_y) - 15, max(all_y) + 15
    _step("line", "Vertical projector through A", {"x1": a_front["x"], "y1": y_lo, "x2": a_front["x"], "y2": y_hi}, "PROJECTION")
    _step("circle", "Mark a' (front view)", {"cx": a_front["x"], "cy": a_front["y"], "radius": 1.5}, "OBJECT")
    _step("circle", "Mark a (top view)", {"cx": a_top["x"], "cy": a_top["y"], "radius": 1.5}, "OBJECT")

    if stage_data:
        b1f, b1t = stage_data["b1_front"], stage_data["b1_top"]
        b2f, b2t = stage_data["b2_front"], stage_data["b2_top"]

        # Stage 1: TL in front
        _step("line", "Draw a'b1' (TL in FV)", {"x1": a_front["x"], "y1": a_front["y"], "x2": b1f["x"], "y2": b1f["y"]})
        _step("line", "Projector b1' down to b1", {"x1": b1f["x"], "y1": b1f["y"], "x2": b1t["x"], "y2": b1t["y"]}, "PROJECTION")
        _step("line", "Draw ab1 (Plan Length)", {"x1": a_top["x"], "y1": a_top["y"], "x2": b1t["x"], "y2": b1t["y"]})
        _step("line", "Locus of b'", {"x1": b_front["x"] - 20, "y1": b1f["y"], "x2": b_front["x"] + 20, "y2": b1f["y"]})

        # Stage 2: TL in top
        _step("line", "Draw ab2 (TL in TV)", {"x1": a_top["x"], "y1": a_top["y"], "x2": b2t["x"], "y2": b2t["y"]})
        _step("line", "Projector b2 up to b2'", {"x1": b2t["x"], "y1": b2t["y"], "x2": b2f["x"], "y2": b2f["y"]}, "PROJECTION")
        _step("line", "Draw a'b2' (Elevation Length)", {"x1": a_front["x"], "y1": a_front["y"], "x2": b2f["x"], "y2": b2f["y"]})
        _step("line", "Locus of b", {"x1": b_top["x"] - 20, "y1": b2t["y"], "x2": b_top["x"] + 20, "y2": b2t["y"]})

        # Final Rotation Arcs
        r_plan = b1t["x"] - a_top["x"]
        ang_start = math.degrees(math.atan2(b_top["y"] - a_top["y"], b_top["x"] - a_top["x"]))
        ang_end = math.degrees(math.atan2(b1t["y"] - a_top["y"], b1t["x"] - a_top["x"]))
        _step("arc", "Rotate plan length ab1 to locus of b", {"cx": a_top["x"], "cy": a_top["y"], "radius": r_plan, "start_angle": min(ang_start, ang_end), "end_angle": max(ang_start, ang_end)})

        r_elev = b2f["x"] - a_front["x"]
        ang_start_f = math.degrees(math.atan2(b_front["y"] - a_front["y"], b_front["x"] - a_front["x"]))
        ang_end_f = math.degrees(math.atan2(b2f["y"] - a_front["y"], b2f["x"] - a_front["x"]))
        _step("arc", "Rotate elevation length a'b2' to locus of b'", {"cx": a_front["x"], "cy": a_front["y"], "radius": r_elev, "start_angle": min(ang_start_f, ang_end_f), "end_angle": max(ang_start_f, ang_end_f)})

        # Final Lines
        _step("line", "Projector b to b'", {"x1": b_top["x"], "y1": b_top["y"], "x2": b_front["x"], "y2": b_front["y"]}, "PROJECTION")
        _step("circle", "Mark b' (final)", {"cx": b_front["x"], "cy": b_front["y"], "radius": 1.5}, "OBJECT")
        _step("circle", "Mark b (final)", {"cx": b_top["x"], "cy": b_top["y"], "radius": 1.5}, "OBJECT")
        _step("line", "Draw a'b' (final FV)", {"x1": a_front["x"], "y1": a_front["y"], "x2": b_front["x"], "y2": b_front["y"]}, "OBJECT")
        _step("line", "Draw ab (final TV)", {"x1": a_top["x"], "y1": a_top["y"], "x2": b_top["x"], "y2": b_top["y"]}, "OBJECT")
    else:
        _step("line", "Draw a'b' (front view)", {"x1": a_front["x"], "y1": a_front["y"], "x2": b_front["x"], "y2": b_front["y"]}, "OBJECT")
        _step("line", "Draw ab (top view)", {"x1": a_top["x"], "y1": a_top["y"], "x2": b_top["x"], "y2": b_top["y"]}, "OBJECT")
        _step("circle", "Mark b' (front view)", {"cx": b_front["x"], "cy": b_front["y"], "radius": 1.5}, "OBJECT")
        _step("circle", "Mark b (top view)", {"cx": b_top["x"], "cy": b_top["y"], "radius": 1.5}, "OBJECT")
        b_y_lo, b_y_hi = min(b_front["y"], b_top["y"]) - 15, max(b_front["y"], b_top["y"]) + 15
        _step("line", "Vertical projector through B", {"x1": b_front["x"], "y1": b_y_lo, "x2": b_front["x"], "y2": b_y_hi}, "PROJECTION")

    return steps


from geometry.planes import plane_projection


# ── SOLID PROJECTION (STUB) ──


def solid_projection(parsed_data: dict[str, Any]) -> dict[str, Any]:
    """
    Compute projections for a 3D solid.

    Args:
        parsed_data: The validated 'parsed' dict.

    Raises:
        NotImplementedError: Not yet implemented.
    """
    raise NotImplementedError("solid_projection is not yet implemented")
