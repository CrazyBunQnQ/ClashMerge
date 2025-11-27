from flask import Blueprint, request, Response
from services import config_service

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
    if name and name.strip().lower() == "template":
        return "不可保存模板文件", 400
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
    .ref {{ margin-top:20px; padding-top:16px; border-top:1px dashed var(--border); }}
    .ref-title {{ font-weight:600; margin-bottom:10px; display:flex; align-items:center; gap:8px; }}
    .accordion {{ display:flex; flex-direction:column; gap:10px; }}
    .item {{ border:1px solid var(--border); border-radius:8px; overflow:hidden; }}
    .item-header {{ width:100%; text-align:left; background:transparent; border:none; padding:10px 12px; color:var(--text); cursor:pointer; }}
    .item-header.important {{ color:#d1242f; }}
    .item-body {{ display:none; border-top:1px solid var(--border); }}
    pre {{ margin:0; padding:10px 12px; overflow:auto; }}
  </style>
</head>
<body>
  <div class='card'>
    <div class='header'>在线编辑配置 <button id='theme' class='ghost'>切换主题</button></div>
    <div class='content'>
      <div class='row'>
        <input id='name' type='text' placeholder='配置名称, 可加载参考配置 template' value='{name}'>
        <button id='load' class='secondary'>加载</button>
        <button id='save'>保存</button>
      </div>
      <textarea id='content' placeholder='在此粘贴或编辑 YAML 配置'>{text}</textarea>
      <div id='status' class='status'></div>
      <div class='ref'>
        <div class='ref-title'>重要配置</div>
        <div class='accordion'>
          <div class='item'><button class='item-header important' data-target='s-pull-proxy-source'>订阅源（pull-proxy-source）</button><div id='s-pull-proxy-source' class='item-body'><pre><code>订阅源列表（name、url）
从这些订阅拉取节点，合并进基础规则与分组
支持多源聚合
不配置则只包含下面自定义写死的节点</code></pre></div></div>
          <div class='item'><button class='item-header important' data-target='s-proxies'>自定义节点（proxies）</button><div id='s-proxies' class='item-body'><pre><code>静态手动节点示例（如 ss、vmess、trojan 等）
包含 name、type、server、port、认证等字段
合并好的配置中所有节点都会显示在这里
此处添加的节点必然会添加到最终合并好的配置中，适用于自建节点</code></pre></div></div>
          <div class='item'><button class='item-header important' data-target='s-filter-proxy-name'>节点名过滤（filter-proxy-name）</button><div id='s-filter-proxy-name' class='item-body'><pre><code>按节点名称过滤，支持正则表达式
匹配到的节点会被剔除，不参与生成与分组</code></pre></div></div>
          <div class='item'><button class='item-header important' data-target='s-rules'>分流规则（rules）- 有什么网站你访问不聊了，在这里最前面加规则</button><div id='s-rules' class='item-body'><pre><code>实际分流规则清单（DOMAIN-SUFFIX / DOMAIN-KEYWORD 等）
匹配到的域名按指定分组或动作（如 美国 / Proxy / DIRECT / REJECT）处理</code></pre></div></div>
        </div>
        <div class='ref-title'>次要配置(可保持默认或从你原来的订阅源里拷贝过来)</div>
        <div class='accordion'>
          <div class='item'><button class='item-header important' data-target='s-filter-proxy-server'>节点服务器过滤（filter-proxy-server）</button><div id='s-filter-proxy-server' class='item-body'><pre><code>按节点 server 值过滤（域名或 IP 片段）
用于排除不可信或不需要的节点来源</code></pre></div></div>
          <div class='item'><button class='item-header important' data-target='s-proxy-providers'>节点订阅提供者（proxy-providers）</button><div id='s-proxy-providers' class='item-body'><pre><code>服务器节点订阅提供者定义
type=http/file、path/url、interval、health-check
用于自动拉取并更新节点列表</code></pre></div></div>
          <div class='item'><button class='item-header important' data-target='s-filter-proxy-providers'>订阅提供者过滤（filter-proxy-providers）</button><div id='s-filter-proxy-providers' class='item-body'><pre><code>按订阅提供者名称过滤
用于忽略指定的 provider（例如测试源或无效源）</code></pre></div></div>
          <div class='item'><button class='item-header important' data-target='s-filter-proxy-groups'>分组过滤（filter-proxy-groups）</button><div id='s-filter-proxy-groups' class='item-body'><pre><code>按代理组名称过滤
剔除不需要的分组，避免生成后出现冗余组</code></pre></div></div>
          <div class='item'><button class='item-header' data-target='s-base-config'>base-config</button><div id='s-base-config' class='item-body'><pre><code>基础规则源列表(可以不配置)
每项包含 name、url
作为生成最终 Clash 配置的基础规则，后续拉取的代理与覆盖参数会合并到此</code></pre></div></div>
          <div class='item'><button class='item-header' data-target='s-port'>port / socks-port</button><div id='s-port' class='item-body'><pre><code>本地 HTTP 代理端口 / SOCKS5 端口
用于浏览器与系统代理接入</code></pre></div></div>
          <div class='item'><button class='item-header' data-target='s-allow-lan'>allow-lan / bind-address</button><div id='s-allow-lan' class='item-body'><pre><code>是否允许局域网访问代理
绑定监听地址（*、具体 IPv4/IPv6）
仅在 allow-lan 为 true 时生效</code></pre></div></div>
          <div class='item'><button class='item-header' data-target='s-mode'>mode</button><div id='s-mode' class='item-body'><pre><code>规则模式：Rule / Global / Direct
Rule：按规则分流（推荐）
Global：全局代理
Direct：全局直连</code></pre></div></div>
          <div class='item'><button class='item-header' data-target='s-log-level'>log-level</button><div id='s-log-level' class='item-body'><pre><code>日志级别：silent / info / warning / error / debug
级别越高输出越多，越偏向调试</code></pre></div></div>
          <div class='item'><button class='item-header' data-target='s-ipv6'>ipv6</button><div id='s-ipv6' class='item-body'><pre><code>是否在解析时返回 IPv6 地址
false 时将避免 AAAA 记录带来的连接问题</code></pre></div></div>
          <div class='item'><button class='item-header' data-target='s-external-controller'>external-controller / secret</button><div id='s-external-controller' class='item-body'><pre><code>Clash RESTful API 地址与口令
用于外部面板（如 dashboard）控制与查询</code></pre></div></div>
          <div class='item'><button class='item-header' data-target='s-hosts'>hosts</button><div id='s-hosts' class='item-body'><pre><code>静态域名解析表（支持通配符）
在 dns.enhanced-mode=redir-host 及 use-hosts=true 时生效</code></pre></div></div>
          <div class='item'><button class='item-header' data-target='s-dns'>dns</button><div id='s-dns' class='item-body'><pre><code>本地 DNS 服务配置：enable、listen、ipv6
default-nameserver：系统基础解析器
enhanced-mode：fake-ip 或 redir-host
fake-ip-range：Fake IP 池 CIDR
use-hosts：查询并返回 hosts 记录
nameserver：首选 DoH/UDP/TCP 解析器
fallback：备用解析器（非 CN 或命中过滤时采用）
fallback-filter：按 geoip/ipcidr 判定结果有效性</code></pre></div></div>
          <div class='item'><button class='item-header' data-target='s-proxy-groups'>proxy-groups</button><div id='s-proxy-groups' class='item-body'><pre><code>代理分组定义：select / url-test / fallback / load-balance 等
用于按国家/场景构建可选/测速/容错/负载的分组</code></pre></div></div>
          <div class='item'><button class='item-header' data-target='s-rule-providers'>rule-providers</button><div id='s-rule-providers' class='item-body'><pre><code>规则提供者定义：behavior=classical/domain/ipcidr
type=http/file、url、path、interval
从各项目拉取分类规则（如 YouTube/Netflix/Telegram 等）</code></pre></div></div>
        </div>
      </div>
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
      if (n.toLowerCase() === 'template') {{ setStatus('不可保存模板文件', false); return; }}
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
    document.querySelectorAll('.item-header').forEach(btn => {{
      btn.addEventListener('click', () => {{
        const id = btn.getAttribute('data-target');
        const body = document.getElementById(id);
        const show = body.style.display !== 'block';
        body.style.display = show ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>
"""
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}
