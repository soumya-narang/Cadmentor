# CADMentor — Setup Guide

## Prerequisites

- **AutoCAD 2026** (installed)
- **.NET 8.0 SDK** (for building the plugin)
- **Python 3.10+** (for the backend server)

---

## Step 1: Install .NET 8 SDK

If not already installed:

```powershell
winget install Microsoft.DotNet.SDK.8
```

Verify:
```powershell
dotnet --version
# Should output 8.x.x
```

---

## Step 2: Build the Plugin

```powershell
cd plugin\CADMentor
dotnet build -c Release
```

The compiled DLL will be at:
```
plugin\CADMentor\bin\Release\net8.0-windows\CADMentor.dll
```

---

## Step 3: Install Python Dependencies

```powershell
cd backend
pip install -r requirements.txt
```

---

## Step 4: Start the Backend Server

In a separate terminal:

```powershell
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

Verify it's running:
```powershell
curl http://localhost:8000/health
# Should return: {"status":"ok","version":"0.1.0"}
```

---

## Step 5: Load the Plugin into AutoCAD

1. Open AutoCAD 2026
2. Type `NETLOAD` in the command line
3. Browse to: `plugin\CADMentor\bin\Release\net8.0-windows\CADMentor.dll`
4. You should see: `CADMentor: Ready. Use Shift+V.`

---

## Step 6: Use It

1. **Type your question** in the drawing using the `TEXT` or `MTEXT` command
   - Example: "Draw the front view and top view of a point A 30mm above HP and 40mm in front of VP"

2. **Press Shift+V** — reads the question and sends it to the backend
   - You'll see: `CADMentor: Problem loaded (5 steps). Press again to start drawing.`

3. **Press Shift+V again** — draws step 1
   - You'll see: `CADMentor: [1/5] Step 1: Draw XY reference line`

4. **Keep pressing Shift+V** — each press draws the next step

5. **After all steps** — press Shift+V to reset for a new problem

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `CADMentor: Unable to reach backend` | Make sure the FastAPI server is running on port 8000 |
| Shift+V types "V" | The keyboard hook may not have loaded. Re-run `NETLOAD` |
| Build errors about missing DLLs | Verify AutoCAD 2026 is installed at `C:\Program Files\Autodesk\AutoCAD 2026\` |
| `NETLOAD` fails | Make sure you're loading from the `Release` build output folder |

---

## Auto-Loading (Optional)

To load CADMentor automatically when AutoCAD starts, add this to your `acad.lsp` file:

```lisp
(command "NETLOAD" "C:\\full\\path\\to\\CADMentor.dll")
```

Or use the `APPLOAD` command to add it to the Startup Suite.
