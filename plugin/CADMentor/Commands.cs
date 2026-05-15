using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;

namespace CADMentor
{
    /// <summary>
    /// Defines the internal AutoCAD command that the keyboard hook invokes.
    /// This command is never typed by the user — it is triggered silently
    /// by the Shift+V hotkey via SendStringToExecute.
    /// 
    /// The command name starts with underscore to work in localized
    /// AutoCAD versions (non-English).
    /// </summary>
    public class Commands
    {
        /// <summary>
        /// The unified command that drives the state machine.
        /// Each invocation advances the engine by one state/step.
        /// 
        /// CommandFlags.NoHistory: prevents the command from appearing in
        /// the command history (Esc recall list).
        /// </summary>
        [CommandMethod("_CADMENTOR_EXEC", CommandFlags.NoHistory)]
        public void Execute()
        {
            Document? doc = Autodesk.AutoCAD.ApplicationServices.Core.Application
                .DocumentManager?.MdiActiveDocument;

            if (doc == null)
                return;

            Editor ed = doc.Editor;

            try
            {
                string result = StepEngine.Advance(doc);
                ed.WriteMessage($"\n{result}\n");

                // Zoom to extents after drawing so geometry is visible
                DrawingExecutor.ZoomExtents(doc);
            }
            catch (System.Exception ex)
            {
                ed.WriteMessage($"\nCADMentor: Error — {ex.Message}\n");
            }
        }
    }
}
