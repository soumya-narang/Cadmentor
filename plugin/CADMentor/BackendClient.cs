using System.Net.Http.Json;
using System.Text.Json;
using CADMentor.Models;

namespace CADMentor
{
    /// <summary>
    /// HTTP client for communicating with the local FastAPI backend.
    /// Uses a singleton HttpClient to avoid socket exhaustion.
    /// </summary>
    public static class BackendClient
    {
        private static readonly HttpClient _client = new()
        {
            BaseAddress = new Uri("http://localhost:8000"),
            Timeout = TimeSpan.FromSeconds(10)
        };

        private static readonly JsonSerializerOptions _jsonOptions = new()
        {
            PropertyNameCaseInsensitive = true
        };

        /// <summary>
        /// Sends the extracted question text to the backend for parsing.
        /// </summary>
        /// <param name="question">The combined question text from the drawing.</param>
        /// <returns>
        /// A SolutionMap on success, or null if the request fails.
        /// Error details are returned via the errorMessage out parameter.
        /// </returns>
        public static SolutionMap? ParseQuestion(string question, out string errorMessage)
        {
            errorMessage = string.Empty;

            try
            {
                var request = new ParseRequest { Question = question };

                // Use synchronous send to avoid async complications
                // within AutoCAD's command context.
                var response = _client.PostAsJsonAsync("/parse", request)
                    .GetAwaiter().GetResult();

                if (!response.IsSuccessStatusCode)
                {
                    errorMessage = $"Backend returned status {(int)response.StatusCode}";
                    return null;
                }

                string json = response.Content.ReadAsStringAsync()
                    .GetAwaiter().GetResult();

                var solutionMap = JsonSerializer.Deserialize<SolutionMap>(json, _jsonOptions);

                if (solutionMap == null || solutionMap.Steps == null || solutionMap.Steps.Count == 0)
                {
                    errorMessage = "Backend returned empty or invalid solution";
                    return null;
                }

                return solutionMap;
            }
            catch (HttpRequestException)
            {
                errorMessage = "Unable to reach backend. Is the server running?";
                return null;
            }
            catch (TaskCanceledException)
            {
                errorMessage = "Backend request timed out";
                return null;
            }
            catch (JsonException)
            {
                errorMessage = "Invalid response from backend";
                return null;
            }
            catch (Exception ex)
            {
                errorMessage = $"Unexpected error: {ex.Message}";
                return null;
            }
        }

        /// <summary>
        /// Disposes the HttpClient. Called during plugin termination.
        /// </summary>
        public static void Dispose()
        {
            _client.Dispose();
        }
    }
}
