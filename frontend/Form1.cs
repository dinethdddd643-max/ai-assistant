using Newtonsoft.Json;
using System;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Windows.Forms;

namespace AIAssistant
{
    public partial class Form1 : Form
    {
        private static readonly HttpClient _client = new HttpClient();
        private const string BASE_URL = "http://localhost:5000";

        public Form1()
        {
            InitializeComponent();
            this.AcceptButton = btnSend;
            this.Text = "AI Assistant Chat";
        }

        // ── Send message ───────────────────────────────────────────────────────
        private async void btnSend_Click(object sender, EventArgs e)
        {
            string userInput = txtInput.Text.Trim();
            if (string.IsNullOrEmpty(userInput)) return;

            try
            {
                btnSend.Enabled = false;
                txtInput.Text   = "";

                var payload = new { message = userInput };
                var content = new StringContent(
                    JsonConvert.SerializeObject(payload),
                    Encoding.UTF8, "application/json");

                var request = new HttpRequestMessage(HttpMethod.Post, $"{BASE_URL}/chat")
                {
                    Content = content
                };

                var response = await _client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead);

                using var stream = await response.Content.ReadAsStreamAsync();
                using var reader = new StreamReader(stream);

                AppendChat($"You: {userInput}", System.Drawing.Color.CornflowerBlue);
                AppendChat("Bot: ", System.Drawing.Color.LightGreen, newline: false);

                char[] buffer = new char[1];
                while (await reader.ReadAsync(buffer, 0, 1) > 0)
                {
                    rtbChat.AppendText(new string(buffer));
                    rtbChat.ScrollToCaret();
                }
                rtbChat.AppendText(Environment.NewLine);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Connection error: {ex.Message}\n\nMake sure the AI Assistant server is running.",
                                "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            finally
            {
                btnSend.Enabled = true;
                txtInput.Focus();
            }
        }

        // ── Clear history ──────────────────────────────────────────────────────
        private async void btnClear_Click(object sender, EventArgs e)
        {
            if (MessageBox.Show("Clear all chat history?", "Confirm",
                MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes) return;

            await _client.PostAsync($"{BASE_URL}/history/clear", null);
            rtbChat.Clear();
        }

        // ── Helper ─────────────────────────────────────────────────────────────
        private void AppendChat(string text, System.Drawing.Color color, bool newline = true)
        {
            rtbChat.SelectionStart  = rtbChat.TextLength;
            rtbChat.SelectionLength = 0;
            rtbChat.SelectionColor  = color;
            rtbChat.AppendText(newline ? text + Environment.NewLine : text);
            rtbChat.SelectionColor  = rtbChat.ForeColor;
            rtbChat.ScrollToCaret();
        }
    }
}
