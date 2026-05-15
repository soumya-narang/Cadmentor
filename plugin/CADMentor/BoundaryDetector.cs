using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Geometry;

namespace CADMentor
{
    /// <summary>
    /// Represents the user-drawn rectangular working boundary.
    /// All geometry will be drawn inside this rectangle.
    /// </summary>
    public class WorkBoundary
    {
        public double MinX { get; set; }
        public double MaxX { get; set; }
        public double MinY { get; set; }
        public double MaxY { get; set; }

        /// <summary>Center X of the rectangle — used as working origin.</summary>
        public double CenterX => (MinX + MaxX) / 2.0;

        /// <summary>Center Y of the rectangle — XY reference line goes here.</summary>
        public double CenterY => (MinY + MaxY) / 2.0;

        /// <summary>Full width of the rectangle.</summary>
        public double Width => MaxX - MinX;

        /// <summary>Full height of the rectangle.</summary>
        public double Height => MaxY - MinY;

        /// <summary>Usable width after 10% margin on each side.</summary>
        public double UsableWidth => Width * 0.80;

        /// <summary>Usable height after 10% margin on each side.</summary>
        public double UsableHeight => Height * 0.80;

        public override string ToString()
            => $"Boundary({MinX:F0},{MinY:F0})-({MaxX:F0},{MaxY:F0}) center=({CenterX:F0},{CenterY:F0})";
    }

    /// <summary>
    /// Scans ModelSpace for a user-drawn rectangle (Polyline with 4 vertices)
    /// and extracts its bounds as the working area.
    /// </summary>
    public static class BoundaryDetector
    {
        /// <summary>
        /// Finds the first rectangular polyline in ModelSpace.
        /// A rectangle is defined as a closed Polyline with exactly 4 vertices.
        /// 
        /// Returns null if no rectangle is found.
        /// </summary>
        public static WorkBoundary? DetectBoundary(Document doc)
        {
            Database db = doc.Database;

            using (Transaction tr = db.TransactionManager.StartTransaction())
            {
                BlockTable bt = (BlockTable)tr.GetObject(
                    db.BlockTableId, OpenMode.ForRead);
                BlockTableRecord modelSpace = (BlockTableRecord)tr.GetObject(
                    bt[BlockTableRecord.ModelSpace], OpenMode.ForRead);

                WorkBoundary? bestBoundary = null;
                double bestArea = 0;

                foreach (ObjectId id in modelSpace)
                {
                    Entity ent = (Entity)tr.GetObject(id, OpenMode.ForRead);

                    if (ent is Polyline pline)
                    {
                        var boundary = TryExtractRectangle(pline);
                        if (boundary != null)
                        {
                            // Pick the largest rectangle if multiple exist
                            double area = boundary.Width * boundary.Height;
                            if (area > bestArea)
                            {
                                bestArea = area;
                                bestBoundary = boundary;
                            }
                        }
                    }
                }

                tr.Commit();
                return bestBoundary;
            }
        }

        /// <summary>
        /// Checks if a Polyline is a rectangle (4 vertices, closed or nearly closed).
        /// Returns a WorkBoundary if valid, null otherwise.
        /// </summary>
        private static WorkBoundary? TryExtractRectangle(Polyline pline)
        {
            int numVerts = pline.NumberOfVertices;

            // Accept 4 vertices (closed) or 5 vertices (last = first, closed loop)
            if (numVerts < 4 || numVerts > 5)
                return null;

            // If 5 vertices, the 5th must be close to the 1st (closed manually)
            // If 4 vertices, the polyline should be flagged as closed
            if (numVerts == 4 && !pline.Closed)
                return null;

            if (numVerts == 5)
            {
                Point2d first = pline.GetPoint2dAt(0);
                Point2d last = pline.GetPoint2dAt(4);
                if (first.GetDistanceTo(last) > 1.0) // tolerance
                    return null;
            }

            // Extract the 4 corner points
            double minX = double.MaxValue, maxX = double.MinValue;
            double minY = double.MaxValue, maxY = double.MinValue;

            for (int i = 0; i < 4; i++)
            {
                Point2d pt = pline.GetPoint2dAt(i);
                if (pt.X < minX) minX = pt.X;
                if (pt.X > maxX) maxX = pt.X;
                if (pt.Y < minY) minY = pt.Y;
                if (pt.Y > maxY) maxY = pt.Y;
            }

            // Validate it's a reasonable size (not a tiny shape)
            double width = maxX - minX;
            double height = maxY - minY;
            if (width < 50 || height < 50)
                return null;

            // Verify it's actually rectangular (all vertices on the bounding box edges)
            for (int i = 0; i < 4; i++)
            {
                Point2d pt = pline.GetPoint2dAt(i);
                bool onXEdge = (System.Math.Abs(pt.X - minX) < 1.0) || (System.Math.Abs(pt.X - maxX) < 1.0);
                bool onYEdge = (System.Math.Abs(pt.Y - minY) < 1.0) || (System.Math.Abs(pt.Y - maxY) < 1.0);
                if (!onXEdge || !onYEdge)
                    return null; // Not a proper rectangle
            }

            return new WorkBoundary
            {
                MinX = minX,
                MaxX = maxX,
                MinY = minY,
                MaxY = maxY,
            };
        }
    }
}
