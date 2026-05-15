using System.Diagnostics;
using System.Runtime.InteropServices;
using Autodesk.AutoCAD.ApplicationServices;

namespace CADMentor
{
    /// <summary>
    /// Low-level keyboard hook that intercepts Shift+V globally and triggers
    /// the CADMentor command ONLY when AutoCAD is the foreground window.
    /// 
    /// Uses Win32 SetWindowsHookEx with WH_KEYBOARD_LL to capture keystrokes
    /// before they reach any application. When Shift+V is detected and AutoCAD
    /// is active, the keypress is suppressed (V is not typed) and the internal
    /// command is invoked silently.
    /// 
    /// Thread safety: The hook callback runs on the thread that installed it
    /// (AutoCAD's main UI thread), so SendStringToExecute is safe to call.
    /// </summary>
    public static class HotkeyHook
    {
        // ── Win32 Constants ──
        private const int WH_KEYBOARD_LL = 13;
        private const int WM_KEYDOWN = 0x0100;
        private const int VK_V = 0x56;
        private const int VK_SHIFT = 0x10;

        // ── Win32 Delegates and Imports ──

        private delegate IntPtr LowLevelKeyboardProc(int nCode, IntPtr wParam, IntPtr lParam);

        [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        private static extern IntPtr SetWindowsHookEx(
            int idHook, LowLevelKeyboardProc lpfn, IntPtr hMod, uint dwThreadId);

        [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool UnhookWindowsHookEx(IntPtr hhk);

        [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        private static extern IntPtr CallNextHookEx(
            IntPtr hhk, int nCode, IntPtr wParam, IntPtr lParam);

        [DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        private static extern IntPtr GetModuleHandle(string lpModuleName);

        [DllImport("user32.dll")]
        private static extern IntPtr GetForegroundWindow();

        [DllImport("user32.dll")]
        private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

        [DllImport("user32.dll")]
        private static extern short GetAsyncKeyState(int vKey);

        // ── State ──

        private static IntPtr _hookId = IntPtr.Zero;
        private static LowLevelKeyboardProc? _hookProc;
        private static bool _isExecuting = false;

        /// <summary>
        /// Installs the low-level keyboard hook.
        /// Must be called from AutoCAD's main UI thread (i.e., in Initialize()).
        /// </summary>
        public static void Install()
        {
            if (_hookId != IntPtr.Zero)
                return; // Already installed

            // Store delegate in a field to prevent GC from collecting it
            _hookProc = HookCallback;

            using (Process currentProcess = Process.GetCurrentProcess())
            using (ProcessModule? mainModule = currentProcess.MainModule)
            {
                if (mainModule == null)
                    return;

                _hookId = SetWindowsHookEx(
                    WH_KEYBOARD_LL,
                    _hookProc,
                    GetModuleHandle(mainModule.ModuleName),
                    0);
            }
        }

        /// <summary>
        /// Removes the keyboard hook. Must be called during Terminate().
        /// </summary>
        public static void Uninstall()
        {
            if (_hookId != IntPtr.Zero)
            {
                UnhookWindowsHookEx(_hookId);
                _hookId = IntPtr.Zero;
            }
            _hookProc = null;
        }

        /// <summary>
        /// The hook callback. Called for every keypress system-wide.
        /// We only act on Shift+V when AutoCAD is the foreground window.
        /// </summary>
        private static IntPtr HookCallback(int nCode, IntPtr wParam, IntPtr lParam)
        {
            if (nCode >= 0 && wParam == (IntPtr)WM_KEYDOWN)
            {
                int vkCode = Marshal.ReadInt32(lParam);

                if (vkCode == VK_V && IsShiftDown() && IsAutoCADForeground())
                {
                    // Prevent re-entrancy if a command is already executing
                    if (!_isExecuting)
                    {
                        _isExecuting = true;

                        try
                        {
                            InvokeCommand();
                        }
                        finally
                        {
                            _isExecuting = false;
                        }
                    }

                    // Return non-zero to suppress the V keypress
                    return (IntPtr)1;
                }
            }

            return CallNextHookEx(_hookId, nCode, wParam, lParam);
        }

        /// <summary>
        /// Checks if either Shift key is currently held down.
        /// </summary>
        private static bool IsShiftDown()
        {
            // GetAsyncKeyState returns the key state at the time of the call.
            // High bit set = key is currently down.
            return (GetAsyncKeyState(VK_SHIFT) & 0x8000) != 0;
        }

        /// <summary>
        /// Checks if the foreground window belongs to the current AutoCAD process.
        /// Prevents the hotkey from firing when using other applications.
        /// </summary>
        private static bool IsAutoCADForeground()
        {
            IntPtr foregroundWindow = GetForegroundWindow();
            if (foregroundWindow == IntPtr.Zero)
                return false;

            GetWindowThreadProcessId(foregroundWindow, out uint foregroundProcessId);
            uint currentProcessId = (uint)Process.GetCurrentProcess().Id;

            return foregroundProcessId == currentProcessId;
        }

        /// <summary>
        /// Sends the internal command to AutoCAD for execution.
        /// Uses SendStringToExecute to queue the command — this is thread-safe
        /// because the hook callback runs on the UI thread.
        /// </summary>
        private static void InvokeCommand()
        {
            try
            {
                Document? doc = Autodesk.AutoCAD.ApplicationServices.Core.Application
                    .DocumentManager?.MdiActiveDocument;

                if (doc != null)
                {
                    // The trailing space acts as Enter, executing the command.
                    // The leading underscore ensures it works in localized AutoCAD versions.
                    doc.SendStringToExecute("_CADMENTOR_EXEC ", true, false, false);
                }
            }
            catch
            {
                // Silently ignore — never crash AutoCAD from a keyboard hook
            }
        }
    }
}
