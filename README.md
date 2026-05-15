# CADMentor

## Intention and Need
Engineering graphics and descriptive geometry are notoriously difficult subjects to master. While there are many online video tutorials and external solvers available, none of them integrate directly into the workspace where the actual drafting happens. 

CADMentor bridges this gap. It acts as an in-editor assistant within AutoCAD itself. It reads your raw problem statement directly from the canvas and generates mathematically perfect, step by step construction geometry right inside your AutoCAD environment. It does not just draw the final answer; it draws the complete construction sequence, including locus lines, projectors, and true length arcs, demonstrating exactly how a student should draft the solution on paper.

## Prerequisites
* Python 3.12 or higher
* .NET 8.0 SDK
* AutoCAD 2021 or newer
* A Google Gemini API key

## Setup Guide

### Part 1: Backend Setup
The geometry engine relies on a local Python server to process the natural language of the question before computing the math.

1. **Open a Command Prompt or Terminal:**
   * On Windows, press the Windows key, type `cmd`, and press Enter.
2. **Navigate to the Backend Folder:**
   * Use the `cd` command to change directories to where you downloaded CADMentor. For example:
     `cd C:\Path\To\CADMentor\backend`
3. **Install the Required Python Packages:**
   * Type the following command and press Enter:
     `pip install -r requirements.txt`
   * Wait for the installation to finish. This downloads the necessary tools for the server to run.
4. **Set Up Your API Key:**
   * In the `backend` folder, you will see a file named `.env.example`.
   * Create a copy of this file and rename the copy to exactly `.env` (make sure there is no `.txt` at the end).
   * Open the new `.env` file using Notepad or any text editor.
   * Go to Google AI Studio (https://aistudio.google.com/), sign in, and create a free Gemini API key.
   * Paste your key into the `.env` file so it looks like this: `GEMINI_API_KEY="your_api_key_here"`
   * Save and close the file.
5. **Start the Server:**
   * Go back to your Command Prompt (which should still be in the `backend` folder).
   * Type the following command and press Enter:
     `python main.py`
   * You should see a message indicating the server has started successfully.

**Important:** Keep this Command Prompt window open and running in the background the entire time you are using the AutoCAD plugin. If you close it, the plugin will not be able to process new questions.

### Part 2: AutoCAD Plugin Setup
1. Open AutoCAD.
2. Type `NETLOAD` in the command line and press Enter.
3. Navigate to the CADMentor plugin folder and select the compiled `CADMentor.dll` file. This is typically located in `plugin/CADMentor/bin/Debug/net8.0-windows/`.

## Usage Instructions
1. Use the `RECTANG` command to draw a boundary box where you want the projection to be generated. Ensure it is reasonably large enough to contain the geometry.
2. Use the `MTEXT` command to type or paste your descriptive geometry question.
3. Select your text.
4. Press `Shift+V` to begin the drafting sequence. Please note that it will take a few seconds initially to read the question, communicate with the local server, and calculate the coordinates.
5. The extension will generate the drawing one mathematical step at a time. This allows you to watch the logic unfold exactly as a human would draft it. Continue pressing `Shift+V` to advance through the steps.
6. Once the final step is drawn, the AutoCAD command line will notify you that the projection is complete.
7. To try a new question, completely `ERASE` the existing geometry from the screen, select your new text, and begin pressing `Shift+V` again.

## Supported Topics
CADMentor currently covers the foundational and intermediate aspects of descriptive geometry with absolute mathematical accuracy:
* Principles of orthographic projection (First-Angle Method)
* Projection of Points in all four quadrants
* Projection of Lines (parallel, inclined to one plane, and the full dual-inclination method for lines inclined to both HP and VP)
* Projection of Planes and Laminas (triangles, squares, pentagons, hexagons) resting on edges or corners, including the rigorous 3-stage change of position method.

## Topics Yet to Conquer
The engine is actively being expanded. The following topics are currently unsupported but planned for future updates:
* Projection of 3D Solids (Prisms, Pyramids, Cylinders, Cones)
* Sections of Solids
* Development of Surfaces
* Isometric Projections

## Troubleshooting API Limits
CADMentor uses the Gemini API exclusively to extract the text parameters (the math engine itself runs entirely offline). If you are using a free tier API key, you may eventually hit a quota limit. 

If the plugin stops responding or shows a `502 Bad Gateway` error in the AutoCAD command line, you have likely exhausted your request quota for the default model.

How to fix quota issues:
1. Open the `backend/main.py` file in a text editor.
2. Locate the `GEMINI_MODEL` variable near the top of the file.
3. Change the model string to another available free tier model. For example, if it is currently set to `"gemini-3.1-flash-lite"`, you can change it to `"gemini-2.0-flash"` or `"gemini-1.5-flash"`.
4. Save the file.
5. Terminate your running Python backend server and run `python main.py` again.

Because Google assigns separate free tier quotas to different models, switching the model name in the code will instantly provide you with a fresh batch of requests to continue working.
