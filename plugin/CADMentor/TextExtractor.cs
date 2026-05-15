using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;

namespace CADMentor
{
    /// <summary>
    /// Extracts all user-typed text from the current drawing's ModelSpace.
    /// Handles both DBText (single-line TEXT command) and MText (multiline MTEXT command).
    /// </summary>
    public static class TextExtractor
    {
        /// <summary>
        /// Scans ModelSpace for all DBText and MText entities
        /// and returns their combined text content.
        /// </summary>
        /// <param name="doc">The active AutoCAD document.</param>
        /// <returns>
        /// Combined text from all text entities, separated by newlines.
        /// Returns empty string if no text entities found.
        /// </returns>
        public static string ExtractAllText(Document doc)
        {
            var textParts = new List<string>();
            Database db = doc.Database;

            using (Transaction tr = db.TransactionManager.StartTransaction())
            {
                // Open ModelSpace block table record for read
                BlockTable bt = (BlockTable)tr.GetObject(
                    db.BlockTableId, OpenMode.ForRead);
                BlockTableRecord modelSpace = (BlockTableRecord)tr.GetObject(
                    bt[BlockTableRecord.ModelSpace], OpenMode.ForRead);

                // Iterate all entities in ModelSpace
                foreach (ObjectId objId in modelSpace)
                {
                    Entity ent = (Entity)tr.GetObject(objId, OpenMode.ForRead);

                    if (ent is DBText dbText)
                    {
                        string text = dbText.TextString?.Trim() ?? string.Empty;
                        if (!string.IsNullOrEmpty(text))
                        {
                            textParts.Add(text);
                        }
                    }
                    else if (ent is MText mText)
                    {
                        // MText.Contents may include formatting codes;
                        // MText.Text returns the plain-text version.
                        string text = mText.Text?.Trim() ?? string.Empty;
                        if (!string.IsNullOrEmpty(text))
                        {
                            textParts.Add(text);
                        }
                    }
                }

                // Read-only transaction — no commit needed, but calling
                // Commit() is harmless and follows best practice.
                tr.Commit();
            }

            return string.Join("\n", textParts);
        }
    }
}
