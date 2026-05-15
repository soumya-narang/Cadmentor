import urllib.request, json

def test_question(q):
    print(f"\n--- Testing: {q} ---")
    try:
        req = urllib.request.Request(
            'http://localhost:8000/parse', 
            data=json.dumps({'question': q}).encode(), 
            headers={'Content-Type': 'application/json'}
        )
        r = urllib.request.urlopen(req, timeout=30)
        res = json.loads(r.read().decode())
        print(f"Shape: {res['parsed']['shape']}")
        if res['parsed']['shape_type']:
            print(f"Shape Type: {res['parsed']['shape_type']}")
        print(f"Dimensions: {res['parsed']['dimensions']}")
        print(f"Position: {res['parsed']['position']}")
        print(f"Inclination: {res['parsed']['inclination']}")
        print(f"Steps: {len(res['steps'])}")
    except urllib.error.HTTPError as e:
        print(f"STATUS: {e.code}")
        print(f"BODY: {e.read().decode()}")

test_question('A point P is 30mm above HP and 40mm in front of VP. Draw its projections.')
test_question('A line AB, 80 mm long, has its end A 15 mm above the HP and 20 mm in front of the VP. The line is inclined at 45 degrees to the HP and 30 degrees to the VP. Draw the projections of the line.')
test_question('A regular pentagon of 30 mm sides has one of its edges on HP. Its surface is inclined at 45 degrees to HP and the resting edge is inclined at 30 degrees to VP. Draw its projections.')
test_question('A regular hexagon of 40 mm side has a corner in the HP. Its surface is inclined at 45 degrees to the HP and the top view of the diagonal through the corner which is in the HP makes an angle of 60 degrees with the VP. Draw its projections.')

