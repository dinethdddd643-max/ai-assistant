from llama_cpp import Llama
from flask import Flask, request, Response
import sqlite3
import os

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

DB_PATH     = os.path.join(BASE_DIR, "assistant.db")
MODEL_DIR   = os.path.join(BASE_DIR, "models")
CONFIG_PATH = os.path.join(BASE_DIR, "launch_config.txt")

def read_config():
    cfg = {"model": None, "gpu_layers": 0, "n_ctx": 4096}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            for line in f:
                k, _, v = line.strip().partition("=")
                if k == "model":        cfg["model"]      = v
                elif k == "gpu_layers": cfg["gpu_layers"] = int(v)
                elif k == "n_ctx":      cfg["n_ctx"]       = int(v)
    return cfg

cfg = read_config()

MODEL_PATH = cfg["model"] or next(
    (os.path.join(MODEL_DIR, f) for f in os.listdir(MODEL_DIR) if f.endswith(".gguf")),
    None
)

if not MODEL_PATH or not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"No .gguf model found in {MODEL_DIR}")

print(f"[AI Assistant] Loading model: {MODEL_PATH}")
print(f"[AI Assistant] GPU layers: {cfg['gpu_layers']}  |  Context: {cfg['n_ctx']}")

llm = Llama(
    model_path=MODEL_PATH,
    n_gpu_layers=cfg["gpu_layers"],
    n_ctx=cfg["n_ctx"],
)

# ── Database ──────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS personality (
            id          INTEGER PRIMARY KEY,
            description TEXT    NOT NULL DEFAULT '',
            tone        TEXT    NOT NULL DEFAULT '',
            style       TEXT    NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS chat_history (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            user_msg TEXT NOT NULL,
            bot_msg  TEXT NOT NULL,
            ts       DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS rules (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            rule  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS main_memory (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            info TEXT NOT NULL
        );

                      CREATE TABLE IF NOT EXISTS starter_scenario (
            id       INTEGER PRIMARY KEY,
            scenario TEXT NOT NULL DEFAULT ''
        );
    """)

    # Ensure one empty personality row exists (no hardcoded values)
    cur.execute("SELECT COUNT(*) FROM personality")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO personality (description, tone, style) VALUES ('', '', '')")

    # Ensure one empty starter_scenario row exists
    cur.execute("SELECT COUNT(*) FROM starter_scenario")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO starter_scenario (scenario) VALUES ('')")

    # Seed rules
    cur.execute("SELECT COUNT(*) FROM rules")
    if cur.fetchone()[0] == 0:
        rules = [
            "Start with a short scene or action (like a story)",
            "Describe emotions, movements, and environment",
            "Then include dialogue",
            "Stay in character at all times",
            "Never respond like a normal assistant",
            "Never break roleplay",
        ]
        cur.executemany("INSERT INTO rules (rule) VALUES (?)", [(r,) for r in rules])

    

    conn.commit()
    conn.close()

init_db()

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_personality():
    conn = get_db()
    row = conn.execute("SELECT description, tone, style FROM personality LIMIT 1").fetchone()
    conn.close()
    if row:
        return f"{row['description']}\nTone: {row['tone']}\nStyle: {row['style']}"
    return ""

def get_chat_history(limit=20):
    conn = get_db()
    rows = conn.execute(
        "SELECT user_msg, bot_msg FROM chat_history ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    history = ""
    for r in reversed(rows):
        history += f"\nUser: {r['user_msg']}\nBot: {r['bot_msg']}"
    return history

def get_rules():
    conn = get_db()
    rows = conn.execute("SELECT rule FROM rules").fetchall()
    conn.close()
    return "\n".join(r["rule"] for r in rows)

def get_main_memory():
    conn = get_db()
    rows = conn.execute("SELECT info FROM main_memory").fetchall()
    conn.close()
    return "\n".join(r["info"] for r in rows)

def save_chat_history(user_msg, bot_msg):
    conn = get_db()
    conn.execute(
        "INSERT INTO chat_history (user_msg, bot_msg) VALUES (?, ?)", (user_msg, bot_msg)
    )
    conn.commit()
    conn.close()

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "")

    def generate():
        personality = get_personality()
        rules       = get_rules()
        memory      = get_main_memory()
        history     = get_chat_history()

        prompt = (
            "\n### SYSTEM: You are a roleplay character. Always respond in immersive roleplay format."
            f"\n### Rules: {rules}"
            f"\n### Character: {personality}"
            f"\n### Conversation: {history}"
            f"\n### Memory: {memory}"
            "\n### SCENE: Begin naturally as part of an ongoing story."
            f"\n### User: {user_input}"
            "\n### Bot:"
        )

        stream = llm(
            prompt,
            max_tokens=200,
            temperature=0.7,
            repeat_penalty=1.1,
            top_p=0.9,
            stop=["\n### User", "### User:", "User:", "\n### Bot", "### Bot:", "Bot:"],
            stream=True,
        )

        full_reply = ""
        for chunk in stream:
            token = chunk["choices"][0]["text"]
            full_reply += token
            yield token

        save_chat_history(user_input, full_reply)

    return Response(generate(), content_type="text/plain")


@app.route("/personality", methods=["GET", "POST"])
def personality():
    if request.method == "GET":
        conn = get_db()
        row = conn.execute("SELECT * FROM personality LIMIT 1").fetchone()
        conn.close()
        return {"description": row["description"], "tone": row["tone"], "style": row["style"]}
    data = request.json
    conn = get_db()
    conn.execute("UPDATE personality SET description=?, tone=?, style=?",
                 (data["description"], data["tone"], data["style"]))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.route("/rules", methods=["GET", "POST", "DELETE"])
def rules():
    conn = get_db()
    if request.method == "GET":
        rows = conn.execute("SELECT id, rule FROM rules").fetchall()
        conn.close()
        return {"rules": [{"id": r["id"], "rule": r["rule"]} for r in rows]}
    if request.method == "POST":
        conn.execute("INSERT INTO rules (rule) VALUES (?)", (request.json["rule"],))
        conn.commit()
        conn.close()
        return {"status": "ok"}
    rule_id = request.json["id"]
    conn.execute("DELETE FROM rules WHERE id=?", (rule_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.route("/memory", methods=["GET", "POST", "DELETE"])
def memory():
    conn = get_db()
    if request.method == "GET":
        rows = conn.execute("SELECT id, info FROM main_memory").fetchall()
        conn.close()
        return {"memory": [{"id": r["id"], "info": r["info"]} for r in rows]}
    if request.method == "POST":
        conn.execute("INSERT INTO main_memory (info) VALUES (?)", (request.json["info"],))
        conn.commit()
        conn.close()
        return {"status": "ok"}
    mem_id = request.json["id"]
    conn.execute("DELETE FROM main_memory WHERE id=?", (mem_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.route("/history/clear", methods=["POST"])
def clear_history():
    conn = get_db()
    conn.execute("DELETE FROM chat_history")
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.route("/setup/status", methods=["GET"])
def setup_status():
    """Returns whether the user has completed initial setup."""
    conn = get_db()
    row = conn.execute("SELECT description FROM personality LIMIT 1").fetchone()
    conn.close()
    is_done = row and row["description"].strip() != ""
    return {"setup_complete": is_done}


@app.route("/starter_scenario", methods=["GET", "POST"])
def starter_scenario():
    conn = get_db()
    if request.method == "GET":
        row = conn.execute("SELECT scenario FROM starter_scenario LIMIT 1").fetchone()
        conn.close()
        return {"scenario": row["scenario"] if row else ""}
    data = request.json
    conn.execute("UPDATE starter_scenario SET scenario=?", (data["scenario"],))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.route("/history", methods=["GET"])
def get_history():
    """Returns full chat history in chronological order for UI restore."""
    conn = get_db()
    rows = conn.execute(
        "SELECT user_msg, bot_msg FROM chat_history ORDER BY id ASC"
    ).fetchall()
    conn.close()
    return {"history": [{"user_msg": r["user_msg"], "bot_msg": r["bot_msg"]} for r in rows]}

@app.route("/memory/replace", methods=["POST"])
def memory_replace():
    items = request.json.get("items", [])
    conn = get_db()
    conn.execute("DELETE FROM main_memory")
    conn.executemany("INSERT INTO main_memory (info) VALUES (?)", [(i,) for i in items])
    conn.commit()
    conn.close()
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(port=5000, debug=False)


