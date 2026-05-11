# CADMentor

A native AutoCAD plugin that lets you solve descriptive geometry problems directly inside AutoCAD — no switching windows, no copy-pasting, no interruptions.

## The problem it solves

Descriptive geometry in AutoCAD is tedious. You look up a problem, mentally translate it into drawing steps, switch back to AutoCAD, and hope you remembered everything correctly. There's no tool that bridges the gap between understanding a problem and drawing it — until now.

## How it works

1. Draw a box anywhere on the AutoCAD canvas
2. Press `Ctrl+W` — the command line confirms: *"Space loaded successfully"*
3. Type your descriptive geometry question inside the box
4. Press `Ctrl+W` again — CADMentor reads the question
5. Press `Ctrl+W` once more — it draws each step of the solution sequentially on the canvas
6. After the final step, the workspace resets automatically

Two keystrokes to load. Two keystrokes to solve. Zero context switching.

## Design principles

- **Stealth integration** — feels like a native AutoCAD feature, not a plugin
- **Dimensional accuracy** — all drawn geometry is precise, not illustrative
- **Human-like drawing aesthetic** — output matches how a drafter would draw it, not how a script would
- **Minimal interaction** — the entire flow is `Ctrl+W` only

## Tech stack

- C# / .NET (AutoCAD .NET API)
- AutoCAD ObjectARX
- NLP layer for geometry problem interpretation

## Status

In active development. Core interaction loop complete. Problem parsing and step-by-step drawing pipeline in progress.

## Scope

Currently targeting standard descriptive geometry problems:
- Projection of points, lines, and planes
- Projection of solids (prisms, pyramids, cylinders, cones)
- Section planes and true shapes
- Isometric views
