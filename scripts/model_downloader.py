#!/usr/bin/env python3
"""
AI Assistant — Model Downloader & Setup (FIXED)
Now safely updates the GUI from the install thread.
"""
import os
import sys
import json
import subprocess
import urllib.request
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import queue

INSTALL_DIR   = os.path.dirname(os.path.abspath(__file__))
INSTALL_ROOT  = os.path.dirname(INSTALL_DIR)
MODELS_DIR    = os.path.join(INSTALL_ROOT, "models")
MODELS_JSON   = os.path.join(INSTALL_ROOT, "models_list", "models.json")
CONFIG_FILE   = os.path.join(INSTALL_ROOT, "launch_config.txt")
MODELS_JSON_URL = "https://raw.githubusercontent.com/dinethdddd643-max/ai-assistant/main/models_list/models.json"

os.makedirs(MODELS_DIR, exist_ok=True)

# ── Load model list ───────────────────────────────────────────────────────────
def load_models():
    try:
        with urllib.request.urlopen(MODELS_JSON_URL, timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception:
        pass
    if os.path.exists(MODELS_JSON):
        with open(MODELS_JSON) as f:
            return json.load(f)
    return []

# ── GPU detection ─────────────────────────────────────────────────────────────
def detect_gpu():
    result = {"gpu_available": False, "name": "None detected", "vram_gb": 0, "suggested_layers": 0}
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL, timeout=5
        ).decode().strip()
        if out:
            parts = out.split(",")
            name  = parts[0].strip()
            vram  = int(parts[1].strip()) // 1024
            layers = min(35, max(8, vram * 4))
            result.update({"gpu_available": True, "name": name, "vram_gb": vram, "suggested_layers": layers})
            return result
    except Exception:
        pass
    try:
        out = subprocess.check_output(["vulkaninfo", "--summary"], stderr=subprocess.DEVNULL, timeout=5).decode()
        if out:
            result.update({"gpu_available": True, "name": "Vulkan GPU", "vram_gb": 4, "suggested_layers": 16})
    except Exception:
        pass
    return result

# ── Write config ──────────────────────────────────────────────────────────────
def write_config(model_path, gpu_layers, n_ctx, backend):
    with open(CONFIG_FILE, "w") as f:
        f.write(f"model={model_path}\n")
        f.write(f"gpu_layers={gpu_layers}\n")
        f.write(f"n_ctx={n_ctx}\n")
        f.write(f"backend={backend}\n")

# ── Main App ──────────────────────────────────────────────────────────────────
class SetupApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI Assistant — Setup")
        self.geometry("720x640")
        self.resizable(False, False)
        self.configure(bg="#1e1e2e")

        self.log_queue = queue.Queue()          # ← NEW: safe communication
        self.models        = load_models()
        self.gpu_info      = detect_gpu()
        self.selected      = tk.StringVar(value=self.models[0]["id"] if self.models else "")
        self.gpu_layers_var = tk.IntVar(value=self.gpu_info["suggested_layers"])
        self.n_ctx_var     = tk.IntVar(value=4096)
        self.backend_var   = tk.StringVar(value="vulkan" if self.gpu_info["gpu_available"] else "cpu")
        self.use_gpu       = tk.BooleanVar(value=self.gpu_info["gpu_available"])
        self.progress      = tk.DoubleVar(value=0)
        self.status        = tk.StringVar(value="Ready")

        self._build_ui()
        self.after(100, self.process_queue)     # ← Start polling the queue

    def _build_ui(self):
        # (same styling as before – unchanged)
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TLabel",      background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#cba6f7", background="#1e1e2e")
        style.configure("TFrame",      background="#1e1e2e")
        style.configure("TButton",     font=("Segoe UI", 10, "bold"), padding=6)
        style.configure("TCheckbutton",background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        style.configure("TRadiobutton",background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        style.configure("green.Horizontal.TProgressbar", troughcolor="#313244", background="#a6e3a1")
        style.configure("TSpinbox",    fieldbackground="#313244", foreground="#cdd6f4")

        f = ttk.Frame(self, padding=20)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text="🤖  AI Assistant Setup", style="Header.TLabel").pack(anchor="w", pady=(0,8))

        gpu_txt = f"✅ GPU: {self.gpu_info['name']}  ({self.gpu_info['vram_gb']} GB VRAM)" \
                  if self.gpu_info["gpu_available"] else "⚠️ No GPU detected — will run on CPU"
        ttk.Label(f, text=gpu_txt).pack(anchor="w", pady=(0,8))

        # Step 1
        ttk.Label(f, text="Step 1 — Install Python packages", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(4,4))
        ttk.Label(f, text="Required: flask, llama-cpp-python (large download ~300MB)", foreground="#a6adc8",
                  background="#1e1e2e", font=("Segoe UI", 9)).pack(anchor="w")

        self.log_box = scrolledtext.ScrolledText(f, height=5, bg="#181825", fg="#cdd6f4",
                                                  font=("Consolas", 9), state="disabled", bd=0)
        self.log_box.pack(fill=tk.X, pady=(6,0))

        btn_pip = ttk.Frame(f)
        btn_pip.pack(fill=tk.X, pady=(6,8))
        ttk.Button(btn_pip, text="Install Packages Now", command=self._install_packages).pack(side=tk.LEFT)
        self.pip_status = ttk.Label(btn_pip, text="", foreground="#a6e3a1", background="#1e1e2e")
        self.pip_status.pack(side=tk.LEFT, padx=10)

        ttk.Separator(f, orient="horizontal").pack(fill=tk.X, pady=6)

        # Step 2 – Models
        ttk.Label(f, text="Step 2 — Choose a model to download", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(4,4))

        for m in self.models:
            already = os.path.exists(os.path.join(MODELS_DIR, m["filename"]))
            lbl = f"{'✔ ' if already else ''}  {m['name']}  ({m['size_gb']} GB)"
            rb = ttk.Radiobutton(f, text=lbl, value=m["id"], variable=self.selected)
            rb.pack(anchor="w", padx=10)
            desc = ttk.Label(f, text=f"     {m['description']}", foreground="#6c7086",
                             background="#1e1e2e", font=("Segoe UI", 9))
            desc.pack(anchor="w")

        ttk.Separator(f, orient="horizontal").pack(fill=tk.X, pady=6)

        # Step 3 – Hardware
        ttk.Label(f, text="Step 3 — Configure hardware", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(4,2))

        opts = ttk.Frame(f)
        opts.pack(fill=tk.X)

        ttk.Checkbutton(opts, text="Use GPU acceleration", variable=self.use_gpu,
                        command=self._toggle_gpu).grid(row=0, column=0, sticky="w", pady=2)

        ttk.Label(opts, text="Backend:").grid(row=1, column=0, sticky="w")
        bf = ttk.Frame(opts)
        bf.grid(row=1, column=1, sticky="w")
        for b in ["vulkan", "cuda", "cpu"]:
            ttk.Radiobutton(bf, text=b.upper(), variable=self.backend_var, value=b).pack(side=tk.LEFT, padx=4)

        ttk.Label(opts, text="GPU Layers (0 = CPU only):").grid(row=2, column=0, sticky="w", pady=(4,0))
        ttk.Spinbox(opts, from_=0, to=100, textvariable=self.gpu_layers_var, width=6)\
            .grid(row=2, column=1, sticky="w", pady=(4,0))

        ttk.Label(opts, text="Context length:").grid(row=3, column=0, sticky="w", pady=(4,0))
        ttk.Spinbox(opts, from_=512, to=32768, increment=512, textvariable=self.n_ctx_var, width=7)\
            .grid(row=3, column=1, sticky="w", pady=(4,0))

        ttk.Separator(f, orient="horizontal").pack(fill=tk.X, pady=8)

        # Progress + Buttons
        ttk.Progressbar(f, variable=self.progress, maximum=100,
                        style="green.Horizontal.TProgressbar").pack(fill=tk.X)
        ttk.Label(f, textvariable=self.status).pack(anchor="w", pady=(4,6))

        bf2 = ttk.Frame(f)
        bf2.pack(fill=tk.X)
        ttk.Button(bf2, text="⬇  Download Model & Finish", command=self._run).pack(side=tk.LEFT, padx=(0,8))
        ttk.Button(bf2, text="Skip (Use Existing Model)",  command=self._skip).pack(side=tk.LEFT)

    # ── Safe GUI updates from thread ─────────────────────────────────────
    def process_queue(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                if isinstance(item, str):
                    # normal log line
                    self.log_box.configure(state="normal")
                    self.log_box.insert(tk.END, item + "\n")
                    self.log_box.see(tk.END)
                    self.log_box.configure(state="disabled")
                elif isinstance(item, tuple) and item[0] == "status":
                    _, text, color = item
                    self.pip_status.config(text=text, foreground=color)
        except queue.Empty:
            pass
        self.after(50, self.process_queue)   # keep polling

    def _log(self, text):
        self.log_queue.put(text)

    def _set_pip_status(self, text, color):
        self.log_queue.put(("status", text, color))

    def _toggle_gpu(self):
        if not self.use_gpu.get():
            self.gpu_layers_var.set(0)
            self.backend_var.set("cpu")
        else:
            self.gpu_layers_var.set(self.gpu_info["suggested_layers"])
            self.backend_var.set("vulkan")

    def _install_packages(self):
        self.pip_status.config(text="Installing...", foreground="#f9e2af")
        self._log("Starting package installation...")

        def run():
            for pkg in ["flask", "llama-cpp-python"]:
                self._log(f"pip install {pkg} ...")
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", pkg],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    self._log(f"  ✔ {pkg} installed successfully")
                else:
                    self._log(f"  ✖ {pkg} failed:\n{result.stderr[:400]}")
            self._set_pip_status("✔ Done", "#a6e3a1")
            self._log("Package installation finished!")

        threading.Thread(target=run, daemon=True).start()

    # (the rest of the methods _get_selected, _run, _skip are unchanged)
    def _get_selected(self):
        mid = self.selected.get()
        return next((m for m in self.models if m["id"] == mid), None)

    def _run(self):
        model = self._get_selected()
        if not model:
            messagebox.showerror("Error", "Please select a model.")
            return

        dest = os.path.join(MODELS_DIR, model["filename"])

        if not os.path.exists(dest):
            self.status.set("Starting download...")
            self.update_idletasks()

            def reporthook(count, block, total):
                if total > 0:
                    pct = min(count * block * 100 / total, 100)
                    self.progress.set(pct)
                    self.status.set(f"Downloading... {pct:.1f}%  ({count*block/1e9:.2f} / {total/1e9:.2f} GB)")
                    self.update_idletasks()

            try:
                urllib.request.urlretrieve(model["url"], dest, reporthook)
            except Exception as e:
                messagebox.showerror("Download Failed", f"Could not download model.\n{e}")
                return

        write_config(dest, self.gpu_layers_var.get(), self.n_ctx_var.get(), self.backend_var.get())
        self.progress.set(100)
        self.status.set("✔ Setup complete!")
        messagebox.showinfo("Done", "Setup complete!\nYou can now launch AI Assistant from the desktop shortcut.")
        self.destroy()

    def _skip(self):
        existing = [f for f in os.listdir(MODELS_DIR) if f.endswith(".gguf")]
        if not existing:
            messagebox.showwarning("No Model", f"No .gguf model found in:\n{MODELS_DIR}")
            return
        dest = os.path.join(MODELS_DIR, existing[0])
        write_config(dest, self.gpu_layers_var.get(), self.n_ctx_var.get(), self.backend_var.get())
        messagebox.showinfo("Configured", f"Using existing model:\n{existing[0]}")
        self.destroy()


if __name__ == "__main__":
    app = SetupApp()
    app.mainloop()