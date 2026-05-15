"""Full integration test of the rewritten planes.py."""
import sys
sys.path.insert(0, ".")
from geometry.planes import plane_projection

data = {
    "shape": "lamina",
    "shape_type": "pentagon",
    "dimensions": {"side": 30},
    "position": {"on_hp": True},
    "inclination": {"angle_to_hp": 45, "angle_to_vp": 30, "resting_element": "edge"},
    "extra": {},
}

res = plane_projection(data)
steps = res["steps"]
print(f"Total steps: {len(steps)}")

for s in steps:
    sid = s["step_id"]
    stype = s["type"]
    layer = s["layer"]
    desc = s["description"]
    p = s["parameters"]
    if stype == "line":
        print(f"  {sid:2d}  {stype:6s}  {layer:12s}  {desc}")
        print(f"       ({p['x1']:.1f}, {p['y1']:.1f}) -> ({p['x2']:.1f}, {p['y2']:.1f})")
    elif stype == "circle":
        print(f"  {sid:2d}  {stype:6s}  {layer:12s}  {desc}")
        print(f"       center=({p['cx']:.1f}, {p['cy']:.1f})")

# Verify key properties:
print("")
print("-- Verification --")

# Stage 1 FV should all be at y=0
s1_fv_steps = [s for s in steps if "Stage 1 FV" in s["description"] and s["type"] == "line"]
for s in s1_fv_steps:
    y1, y2 = s["parameters"]["y1"], s["parameters"]["y2"]
    assert y1 == 0.0 and y2 == 0.0, f"Stage 1 FV not on XY! y1={y1}, y2={y2}"
print("OK: Stage 1 FV is ON the XY line (y=0)")

# Stage 1 TV should all be below XY
s1_tv_steps = [s for s in steps if "Stage 1 TV" in s["description"] and s["type"] == "line"]
for s in s1_tv_steps:
    assert s["parameters"]["y1"] < 0 and s["parameters"]["y2"] < 0, "TV not below XY!"
print("OK: Stage 1 TV is entirely below XY")

# Stage 2 FV should be a SINGLE LINE (not multiple edges)
s2_fv_obj = [s for s in steps if "Stage 2 FV" in s["description"] and s["type"] == "line" and s["layer"] == "OBJECT"]
print(f"OK: Stage 2 FV: {len(s2_fv_obj)} line(s) -- should be exactly 1")
assert len(s2_fv_obj) == 1, f"Expected 1 FV line in Stage 2, got {len(s2_fv_obj)}"

# Stage 2 FV resting point should be on XY
s2_fv = s2_fv_obj[0]["parameters"]
print(f"   Resting point: ({s2_fv['x1']:.1f}, {s2_fv['y1']:.1f})")
assert abs(s2_fv["y1"]) < 0.01, f"Stage 2 resting point not on XY! y={s2_fv['y1']}"
print("OK: Stage 2 FV resting point is ON XY")

# Stage 3 FV should have n edges (connecting the polygon)
s3_fv_edges = [s for s in steps if "Stage 3 FV: edge" in s["description"]]
print(f"OK: Stage 3 FV: {len(s3_fv_edges)} edges (should be 5 for pentagon)")

# Stage 3 FV edges should all be ABOVE or ON XY (y >= 0)
for s in s3_fv_edges:
    y1, y2 = s["parameters"]["y1"], s["parameters"]["y2"]
    assert y1 >= -0.01 and y2 >= -0.01, f"Stage 3 FV below XY! y1={y1}, y2={y2}"
print("OK: Stage 3 FV is above/on XY")

# Stage 3 TV edges should all be BELOW XY (y < 0)
s3_tv_edges = [s for s in steps if "Stage 3 TV: edge" in s["description"]]
for s in s3_tv_edges:
    y1, y2 = s["parameters"]["y1"], s["parameters"]["y2"]
    assert y1 < 0.01 and y2 < 0.01, f"Stage 3 TV above XY! y1={y1}, y2={y2}"
print("OK: Stage 3 TV is below XY")

print("")
print("-- ALL TESTS PASSED --")
