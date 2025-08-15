import json, os
from urllib.parse import urlencode
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from flask import send_from_directory, abort
import requests

# ---- Load config ----
CONF = json.load(open("server_config.json", encoding="utf-8"))
AGENT = CONF.get("AGENT_BASE_URL", "http://192.168.193.159:8787").rstrip("/")
AGENT_KEY = CONF.get("AGENT_API_KEY", "change-me")
BIND = CONF.get("SERVER_BIND", "0.0.0.0")
PORT = int(CONF.get("SERVER_PORT", 5008))

app = Flask(__name__)
CORS(app)

def agent_headers(extra=None):
    h = {"X-API-KEY": AGENT_KEY}
    if extra:
        h.update(extra)
    return h

def forward_get(path, params=None):
    try:
        r = requests.get(f"{AGENT}{path}", headers=agent_headers(), params=params, timeout=30)
        return Response(r.content, r.status_code, r.headers.items())
    except requests.RequestException as e:
        return jsonify({"success": False, "error": str(e)}), 502

def forward_put(path, data=None, params=None, mime=None):
    try:
        r = requests.put(f"{AGENT}{path}", headers=agent_headers({"Content-Type": mime} if mime else None),
                         params=params, data=data, timeout=60)
        return Response(r.content, r.status_code, r.headers.items())
    except requests.RequestException as e:
        return jsonify({"success": False, "error": str(e)}), 502

def forward_post(path, data=None, params=None, mime=None):
    try:
        r = requests.post(f"{AGENT}{path}", headers=agent_headers({"Content-Type": mime} if mime else None),
                          params=params, data=data, timeout=60)
        return Response(r.content, r.status_code, r.headers.items())
    except requests.RequestException as e:
        return jsonify({"success": False, "error": str(e)}), 502

def forward_delete(path, params=None):
    try:
        r = requests.delete(f"{AGENT}{path}", headers=agent_headers(), params=params, timeout=60)
        return Response(r.content, r.status_code, r.headers.items())
    except requests.RequestException as e:
        return jsonify({"success": False, "error": str(e)}), 502

# ---------- Health ----------
@app.get("/health")
def health():
    # server health + agent health
    agent = requests.get(f"{AGENT}/health", headers=agent_headers(), timeout=10)
    return jsonify({"server_ok": True, "agent_ok": agent.ok})

# ---------- GPO list ----------
@app.get("/api/gpos")
def api_gpos():
    return forward_get("/gpos")

# ---------- Treeview ----------
@app.get("/api/gpo/<guid>/treeview")
def api_treeview(guid):
    include_details = request.args.get("includeDetails", "false")
    return forward_get(f"/gpo/{guid}/treeview", params={"includeDetails": include_details})

# ---------- GPT.INI ----------
@app.get("/api/gpo/<guid>/gpt-ini")
def api_get_gpt_ini(guid):
    return forward_get(f"/gpo/{guid}/gpt-ini")

@app.put("/api/gpo/<guid>/gpt-ini")
def api_put_gpt_ini(guid):
    raw = request.get_data()
    # truyền nguyên vẹn nội dung (text/plain)
    return forward_put(f"/gpo/{guid}/gpt-ini", data=raw, mime=request.headers.get("Content-Type", "text/plain"))

# ---------- Scripts ----------
@app.get("/api/gpo/<guid>/scripts")
def api_get_scripts(guid):
    side = request.args.get("side", "Machine")
    return forward_get(f"/gpo/{guid}/scripts", params={"side": side})

@app.post("/api/gpo/<guid>/scripts")
def api_add_script(guid):
    side = request.args.get("side", "Machine")
    typ = request.args.get("type", "Startup")
    filename = request.args.get("filename") or request.args.get("name")
    if not filename:
        return jsonify({"success": False, "error": "missing filename"}), 400
    data = request.get_data()
    return forward_post(f"/gpo/{guid}/scripts",
                        params={"side": side, "type": typ, "filename": filename},
                        data=data, mime=request.headers.get("Content-Type", "application/octet-stream"))

@app.delete("/api/gpo/<guid>/scripts")
def api_delete_script(guid):
    side = request.args.get("side", "Machine")
    typ = request.args.get("type", "Startup")
    filename = request.args.get("filename")
    if not filename:
        return jsonify({"success": False, "error": "missing filename"}), 400
    return forward_delete(f"/gpo/{guid}/scripts",
                          params={"side": side, "type": typ, "filename": filename})

# ---------- Security Settings ----------
@app.get("/api/gpo/<guid>/security")
def api_get_security(guid):
    side = request.args.get("side", "Machine")
    section = request.args.get("section")  # <-- nhận thêm
    params = {"side": side}
    if section:                      # <-- forward nếu có
        params["section"] = section
    return forward_get(f"/gpo/{guid}/security", params=params)

# ---------- Preferences ----------
@app.get("/api/gpo/<guid>/preferences")
def api_get_preferences(guid):
    side = request.args.get("side", "Machine")
    return forward_get(f"/gpo/{guid}/preferences", params={"side": side})

# ---------- Administrative Templates / registry.pol ----------
@app.get("/api/gpo/<guid>/registry-pol")
def api_get_registry_pol(guid):
    side = request.args.get("side", "Machine")
    use_lgpo = request.args.get("use_lgpo", "false")
    return forward_get(f"/gpo/{guid}/registry-pol", params={"side": side, "use_lgpo": use_lgpo})

# ---------- Local Security ----------
@app.get("/api/local/security")
def api_local_security():
    section = request.args.get("section")  # vd: security/account-policies/password-policy
    params = {}
    if section: params["section"] = section
    return forward_get("/local/security", params=params)

@app.get("/api/local/treeview")
def api_local_treeview():
    include_details = request.args.get("includeDetails", "false")
    return forward_get("/local/treeview", params={"includeDetails": include_details})

@app.get("/")
def index():
    try:
        return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "gpo_viewer.html")
    except Exception:
        return jsonify({"ok": False, "error": "gpo_viewer.html not found beside app.py"}), 404

# ---------- Extra debug endpoints (optional) ----------
@app.get("/agent/health")
def agent_health():
    try:
        r = requests.get(f"{AGENT}/health", headers=agent_headers(), timeout=10)
        return jsonify({"ok": r.ok, "status": r.status_code, "text": r.text})
    except requests.RequestException as e:
        return jsonify({"ok": False, "error": str(e)}), 502

# Proxy GET bất kỳ path sang agent để test nhanh (chỉ GET)
@app.get("/agent/<path:subpath>")
def agent_passthrough(subpath):
    try:
        r = requests.get(f"{AGENT}/{subpath}", headers=agent_headers(), params=request.args, timeout=30)
        return Response(r.content, r.status_code, r.headers.items())
    except requests.RequestException as e:
        return jsonify({"success": False, "error": str(e)}), 502

# ---------- Run ----------
if __name__ == "__main__":
    app.run(host=BIND, port=PORT)
