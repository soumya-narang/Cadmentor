using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;

// Register this class as the extension application entry point
[assembly: ExtensionApplication(typeof(CADMentor.Plugin))]
[assembly: CommandClass(typeof(CADMentor.Commands))]

namespace CADMentor
{
    /// <summary>
    /// Plugin entry point. Implements IExtensionApplication for AutoCAD
    /// lifecycle integration. Installs the keyboard hook on load and
    /// cleans up on termination.
    /// 
    /// The plugin is completely invisible — no ribbon, no toolbar, no palette.
    /// Only the command line receives status messages.
    /// </summary>
    public class Plugin : IExtensionApplication
    {
        /// <summary>
        /// Called when AutoCAD loads the plugin (via NETLOAD or auto-load).
        /// </summary>
        public void Initialize()
        {
            try
            {
                // Install the Shift+V keyboard hook
                HotkeyHook.Install();

                // Minimal confirmation in command line only
                Document? doc = Autodesk.AutoCAD.ApplicationServices.Core.Application
                    .DocumentManager?.MdiActiveDocument;
                doc?.Editor.WriteMessage("\nCADMentor: Ready. Use Shift+V.\n");
            }
            catch (System.Exception ex)
            {
                // Log but never crash AutoCAD
                try
                {
                    Document? doc = Autodesk.AutoCAD.ApplicationServices.Core.Application
                        .DocumentManager?.MdiActiveDocument;
                    doc?.Editor.WriteMessage($"\nCADMentor: Init failed — {ex.Message}\n");
                }
                catch { /* Absolute last resort — silently fail */ }
            }
        }

        /// <summary>
        /// Called when AutoCAD shuts down.
        /// </summary>
        public void Terminate()
        {
            try
            {
                HotkeyHook.Uninstall();
                BackendClient.Dispose();
                StepEngine.ForceReset();
            }
            catch { /* Never crash AutoCAD during shutdown */ }
        }
    }
}
