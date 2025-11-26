from flask import Blueprint, request, Response
import logging
from services import config_service

logger = logging.getLogger(__name__)

config_bp = Blueprint("config", __name__)

@config_bp.route("/config/load", methods=["GET"])
def load_config():
    name = request.args.get("name")
    text, err = config_service.load_config_text(name)
    if err is not None:
        return err, 400
    return Response(text, mimetype='text/yaml')

@config_bp.route("/config/save", methods=["POST"])
def save_config():
    name = request.args.get("name") or request.form.get("name")
    content = request.form.get("content")
    if content is None:
        content = request.get_data(as_text=True)
    ok, err = config_service.save_config_text(name, content)
    if not ok:
        return err, 400
    return "保存成功"

@config_bp.route("/config/ui", methods=["GET"])
def config_ui():
    name = request.args.get("name") or ""
    text = ""
    if name:
        loaded, err = config_service.load_config_text(name)
        if err is None and loaded is not None:
            text = loaded
    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'>
  <title>配置编辑</title>
  <style>
    :root {{ --bg:#0b0d10; --card:#0f141b; --border:#1f2a36; --text:#e6edf3; --muted:#9da7b1; --primary:#1f883d; --primary-contrast:#ffffff; --secondary:#4493f8; }}
    body[data-theme="light"] {{ --bg:#f7f7f8; --card:#ffffff; --border:#e6e8eb; --text:#1f2328; --muted:#59636e; --primary:#1f883d; --primary-contrast:#ffffff; --secondary:#0969da; }}
    body {{ margin:0; padding:24px; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,'Noto Sans','Apple Color Emoji','Segoe UI Emoji'; background:var(--bg); color:var(--text); }}
    .card {{ max-width:960px; margin:0 auto; background:var(--card); border:1px solid var(--border); border-radius:12px; box-shadow:0 1px 2px rgba(0,0,0,0.15); }}
    .header {{ padding:16px 20px; border-bottom:1px solid var(--border); font-weight:600; display:flex; justify-content:space-between; align-items:center; }}
    .content {{ padding:20px; }}
    .row {{ display:flex; gap:12px; align-items:center; margin-bottom:12px; }}
    input[type=text] {{ flex:1; padding:8px 10px; border:1px solid var(--border); background:transparent; color:var(--text); border-radius:8px; font-size:14px; }}
    button {{ padding:8px 14px; border:1px solid var(--primary); background:var(--primary); color:var(--primary-contrast); border-radius:8px; font-size:14px; cursor:pointer; }}
    button.secondary {{ border-color:var(--secondary); background:var(--secondary); }}
    button.ghost {{ border-color:var(--border); background:transparent; color:var(--text); }}
    textarea {{ width:100%; height:420px; padding:10px; border:1px solid var(--border); background:transparent; color:var(--text); border-radius:8px; font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,'Liberation Mono'; font-size:13px; line-height:1.5; resize:vertical; }}
    .status {{ margin-top:10px; min-height:24px; font-size:13px; color:var(--muted); }}
  </style>
</head>
<body>
  <div class='card'>
    <div class='header'>在线编辑配置 <button id='theme' class='ghost'>切换主题</button></div>
    <div class='content'>
      <div class='row'>
        <input id='name' type='text' placeholder='文件名，不含后缀' value='{name}'>
        <button id='load' class='secondary'>加载</button>
        <button id='save'>保存</button>
      </div>
      <textarea id='content' placeholder='在此粘贴或编辑 YAML 配置'>{text}</textarea>
      <div id='status' class='status'></div>
    </div>
  </div>
  <script>
    const qs = new URLSearchParams(location.search);
    const nameInput = document.getElementById('name');
    const contentEl = document.getElementById('content');
    const statusEl = document.getElementById('status');
    const themeBtn = document.getElementById('theme');
    function setStatus(msg, ok=true) {{ statusEl.textContent = msg; statusEl.style.color = ok ? '#1f883d' : '#d1242f'; }}
    function applyTheme(t) {{ document.body.setAttribute('data-theme', t); localStorage.setItem('theme', t); themeBtn.textContent = t==='dark' ? '切换到亮色' : '切换到暗色'; }}
    const initTheme = (localStorage.getItem('theme') || qs.get('theme') || 'dark');
    applyTheme(initTheme);
    async function load() {{
      const n = nameInput.value.trim();
      if (!n) {{ setStatus('请输入文件名', false); return; }}
      try {{
        const r = await fetch('/config/load?name=' + encodeURIComponent(n));
        if (!r.ok) {{ setStatus(await r.text(), false); return; }}
        const t = await r.text();
        contentEl.value = t;
        setStatus('已加载 ' + n);
      }} catch(e) {{ setStatus('加载失败', false); }}
    }}
    async function save() {{
      const n = nameInput.value.trim();
      const t = contentEl.value;
      if (!n) {{ setStatus('请输入文件名', false); return; }}
      try {{
        const r = await fetch('/config/save?name=' + encodeURIComponent(n), {{ method: 'POST', headers: {{ 'Content-Type': 'text/plain' }}, body: t }});
        const b = await r.text();
        if (!r.ok) {{ setStatus(b || '保存失败', false); return; }}
        setStatus('保存成功: ' + n);
      }} catch(e) {{ setStatus('保存失败', false); }}
    }}
    document.getElementById('load').addEventListener('click', load);
    document.getElementById('save').addEventListener('click', save);
    themeBtn.addEventListener('click', () => {{ applyTheme(document.body.getAttribute('data-theme')==='dark' ? 'light' : 'dark'); }});
    if (qs.get('name')) {{ load(); }}
  </script>
</body>
</html>
"""
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}
