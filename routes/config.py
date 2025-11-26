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
    body {{ margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', 'Apple Color Emoji', 'Segoe UI Emoji'; background: #f7f7f8; color: #1f2328; }}
    .card {{ max-width: 960px; margin: 0 auto; background: #fff; border: 1px solid #e6e8eb; border-radius: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }}
    .header {{ padding: 16px 20px; border-bottom: 1px solid #e6e8eb; font-weight: 600; }}
    .content {{ padding: 20px; }}
    .row {{ display: flex; gap: 12px; align-items: center; margin-bottom: 12px; }}
    input[type=text] {{ flex: 1; padding: 8px 10px; border: 1px solid #d0d7de; border-radius: 8px; font-size: 14px; }}
    button {{ padding: 8px 14px; border: 1px solid #1f883d; background: #1f883d; color: #fff; border-radius: 8px; font-size: 14px; cursor: pointer; }}
    button.secondary {{ border-color: #0969da; background: #0969da; }}
    textarea {{ width: 100%; height: 420px; padding: 10px; border: 1px solid #d0d7de; border-radius: 8px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono'; font-size: 13px; line-height: 1.5; resize: vertical; }}
    .status {{ margin-top: 10px; min-height: 24px; font-size: 13px; }}
  </style>
</head>
<body>
  <div class='card'>
    <div class='header'>在线编辑配置</div>
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
    function setStatus(msg, ok=true) {{ statusEl.textContent = msg; statusEl.style.color = ok ? '#1f883d' : '#d1242f'; }}
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
    if (qs.get('name')) {{ load(); }}
  </script>
</body>
</html>
"""
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}
