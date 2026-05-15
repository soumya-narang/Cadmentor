using System.Text.Json.Serialization;

namespace CADMentor.Models
{
    /// <summary>
    /// Request body sent to the FastAPI backend for question parsing.
    /// </summary>
    public class ParseRequest
    {
        [JsonPropertyName("question")]
        public string Question { get; set; } = string.Empty;
    }
}
