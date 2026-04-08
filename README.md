# 🤖 AI Assistant — Local Roleplay Chatbot

A fully offline AI assistant running on your PC, powered by local GGUF models, a Flask API backend, and a Windows Forms frontend.

---

## 📦 What's Included

| File | Description |
|------|-------------|
| `backend/server.py` | Flask API server (SQLite database) |
| `scripts/model_downloader.py` | GUI to download and configure AI models |
| `models_list/models.json` | List of downloadable GGUF models |
| `installer/installer.nsi` | NSIS Windows installer script |
| `frontend/Form1.cs` | C# WinForms chat client |

---

## 🚀 Quick Start (End User)

1. **Run** `AIAssistant_Setup.exe`
2. Follow the installer wizard — check the options you want
3. The **Model Downloader** will open automatically after install
4. Pick a model that fits your PC (see recommendations below)
5. Configure your GPU/CPU settings
6. Click **Download & Configure**
7. Launch **AI Assistant** from your desktop shortcut
8. Open and run the WinForms chat app

---

## 🖥️ System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows 10 64-bit | Windows 11 |
| RAM | 6 GB | 16 GB+ |
| Storage | 5 GB free | 15 GB+ free |
| Python | 3.10+ | 3.11 |
| GPU (optional) | Vulkan/CUDA capable | 8 GB VRAM |

---

## 🧠 Model Recommendations

| Model | Size | RAM | Best For |
|-------|------|-----|----------|
| Phi-3 Mini (Q4) | 2.2 GB | 4 GB | Low-spec PCs, fast responses |
| Mistral 7B (Q4) | 4.1 GB | 6 GB | General chat, balanced |
| **MythoMax 13B (Q4)** | **7.9 GB** | **10 GB** | **Roleplay (recommended)** |
| MythoMax 13B (Q5) | 9.2 GB | 14 GB | High-quality roleplay |
| Llama 3 8B (Q4) | 4.9 GB | 8 GB | General purpose |

---

## ⚙️ GPU Configuration

### Vulkan (AMD / Intel / NVIDIA)
Set **Backend = VULKAN** in the Model Downloader.  
GPU Layers: Start with `8`, increase if you have more VRAM.

```
VRAM 4 GB  → ~8–12 layers
VRAM 6 GB  → ~16–20 layers
VRAM 8 GB  → ~24–32 layers
VRAM 12 GB+ → 35+ layers (full GPU offload)
```

### CUDA (NVIDIA only — faster than Vulkan)
Set **Backend = CUDA**. Reinstall llama-cpp-python with CUDA support:
```bash
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
```

### CPU Only (no GPU)
Set **GPU Layers = 0** and **Backend = CPU**.  
Slower but works on any PC. Use a small model (Phi-3 or Mistral 7B).

---

## 🗄️ Database (SQLite)

The app uses **SQLite** — no SQL Server or SSMS required. The database file is:
```
C:\Program Files\AIAssistant\assistant.db
```

### Tables

| Table | Purpose |
|-------|---------|
| `personality` | Character description, tone, style |
| `chat_history` | All past conversations |
| `rules` | Roleplay rules for the AI |
| `main_memory` | Long-term facts the AI remembers |

You can edit the database with any free tool like [DB Browser for SQLite](https://sqlitebrowser.org/).

---

## 🌐 Hosting on Your Website

If you want users to download and install via your website:

1. **Build the installer** (see Developer section below)
2. **Upload** `AIAssistant_Setup.exe` to your web server or GitHub Releases
3. **Link** to it from your website:
```html
<a href="https://yoursite.com/downloads/AIAssistant_Setup.exe">
  Download AI Assistant
</a>
```
4. Optionally host `models.json` on your server/GitHub so the model list can be updated without reinstalling.

> ⚠️ Note: Windows Defender SmartScreen will warn about unsigned installers. To remove this warning you need a **code signing certificate** (~$200/year from DigiCert, Sectigo, etc.) or upload to GitHub Releases which builds trust over time.

---

## 🔧 Developer Setup

### Prerequisites
```bash
pip install flask llama-cpp-python
# For NSIS installer build:
# Download NSIS from https://nsis.sourceforge.io/
```

### Run the server manually
```bash
cd backend
python server.py
```

### Build the installer
1. Install [NSIS](https://nsis.sourceforge.io/Download)
2. Place your app files in the correct directories (see project structure above)
3. Run:
```bash
makensis installer\installer.nsi
```
This produces `AIAssistant_Setup.exe`.

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Send a message, stream response |
| `/personality` | GET/POST | View/update character |
| `/rules` | GET/POST/DELETE | Manage roleplay rules |
| `/memory` | GET/POST/DELETE | Manage long-term memory |
| `/history/clear` | POST | Clear chat history |

---

## 📁 Project Structure

```
AIAssistant/
├── backend/
│   └── server.py            ← Flask API (SQLite)
├── scripts/
│   └── model_downloader.py  ← GUI model downloader
├── models_list/
│   └── models.json          ← Model catalog
├── models/                  ← Downloaded .gguf files go here
├── installer/
│   └── installer.nsi        ← NSIS installer script
├── frontend/
│   └── Form1.cs             ← C# WinForms chat UI
├── assistant.db             ← SQLite database (created on first run)
└── launch_config.txt        ← Written by model downloader
```

---

## ❓ Troubleshooting

**Server won't start / no model found**  
→ Run the Model Downloader from your desktop shortcut and download a model.

**Very slow responses**  
→ Use a smaller model (Mistral 7B or Phi-3). Set GPU layers > 0 if you have a GPU.

**GPU not detected**  
→ Make sure your GPU drivers are up to date. For Vulkan, install the Vulkan Runtime from [LunarG](https://vulkan.lunarg.com/).

**`llama_cpp` import error**  
→ Reinstall: `pip install llama-cpp-python --force-reinstall`

**Database errors**  
→ Delete `assistant.db` and restart — it will be recreated automatically.

---

## 📄 License

MIT License — free to use, modify, and distribute.
