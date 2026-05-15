using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Geometry;
using Autodesk.AutoCAD.Colors;
using CADMentor.Models;

namespace CADMentor
{
    /// <summary>
    /// Creates AutoCAD geometry entities from solution steps.
    /// 
    /// All geometry is drawn at TRUE SCALE (1:1).
    /// NO scaling, NO normalization, NO compression.
    /// 
    /// Only TRANSLATION is applied:
    ///   Backend (0,0) → maps to rectangle center (center_x, center_y)
    ///   x_final = center_x + x
    ///   y_final = center_y + y
    /// 
    /// XY reference line sits at y = center_y.
    /// Front view at 30mm above HP → exactly 30 units above XY line.
    /// Top view at 50mm in front VP → exactly 50 units below XY line.
    /// 
    /// All entities drawn in WHITE.
    /// </summary>
    public static class DrawingExecutor
    {
        // Translation origin — set from boundary center offset by geometry center
        private static double _originX = 0;
        private static double _originY = 0;
        private static WorkBoundary? _boundary;

        /// <summary>
        /// Configures the executor with a detected boundary.
        /// Centers the 1:1 true scale geometry inside the bounding box.
        /// Does NOT scale the geometry, preserving accurate true lengths.
        /// </summary>
        public static void SetBoundary(WorkBoundary boundary, SolutionMap solution)
        {
            _boundary = boundary;

            // Compute bounding box of ALL geometry from step parameters
            double minX = 0, maxX = 0, minY = 0, maxY = 0;
            bool first = true;

            foreach (var step in solution.Steps)
            {
                double[] xs = Array.Empty<double>();
                double[] ys = Array.Empty<double>();

                switch (step.Type.ToLowerInvariant())
                {
                    case "line":
                        if (step.Parameters.TryGetValue("x1", out double x1) &&
                            step.Parameters.TryGetValue("y1", out double y1) &&
                            step.Parameters.TryGetValue("x2", out double x2) &&
                            step.Parameters.TryGetValue("y2", out double y2))
                        {
                            xs = new[] { x1, x2 };
                            ys = new[] { y1, y2 };
                        }
                        break;
                    case "circle":
                    case "point":
                        {
                            double cx = 0, cy = 0, r = 0;
                            step.Parameters.TryGetValue("cx", out cx);
                            step.Parameters.TryGetValue("cy", out cy);
                            step.Parameters.TryGetValue("radius", out r);
                            if (!step.Parameters.ContainsKey("cx"))
                            {
                                step.Parameters.TryGetValue("x", out cx);
                                step.Parameters.TryGetValue("y", out cy);
                            }
                            xs = new[] { cx - r, cx + r };
                            ys = new[] { cy - r, cy + r };
                        }
                        break;
                    case "arc":
                        {
                            step.Parameters.TryGetValue("cx", out double acx);
                            step.Parameters.TryGetValue("cy", out double acy);
                            step.Parameters.TryGetValue("radius", out double ar);
                            xs = new[] { acx - ar, acx + ar };
                            ys = new[] { acy - ar, acy + ar };
                        }
                        break;
                }

                foreach (double x in xs)
                {
                    if (first) { minX = maxX = x; first = false; }
                    if (x < minX) minX = x;
                    if (x > maxX) maxX = x;
                }
                foreach (double y in ys)
                {
                    if (first) { minY = maxY = y; first = false; }
                    if (y < minY) minY = y;
                    if (y > maxY) maxY = y;
                }
            }

            // Center of geometry
            double geoCenterX = (minX + maxX) / 2.0;
            double geoCenterY = (minY + maxY) / 2.0;

            // Offset origin so that the geometry center matches the boundary center
            _originX = boundary.CenterX - geoCenterX;
            _originY = boundary.CenterY - geoCenterY;
        }

        /// <summary>
        /// Translates a backend coordinate to drawing space.
        /// Geometry is centered on the boundary at true scale (1:1).
        /// </summary>
        private static (double x, double y) Translate(double localX, double localY)
        {
            return (_originX + localX, _originY + localY);
        }

        /// <summary>
        /// Returns a color index based on the step's layer.
        /// OBJECT = 7 (white), PROJECTION = 8 (dark gray), CONSTRUCTION = 3 (green).
        /// This makes construction/projection lines visually distinct from object edges.
        /// </summary>
        private static short GetLayerColorIndex(string layer)
        {
            return layer.ToUpperInvariant() switch
            {
                "PROJECTION" => 8,    // dark gray — faint projector lines
                "CONSTRUCTION" => 3,  // green — XY reference line
                _ => 7,              // white — object edges
            };
        }

        /// <summary>
        /// Executes a single construction step.
        /// Coordinates are translated (NOT scaled) to boundary center.
        /// All entities are WHITE.
        /// </summary>
        public static string ExecuteStep(Document doc, Step step)
        {
            Database db = doc.Database;

            using (Transaction tr = db.TransactionManager.StartTransaction())
            {
                try
                {
                    EnsureLayerExists(db, tr, step.Layer);

                    BlockTable bt = (BlockTable)tr.GetObject(
                        db.BlockTableId, OpenMode.ForRead);
                    BlockTableRecord modelSpace = (BlockTableRecord)tr.GetObject(
                        bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite);

                    string debugInfo;
                    switch (step.Type.Trim().ToLowerInvariant())
                    {
                        case "line":
                            debugInfo = DrawLine(step, tr, modelSpace);
                            break;
                        case "point":
                            debugInfo = DrawPointCross(step, tr, modelSpace);
                            break;
                        case "circle":
                            debugInfo = DrawCircleMarker(step, tr, modelSpace);
                            break;
                        case "arc":
                            debugInfo = DrawArc(step, tr, modelSpace);
                            break;
                        default:
                            tr.Commit();
                            return $"Step {step.StepId}: {step.Description} (type '{step.Type}' not supported)";
                    }

                    tr.Commit();
                    return $"Step {step.StepId}: {step.Description} — {debugInfo}";
                }
                catch (Exception ex)
                {
                    tr.Abort();
                    return $"Step {step.StepId}: FAILED — {ex.Message}";
                }
            }
        }

        /// <summary>
        /// Draws a Line at true scale. Only translation applied.
        /// XY line (y1=0, y2=0) will appear at y = center_y.
        /// </summary>
        private static string DrawLine(Step step, Transaction tr, BlockTableRecord modelSpace)
        {
            if (!step.Parameters.TryGetValue("x1", out double x1) ||
                !step.Parameters.TryGetValue("y1", out double y1) ||
                !step.Parameters.TryGetValue("x2", out double x2) ||
                !step.Parameters.TryGetValue("y2", out double y2))
            {
                return "missing parameters";
            }

            // For XY reference line: clamp X to rectangle width
            if (Math.Abs(y1) < 0.001 && Math.Abs(y2) < 0.001 && _boundary != null)
            {
                // XY line spans full rectangle width
                x1 = _boundary.MinX - _originX; // will translate to MinX
                x2 = _boundary.MaxX - _originX; // will translate to MaxX
            }

            var (dx1, dy1) = Translate(x1, y1);
            var (dx2, dy2) = Translate(x2, y2);

            var line = new Line(
                new Point3d(dx1, dy1, 0),
                new Point3d(dx2, dy2, 0)
            );
            line.Layer = step.Layer;
            line.Color = Autodesk.AutoCAD.Colors.Color.FromColorIndex(ColorMethod.ByAci, GetLayerColorIndex(step.Layer));

            modelSpace.AppendEntity(line);
            tr.AddNewlyCreatedDBObject(line, true);

            return $"Line ({dx1:F0},{dy1:F0}) to ({dx2:F0},{dy2:F0})";
        }

        /// <summary>
        /// Draws a visible cross (+) at true-scale position.
        /// </summary>
        private static string DrawPointCross(Step step, Transaction tr, BlockTableRecord modelSpace)
        {
            if (!step.Parameters.TryGetValue("x", out double x) ||
                !step.Parameters.TryGetValue("y", out double y))
            {
                return "missing parameters";
            }

            var (dx, dy) = Translate(x, y);
            double half = 3.0;

            // Horizontal arm
            var hLine = new Line(
                new Point3d(dx - half, dy, 0),
                new Point3d(dx + half, dy, 0)
            );
            hLine.Layer = step.Layer;
            hLine.Color = Autodesk.AutoCAD.Colors.Color.FromColorIndex(ColorMethod.ByAci, 7);
            modelSpace.AppendEntity(hLine);
            tr.AddNewlyCreatedDBObject(hLine, true);

            // Vertical arm
            var vLine = new Line(
                new Point3d(dx, dy - half, 0),
                new Point3d(dx, dy + half, 0)
            );
            vLine.Layer = step.Layer;
            vLine.Color = Autodesk.AutoCAD.Colors.Color.FromColorIndex(ColorMethod.ByAci, 7);
            modelSpace.AppendEntity(vLine);
            tr.AddNewlyCreatedDBObject(vLine, true);

            return $"Point at ({dx:F0},{dy:F0})";
        }

        /// <summary>
        /// Draws a small circle marker at the given point (professional point marker).
        /// Parameters: cx, cy, radius
        /// </summary>
        private static string DrawCircleMarker(Step step, Transaction tr, BlockTableRecord modelSpace)
        {
            if (!step.Parameters.TryGetValue("cx", out double cx) ||
                !step.Parameters.TryGetValue("cy", out double cy) ||
                !step.Parameters.TryGetValue("radius", out double radius))
            {
                return "missing parameters";
            }

            var (dx, dy) = Translate(cx, cy);

            var circle = new Circle(
                new Point3d(dx, dy, 0),
                Vector3d.ZAxis,
                radius
            );
            circle.Layer = step.Layer;
            circle.Color = Autodesk.AutoCAD.Colors.Color.FromColorIndex(ColorMethod.ByAci, GetLayerColorIndex(step.Layer));
            modelSpace.AppendEntity(circle);
            tr.AddNewlyCreatedDBObject(circle, true);

            return $"Circle at ({dx:F0},{dy:F0}) r={radius:F1}";
        }

        /// <summary>
        /// Draws an arc entity for construction geometry (locus arcs, TL arcs).
        /// Parameters: cx, cy, radius, start_angle, end_angle (degrees)
        /// </summary>
        private static string DrawArc(Step step, Transaction tr, BlockTableRecord modelSpace)
        {
            if (!step.Parameters.TryGetValue("cx", out double cx) ||
                !step.Parameters.TryGetValue("cy", out double cy) ||
                !step.Parameters.TryGetValue("radius", out double radius) ||
                !step.Parameters.TryGetValue("start_angle", out double startDeg) ||
                !step.Parameters.TryGetValue("end_angle", out double endDeg))
            {
                return "missing parameters";
            }

            var (dx, dy) = Translate(cx, cy);

            double startRad = startDeg * Math.PI / 180.0;
            double endRad = endDeg * Math.PI / 180.0;

            var arc = new Arc(
                new Point3d(dx, dy, 0),
                radius,
                startRad,
                endRad
            );
            arc.Layer = step.Layer;
            arc.Color = Autodesk.AutoCAD.Colors.Color.FromColorIndex(ColorMethod.ByAci, GetLayerColorIndex(step.Layer));
            modelSpace.AppendEntity(arc);
            tr.AddNewlyCreatedDBObject(arc, true);

            return $"Arc at ({dx:F0},{dy:F0}) r={radius:F1} {startDeg:F0}°→{endDeg:F0}°";
        }

        /// <summary>
        /// Zooms the viewport to show all geometry.
        /// </summary>
        public static void ZoomExtents(Document doc)
        {
            try
            {
                doc.SendStringToExecute("_.ZOOM _E ", true, false, false);
            }
            catch { }
        }

        /// <summary>
        /// Ensures a layer exists. White color.
        /// </summary>
        private static void EnsureLayerExists(Database db, Transaction tr, string layerName)
        {
            LayerTable lt = (LayerTable)tr.GetObject(
                db.LayerTableId, OpenMode.ForRead);

            if (lt.Has(layerName))
                return;

            lt.UpgradeOpen();

            var layerRecord = new LayerTableRecord
            {
                Name = layerName,
                Color = Autodesk.AutoCAD.Colors.Color.FromColorIndex(ColorMethod.ByAci, 7),
            };

            lt.Add(layerRecord);
            tr.AddNewlyCreatedDBObject(layerRecord, true);
        }
    }
}
