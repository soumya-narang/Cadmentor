using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Geometry;
using CADMentor.Models;

namespace CADMentor
{
    /// <summary>
    /// Detects whether a construction step has already been drawn in the current drawing.
    /// This is the foundation for preventing duplicate geometry when STEP is pressed
    /// multiple times or after reloading a problem.
    /// 
    /// Current implementation: basic line endpoint matching with tolerance.
    /// Future: will integrate with geometry engine for more sophisticated detection.
    /// </summary>
    public static class DuplicateDetector
    {
        /// <summary>
        /// Tolerance for comparing point coordinates (in drawing units).
        /// AutoCAD's default tolerance is 1e-6, but we use a slightly
        /// larger value to account for floating-point rounding from JSON.
        /// </summary>
        private const double Tolerance = 0.01;

        /// <summary>
        /// Checks if the geometry described by a step already exists in ModelSpace.
        /// </summary>
        /// <param name="doc">The active AutoCAD document.</param>
        /// <param name="step">The step to check.</param>
        /// <returns>True if equivalent geometry already exists.</returns>
        public static bool IsStepAlreadyDrawn(Document doc, Step step)
        {
            if (step.Type != "line")
            {
                // Only line detection implemented for now.
                // Future types (point, arc, circle) will be added
                // as the geometry engine is built out.
                return false;
            }

            // Extract expected coordinates from step parameters
            if (!step.Parameters.TryGetValue("x1", out double x1) ||
                !step.Parameters.TryGetValue("y1", out double y1) ||
                !step.Parameters.TryGetValue("x2", out double x2) ||
                !step.Parameters.TryGetValue("y2", out double y2))
            {
                return false;
            }

            var expectedStart = new Point3d(x1, y1, 0);
            var expectedEnd = new Point3d(x2, y2, 0);
            Database db = doc.Database;

            using (Transaction tr = db.TransactionManager.StartTransaction())
            {
                BlockTable bt = (BlockTable)tr.GetObject(
                    db.BlockTableId, OpenMode.ForRead);
                BlockTableRecord modelSpace = (BlockTableRecord)tr.GetObject(
                    bt[BlockTableRecord.ModelSpace], OpenMode.ForRead);

                foreach (ObjectId objId in modelSpace)
                {
                    Entity ent = (Entity)tr.GetObject(objId, OpenMode.ForRead);

                    if (ent is Line line)
                    {
                        // Check both forward and reverse direction matches
                        bool forwardMatch =
                            line.StartPoint.DistanceTo(expectedStart) < Tolerance &&
                            line.EndPoint.DistanceTo(expectedEnd) < Tolerance;

                        bool reverseMatch =
                            line.StartPoint.DistanceTo(expectedEnd) < Tolerance &&
                            line.EndPoint.DistanceTo(expectedStart) < Tolerance;

                        if (forwardMatch || reverseMatch)
                        {
                            tr.Commit();
                            return true;
                        }
                    }
                }

                tr.Commit();
            }

            return false;
        }
    }
}
