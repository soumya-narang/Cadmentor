using Autodesk.AutoCAD.ApplicationServices;
using CADMentor.Models;

namespace CADMentor
{
    /// <summary>
    /// Unified state machine that drives the entire CADMentor workflow.
    /// 
    /// State transitions (all triggered by the same Shift+V hotkey):
    /// 
    ///   IDLE ──[Shift+V]──► LOADED ──[Shift+V]──► STEPPING ──► ... ──► DONE ──[Shift+V]──► IDLE
    ///   
    /// Supports MULTIPLE consecutive problems without restarting AutoCAD.
    /// Every HandleIdle call force-clears all previous state.
    /// </summary>
    public static class StepEngine
    {
        public enum EngineState
        {
            Idle,
            Loaded,
            Stepping,
            Done
        }

        // ── Current state ──
        private static EngineState _state = EngineState.Idle;
        private static SolutionMap? _activeProblem;
        private static int _currentStepIndex;
        private static WorkBoundary? _activeBoundary;

        public static EngineState CurrentState => _state;

        /// <summary>
        /// Advances the engine by one step. Called on every Shift+V press.
        /// </summary>
        public static string Advance(Document doc)
        {
            switch (_state)
            {
                case EngineState.Idle:
                    return HandleIdle(doc);

                case EngineState.Loaded:
                    _state = EngineState.Stepping;
                    return HandleStep(doc);

                case EngineState.Stepping:
                    return HandleStep(doc);

                case EngineState.Done:
                    return HandleReset();

                default:
                    return "CADMentor: Unknown state";
            }
        }

        /// <summary>
        /// IDLE → LOADED: Force-clear old state, detect boundary, extract text,
        /// call backend, store NEW problem.
        /// </summary>
        private static string HandleIdle(Document doc)
        {
            // ── FORCE CLEAR all previous state ──
            _activeProblem = null;
            _activeBoundary = null;
            _currentStepIndex = 0;

            // 1. Detect boundary rectangle
            _activeBoundary = BoundaryDetector.DetectBoundary(doc);

            if (_activeBoundary == null)
            {
                return "CADMentor: Please draw a boundary rectangle first. " +
                       "Use RECTANG command to draw a rectangle, then press Shift+V again.";
            }

            // 2. Extract all text from the drawing
            string questionText = TextExtractor.ExtractAllText(doc);

            if (string.IsNullOrWhiteSpace(questionText))
            {
                return "CADMentor: No text found in drawing. Type your question first.";
            }

            // 3. Send to backend
            var solutionMap = BackendClient.ParseQuestion(questionText, out string errorMessage);

            if (solutionMap == null)
            {
                return $"CADMentor: Backend error — {errorMessage}";
            }

            // 4. Store the NEW problem — always overwrites any previous
            _activeProblem = solutionMap;
            _currentStepIndex = 0;

            // 5. Check if steps were generated
            int stepCount = _activeProblem.Steps.Count;

            if (stepCount > 0)
            {
                // Configure drawing executor with boundary
                DrawingExecutor.SetBoundary(_activeBoundary, _activeProblem);

                _state = EngineState.Loaded;

                string status = $"CADMentor: Boundary detected {_activeBoundary}";
                status += $"\nCADMentor: Steps loaded: {stepCount}";

                if (_activeProblem.Points?.FrontView != null && _activeProblem.Points?.TopView != null)
                {
                    var fv = _activeProblem.Points.FrontView;
                    var tv = _activeProblem.Points.TopView;
                    status += $" | FV=({fv.X},{fv.Y}), TV=({tv.X},{tv.Y})";
                }

                status += "\nCADMentor: Press Shift+V to draw step 1.";
                return status;
            }
            else if (_activeProblem.Parsed != null)
            {
                _state = EngineState.Done;
                return $"CADMentor: No steps generated for this problem (shape={_activeProblem.Parsed.Shape}). " +
                       "Geometry engine may not support this shape yet. Press again to reset.";
            }
            else
            {
                _state = EngineState.Done;
                return "CADMentor: No steps generated for this problem. Press again to reset.";
            }
        }

        /// <summary>
        /// STEPPING: Execute the next step from the CURRENT _activeProblem.
        /// Every step always executes — no skip logic.
        /// </summary>
        private static string HandleStep(Document doc)
        {
            // Guard: ensure we have a valid, current problem
            if (_activeProblem == null)
            {
                _state = EngineState.Idle;
                return "CADMentor: No problem loaded. Press Shift+V to start.";
            }

            if (_activeProblem.Steps.Count == 0)
            {
                _state = EngineState.Idle;
                return "CADMentor: No steps in current problem. Press Shift+V to reload.";
            }

            if (_currentStepIndex >= _activeProblem.Steps.Count)
            {
                _state = EngineState.Done;
                return "CADMentor: All steps completed. Press Shift+V to reset.";
            }

            // Execute step from the LATEST _activeProblem
            Step currentStep = _activeProblem.Steps[_currentStepIndex];
            string result = DrawingExecutor.ExecuteStep(doc, currentStep);
            string message = $"CADMentor: [{currentStep.StepId}/{_activeProblem.Steps.Count}] {result}";

            _currentStepIndex++;

            if (_currentStepIndex >= _activeProblem.Steps.Count)
            {
                _state = EngineState.Done;
                message += "\nCADMentor: All steps completed. Press Shift+V to reset.";
            }

            return message;
        }

        /// <summary>
        /// DONE → IDLE: Clear everything for next problem.
        /// </summary>
        private static string HandleReset()
        {
            _activeProblem = null;
            _activeBoundary = null;
            _currentStepIndex = 0;
            _state = EngineState.Idle;

            return "CADMentor: Reset complete. Erase old geometry, type new question, press Shift+V.";
        }

        /// <summary>
        /// Force-reset from any state.
        /// </summary>
        public static void ForceReset()
        {
            _activeProblem = null;
            _activeBoundary = null;
            _currentStepIndex = 0;
            _state = EngineState.Idle;
        }
    }
}
