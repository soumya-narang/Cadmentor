using System.Text.Json.Serialization;

namespace CADMentor.Models
{
    /// <summary>
    /// Represents the complete response from the backend.
    /// Contains the Gemini-extracted entity data and an ordered list of
    /// construction steps to be executed sequentially.
    /// </summary>
    public class SolutionMap
    {
        [JsonPropertyName("parsed")]
        public ParsedEntity? Parsed { get; set; }

        [JsonPropertyName("points")]
        public PointsData? Points { get; set; }

        [JsonPropertyName("steps")]
        public List<Step> Steps { get; set; } = new();
    }

    /// <summary>
    /// Computed 2D projection coordinates for a point.
    /// Only present when shape is "point".
    /// </summary>
    public class PointsData
    {
        [JsonPropertyName("front_view")]
        public PointCoord? FrontView { get; set; }

        [JsonPropertyName("top_view")]
        public PointCoord? TopView { get; set; }
    }

    /// <summary>
    /// A single 2D coordinate.
    /// </summary>
    public class PointCoord
    {
        [JsonPropertyName("x")]
        public double X { get; set; }

        [JsonPropertyName("y")]
        public double Y { get; set; }
    }

    /// <summary>
    /// Structured data extracted from the problem statement by Gemini.
    /// This is pure NLP extraction — no geometry computation.
    /// </summary>
    public class ParsedEntity
    {
        [JsonPropertyName("shape")]
        public string Shape { get; set; } = string.Empty;

        [JsonPropertyName("dimensions")]
        public Dictionary<string, object>? Dimensions { get; set; } = new();

        [JsonPropertyName("position")]
        public PositionData? Position { get; set; }

        [JsonPropertyName("inclination")]
        public InclinationData? Inclination { get; set; }

        [JsonPropertyName("extra")]
        public Dictionary<string, object>? Extra { get; set; } = new();
    }

    /// <summary>
    /// Position of the entity relative to HP (Horizontal Plane)
    /// and VP (Vertical Plane).
    /// </summary>
    public class PositionData
    {
        [JsonPropertyName("above_hp")]
        public double? AboveHp { get; set; }

        [JsonPropertyName("below_hp")]
        public double? BelowHp { get; set; }

        [JsonPropertyName("infront_vp")]
        public double? InfrontVp { get; set; }

        [JsonPropertyName("behind_vp")]
        public double? BehindVp { get; set; }

        [JsonPropertyName("on_hp")]
        public bool OnHp { get; set; }

        [JsonPropertyName("on_vp")]
        public bool OnVp { get; set; }
    }

    /// <summary>
    /// Inclination angles of the entity relative to reference planes.
    /// </summary>
    public class InclinationData
    {
        [JsonPropertyName("angle_to_hp")]
        public double? AngleToHp { get; set; }

        [JsonPropertyName("angle_to_vp")]
        public double? AngleToVp { get; set; }

        [JsonPropertyName("angle_to_xy")]
        public double? AngleToXy { get; set; }

        [JsonPropertyName("resting_element")]
        public string? RestingElement { get; set; }
    }

    /// <summary>
    /// Represents a single construction step in the solution.
    /// Each step corresponds to one geometric entity or operation.
    /// 
    /// Supported types (current and future):
    ///   - "line"       : straight line between two points
    ///   - "point"      : a single point marker
    ///   - "arc"        : circular arc
    ///   - "circle"     : full circle
    ///   - "projection" : projection line connecting views
    ///   
    /// Parameters are stored as flexible key-value pairs to accommodate
    /// different geometry types without requiring type-specific classes:
    ///   - line:   x1, y1, x2, y2
    ///   - point:  x, y
    ///   - arc:    cx, cy, radius, startAngle, endAngle
    ///   - circle: cx, cy, radius
    /// </summary>
    public class Step
    {
        [JsonPropertyName("step_id")]
        public int StepId { get; set; }

        [JsonPropertyName("type")]
        public string Type { get; set; } = string.Empty;

        [JsonPropertyName("parameters")]
        public Dictionary<string, double> Parameters { get; set; } = new();

        [JsonPropertyName("layer")]
        public string Layer { get; set; } = string.Empty;

        [JsonPropertyName("description")]
        public string Description { get; set; } = string.Empty;
    }
}
