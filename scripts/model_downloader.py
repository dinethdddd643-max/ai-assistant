#!/usr/bin/env python3
"""
AI Assistant — Model Downloader
Runs after installation to let users pick and download a model.
"""
import os
import sys
import json
import urllib.request
import tkinter as tk
from tkinter import ttk, messagebox

# ── Paths ─────────────────────────────────────────────────────────────────────
INSTALL_DIR   = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR    = os.path.join(INSTALL_DIR, "models")
MODELS_JSON   = os.path.join(INSTALL_DIR, "models_list", "models.json")
CONFIG_FILE   = os.path.join(INSTALL_DIR, "launch_config.txt")
MODELS_JSON_URL = "https://raw.githubusercontent.com/dinethdddd643-max/ai-assistant/main/models_list/models.json"

os.makedirs(MODELS_DIR, exist_ok=True)

# ── Load model list ───────────────────────────────────────────────────────────
def load_models():
    # Try to refresh from internet, fall back to local copy
    try:
        with urllib.request.urlopen(MODELS_JSON_URL, timeout=5) as r:
            return json.loads(r.read().decode())
    except Exception:
        pass
    if os.path.exists(MODELS_JSON):
        with open(MODELS_JSON) as f:
            return json.load(f)
    return []

# ── GPU detection ─────────────────────────────────────────────────────────────
def detect_gpu():
    """Return a dict with gpu_available and suggested_layers."""
    result = {"gpu_available": False, "name": "None detected", "vram_gb": 0, "suggested_layers": 0}
    try:
        import subprocess
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL, timeout=5
        ).decode().strip()
        if out:
            parts = out.split(",")
            name   = parts[0].strip()
            vram   = int(parts[1].strip()) // 1024  # MB → GB
            layers = min(35, max(8, vram * 4))       # rough heuristic
            result.update({"gpu_available": True, "name": name, "vram_gb": vram, "suggested_layers": layers})
            return result
    except Exception:
        pass
    # Try Vulkan via vulkaninfo
    try:
        import subprocess
        out = subprocess.check_output(["vulkaninfo", "--summary"], stderr=subprocess.DEVNULL, timeout=5).decode()
        if "GPU" in out or "deviceName" in out:
            result.update({"gpu_available": True, "name": "Vulkan GPU", "vram_gb": 4, "suggested_layers": 16})
    except Exception:
        pass
    return result

# ── Write launch config ───────────────────────────────────────────────────────
def write_config(model_path, gpu_layers, n_ctx, backend):
    with open(CONFIG_FILE, "w") as f:
        f.write(f"model={model_path}\n")
        f.write(f"gpu_layers={gpu_layers}\n")
        f.write(f"n_ctx={n_ctx}\n")
        f.write(f"backend={backend}\n")
    print(f"[Config] Written to {CONFIG_FILE}")

# ── Download with progress ────────────────────────────────────────────────────
def download_model(url, dest_path, progress_var, status_var, root):
    def reporthook(count, block_size, total_size):
        if total_size > 0:
            pct = count * block_size * 100 / total_size
            progress_var.set(min(pct, 100))
            status_var.set(f"Downloading... {min(pct,100):.1f}%  ({count*block_size/1e9:.2f} / {total_size/1e9:.2f} GB)")
            root.update_idletasks()

    try:
        urllib.request.urlretrieve(url, dest_path, reporthook)
        return True
    except Exception as e:
        status_var.set(f"Error: {e}")
        return False

# ── GUI ───────────────────────────────────────────────────────────────────────
class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI Assistant — Setup")
        self.geometry("700x580")
        self.resizable(False, False)
        self.configure(bg="#1e1e2e")

        self.models    = load_models()
        self.gpu_info  = detect_gpu()
        self.selected  = tk.StringVar()
        self.gpu_layers_var = tk.IntVar(value=self.gpu_info["suggested_layers"])
        self.n_ctx_var  = tk.IntVar(value=4096)
        self.backend_var= tk.StringVar(value="vulkan" if self.gpu_info["gpu_available"] else "cpu")
        self.use_gpu    = tk.BooleanVar(value=self.gpu_info["gpu_available"])
        self.progress   = tk.DoubleVar(value=0)
        self.status     = tk.StringVar(value="Ready")

        self._build_ui()

    # ── UI Layout ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TLabel",      background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#cba6f7")
        style.configure("TFrame",      background="#1e1e2e")
        style.configure("TButton",     font=("Segoe UI", 10, "bold"), padding=6)
        style.configure("TCheckbutton",background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        style.configure("TRadiobutton",background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        style.configure("green.Horizontal.TProgressbar", troughcolor="#313244", background="#a6e3a1")

        root_frame = ttk.Frame(self, padding=20)
        root_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(root_frame, text="🤖  AI Assistant Setup", style="Header.TLabel").pack(anchor="w", pady=(0,10))

        # GPU info
        gpu_frame = ttk.Frame(root_frame)
        gpu_frame.pack(fill=tk.X, pady=(0,10))
        gpu_status = f"✅ {self.gpu_info['name']}  ({self.gpu_info['vram_gb']} GB VRAM)" \
                     if self.gpu_info["gpu_available"] else "⚠️ No GPU detected — CPU mode"
        ttk.Label(gpu_frame, text=f"GPU: {gpu_status}").pack(anchor="w")

        # Model list
        ttk.Label(root_frame, text="Select a model to download:", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(5,4))
        for m in self.models:
            already = os.path.exists(os.path.join(MODELS_DIR, m["filename"]))
            label = f"{'✔ ' if already else ''}  {m['name']}  ({m['size_gb']} GB)  — {m['description']}"
            rb = ttk.Radiobutton(root_frame, text=label, value=m["id"], variable=self.selected)
            rb.pack(anchor="w", padx=10)
        if self.models:
            self.selected.set(self.models[0]["id"])

        ttk.Separator(root_frame, orient="horizontal").pack(fill=tk.X, pady=10)

        # Options
        opts = ttk.Frame(root_frame)
        opts.pack(fill=tk.X)

        # Use GPU toggle
        gpu_check = ttk.Checkbutton(opts, text="Use GPU acceleration", variable=self.use_gpu,
                                    command=self._toggle_gpu)
        gpu_check.grid(row=0, column=0, sticky="w", pady=3)

        # Backend
        ttk.Label(opts, text="Backend:").grid(row=1, column=0, sticky="w")
        backends = ttk.Frame(opts)
        backends.grid(row=1, column=1, sticky="w")
        for b in ["vulkan", "cuda", "cpu"]:
            ttk.Radiobutton(backends, text=b.upper(), variable=self.backend_var, value=b).pack(side=tk.LEFT, padx=4)

        # GPU Layers
        ttk.Label(opts, text="GPU Layers (0 = CPU only):").grid(row=2, column=0, sticky="w", pady=(6,0))
        self.layers_spin = ttk.Spinbox(opts, from_=0, to=100, textvariable=self.gpu_layers_var, width=6)
        self.layers_spin.grid(row=2, column=1, sticky="w", pady=(6,0))

        # Context length
        ttk.Label(opts, text="Context length (n_ctx):").grid(row=3, column=0, sticky="w", pady=(6,0))
        ttk.Spinbox(opts, from_=512, to=32768, increment=512, textvariable=self.n_ctx_var, width=7)\
            .grid(row=3, column=1, sticky="w", pady=(6,0))

        ttk.Separator(root_frame, orient="horizontal").pack(fill=tk.X, pady=10)

        # Progress
        ttk.Progressbar(root_frame, variable=self.progress, maximum=100,
                        style="green.Horizontal.TProgressbar", length=640).pack(fill=tk.X)
        ttk.Label(root_frame, textvariable=self.status).pack(anchor="w", pady=(4,8))

        # Buttons
        btn_frame = ttk.Frame(root_frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="⬇  Download & Configure", command=self._run).pack(side=tk.LEFT, padx=(0,8))
        ttk.Button(btn_frame, text="Skip (Use Existing Model)", command=self._skip).pack(side=tk.LEFT)

    def _toggle_gpu(self):
        if not self.use_gpu.get():
            self.gpu_layers_var.set(0)
            self.backend_var.set("cpu")
        else:
            self.gpu_layers_var.set(self.gpu_info["suggested_layers"])
            self.backend_var.set("vulkan")

    def _get_selected_model(self):
        mid = self.selected.get()
        return next((m for m in self.models if m["id"] == mid), None)

    def _run(self):
        model = self._get_selected_model()
        if not model:
            messagebox.showerror("Error", "Please select a model.")
            return

        dest = os.path.join(MODELS_DIR, model["filename"])

        if not os.path.exists(dest):
            self.status.set("Starting download...")
            self.update_idletasks()
            ok = download_model(model["url"], dest, self.progress, self.status, self)
            if not ok:
                messagebox.showerror("Download Failed", f"Could not download model.\nTry again or place a .gguf file in:\n{MODELS_DIR}")
                return

        write_config(dest, self.gpu_layers_var.get(), self.n_ctx_var.get(), self.backend_var.get())
        self.status.set("✅ Done! You can now launch AI Assistant.")
        self.progress.set(100)
        messagebox.showinfo("Setup Complete", "Model downloaded and configured!\nLaunch AI Assistant from your desktop shortcut.")
        self.destroy()

    def _skip(self):
        # Find any existing model
        existing = [f for f in os.listdir(MODELS_DIR) if f.endswith(".gguf")]
        if not existing:
            messagebox.showwarning("No Model Found", f"No .gguf files found in:\n{MODELS_DIR}\n\nPlease download a model first.")
            return
        dest = os.path.join(MODELS_DIR, existing[0])
        write_config(dest, self.gpu_layers_var.get(), self.n_ctx_var.get(), self.backend_var.get())
        messagebox.showinfo("Configured", f"Using existing model:\n{existing[0]}")
        self.destroy()


if __name__ == "__main__":
    app = InstallerApp()
    app.mainloop()
