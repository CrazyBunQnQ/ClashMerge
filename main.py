import os
import sys
import yaml
import logging
from flask import Flask, request, Response
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the parent directory to sys.path to allow imports from utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import config_utils
from utils import http_utils
from utils import parse_utils

app = Flask(__name__)

# Setup logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='TRACE: %(asctime)s %(message)s',
    datefmt='%Y/%m/%d %H:%M:%S',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'errors.txt')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@app.route('/parse')
def parse_rule():
    user_config_map, base_rule_map, done = parse_request_params(request)
    if done:
        return "Error parsing request params", 400

    proxy_arr, proxy_group_arr, proxy_name_arr, done2 = get_proxies(user_config_map, request)
    if done2:
        return "Error getting proxies", 500

    return output_clash(user_config_map, base_rule_map, proxy_arr, proxy_group_arr, proxy_name_arr)

def parse_request_params(req):
    config_file_name = req.args.get("name")
    if not config_file_name:
        return None, None, True

    try:
        # Assuming config is in the parent directory's config folder relative to where script is run
        # Or in a 'config' folder in the current working directory
        config_path = os.path.abspath(os.path.join(os.getcwd(), "config", f"{config_file_name}.yaml"))
        if not os.path.exists(config_path):
             # Try relative to the python script
             config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", f"{config_file_name}.yaml")
        
        user_config_map = config_utils.load_config(config_path)
        if user_config_map is None:
            logger.error("Failed to read config file")
            return None, None, True
    except Exception as e:
        logger.error(f"error: {e}")
        return None, None, True

    base_config_name = req.args.get("baseName")
    base_config_request_url = ""

    if base_config_name:
        if "base-config" in user_config_map:
            for base_config in user_config_map["base-config"]:
                if base_config.get("name") == base_config_name:
                    base_config_request_url = base_config.get("url")
                    break
    else:
        logger.error(f"Request URL: {req.url}, IP: {http_utils.get_request_ip(req)}, No base config name provided")
        return None, None, True

    if not base_config_request_url:
        logger.error(f"Request URL: {req.url}, IP: {http_utils.get_request_ip(req)}, Base config not found")

    # Hardcoded base rule body as in Go code
    base_rule_body = """#---------------------------------------------------#
## 配置文件需要放置在 $HOME/.config/clash/config.yml
##
## 如果您不知道如何操作，请参阅 SS-Rule-Snippet 的 Wiki：
## https://github.com/Hackl0us/SS-Rule-Snippet/wiki/clash(X)
#---------------------------------------------------#

# HTTP 代理端口
port: 7890

# SOCKS5 代理端口
socks-port: 7891

# Linux 和 macOS 的 redir 透明代理端口 (重定向 TCP 和 TProxy UDP 流量)
# redir-port: 7892

# Linux 的透明代理端口（适用于 TProxy TCP 和 TProxy UDP 流量)
# tproxy-port: 7893

# HTTP(S) and SOCKS5 共用端口
# mixed-port: 7890

# 本地 SOCKS5/HTTP(S) 服务验证
# authentication:
#  - "user1:pass1"
#  - "user2:pass2"

# 允许局域网的连接（可用来共享代理）
allow-lan: true
bind-address: "*"
# 此功能仅在 allow-lan 设置为 true 时生效，支持三种参数：
# "*"                           绑定所有的 IP 地址
# 192.168.122.11                绑定一个的 IPv4 地址
# "[aaaa::a8aa:ff:fe09:57d8]"   绑定一个 IPv6 地址

# Clash 路由工作模式
# 规则模式：rule（规则） / global（全局代理）/ direct（全局直连）
mode: rule

# Clash 默认将日志输出至 STDOUT
# 设置日志输出级别 (默认级别：silent，即不输出任何内容，以避免因日志内容过大而导致程序内存溢出）。
# 5 个级别：silent / info / warning / error / debug。级别越高日志输出量越大，越倾向于调试，若需要请自行开启。
log-level: silent

# clash 的 RESTful API 监听地址
external-controller: 127.0.0.1:9090

# 存放配置文件的相对路径，或存放网页静态资源的绝对路径
# Clash core 将会将其部署在 http://{{external-controller}}/ui
# external-ui: folder

# RESTful API 的口令 (可选)
# 通过 HTTP 头中 Authorization: Bearer ${secret} 参数来验证口令
# 当 RESTful API 的监听地址为 0.0.0.0 时，请务必设定口令以保证安全
# secret: ""

# 出站网卡接口
# interface-name: en0

# DNS 服务器和建立连接时的 静态 Hosts, 仅在 dns.enhanced-mode 模式为 redir-host 生效
# 支持通配符域名 (例如: *.clash.dev, *.foo.*.example.com )
# 不使用通配符的域名优先级高于使用通配符的域名 (例如: foo.example.com > *.example.com > .example.com )
# 注意: +.foo.com 的效果等同于 .foo.com 和 foo.com
hosts:
# '*.clash.dev': 127.0.0.1
# '.dev': 127.0.0.1
# 'alpha.clash.dev': '::1'

# DNS 服务器配置(可选；若不配置，程序内置的 DNS 服务会被关闭)
dns:
  enable: true
  listen: 0.0.0.0:53
  ipv6: true # 当此选项为 false 时, AAAA 请求将返回空

  # 以下填写的 DNS 服务器将会被用来解析 DNS 服务的域名
  # 仅填写 DNS 服务器的 IP 地址
  nameserver:
    - 223.5.5.5
    - 114.114.114.114
    - 119.29.29.29
    # - tls://dns.rubyfish.cn:853

  # fallback 列表
  # 当 nameserver 列表中的服务器解析失败，或解析出的 IP 地址为污染 IP 时
  # 将会使用 fallback 列表中的服务器进行解析
  fallback:
    - 8.8.8.8
    - 1.1.1.1
    # - tls://1.0.0.1:853
    # - tls://dns.google:853

  # 建立连接时的静态 Hosts
  # 仅在 dns.enhanced-mode 模式为 redir-host 生效
  fallback-filter:
    geoip: true
    ipcidr:
      - 240.0.0.0/4
"""
    
    try:
        base_rule_map = yaml.safe_load(base_rule_body)
    except Exception as e:
        logger.error(f"error: {e}")
        logger.error("Failed to parse base rule")
        return None, None, True

    return user_config_map, base_rule_map, False

def get_proxies(user_config_map, req):
    pull_proxy_source = user_config_map.get("pull-proxy-source")
    if not pull_proxy_source:
        return None, None, None, True

    proxy_arr = []
    proxy_group_arr = []
    proxy_name_arr = []
    
    # Use ThreadPoolExecutor for concurrent fetching
    with ThreadPoolExecutor(max_workers=len(pull_proxy_source)) as executor:
        future_to_source = {executor.submit(process_proxy_source, source, user_config_map, req): source for source in pull_proxy_source}
        
        for future in as_completed(future_to_source):
            source = future_to_source[future]
            try:
                p_arr, pg_map, pn_arr = future.result()
                if p_arr:
                    proxy_arr.extend(p_arr)
                if pg_map:
                    proxy_group_arr.append(pg_map)
                if pn_arr:
                    proxy_name_arr.extend(pn_arr)
            except Exception as exc:
                logger.error(f'{source.get("name")} generated an exception: {exc}')

    return proxy_arr, proxy_group_arr, proxy_name_arr, False

def process_proxy_source(proxy_source, user_config_map, req):
    url = proxy_source.get("url")
    name = proxy_source.get("name")
    
    content = http_utils.http_get(url)
    if content is None:
        logger.error(f"Request URL: {req.url}, IP: {http_utils.get_request_ip(req)}, Subscription URL: {url}, Failed to fetch subscription")
        return None, None, None
    
    print(f"Got subscription for {name}: {url}")
    
    filter_proxy_name = user_config_map.get("filter-proxy-name", [])
    filter_proxy_server = user_config_map.get("filter-proxy-server", [])
    
    # Try base64 decode first (check if it's base64 content)
    # The Go code logic: if decodeBase64Proxy != nil -> ParseBase64Proxy else ParseYamlProxy
    # Note: parse_utils.get_base64_decode returns None if not valid base64
    
    decoded_content = parse_utils.get_base64_decode(content.decode('utf-8', errors='ignore'))
    
    if decoded_content is None:
        # Not base64, try yaml
        yaml_proxy_arr, err = parse_utils.parse_yaml_proxy(content, filter_proxy_name, filter_proxy_server)
        if err:
             logger.error(f"Request URL: {req.url}, IP: {http_utils.get_request_ip(req)}, Subscription URL: {url}, Failed to parse as base64 or yaml")
             return None, None, None
             
        proxy_group_map, temp_proxy_name_arr = parse_utils.generate_group_and_proxy_name_arr(yaml_proxy_arr, name)
        
        if proxy_group_map.get("proxies"):
             return yaml_proxy_arr, proxy_group_map, temp_proxy_name_arr
        return None, None, None
    
    # Is base64
    base64_proxy_arr, err = parse_utils.parse_base64_proxy(content, filter_proxy_name, filter_proxy_server)
    if err:
        return None, None, None
        
    proxy_group_map, temp_proxy_name_arr = parse_utils.generate_group_and_proxy_name_arr(base64_proxy_arr, name)
    
    if proxy_group_map.get("proxies"):
        return base64_proxy_arr, proxy_group_map, temp_proxy_name_arr
    
    return None, None, None


def output_clash(user_config_map, base_rule_map, proxy_arr, proxy_group_arr, proxy_name_arr):
    output_config = {}
    
    # Simple fields
    for field in ["port", "socks-port", "redir-port", "mixed-port", "allow-lan", "bind-address", "mode", "log-level", "ipv6", "external-controller", "external-ui", "secret", "interface-name"]:
        val = config_utils.get_config_field_value(field, user_config_map, base_rule_map)
        if val is not None:
            output_config[field] = val
            
    # Authentication
    auth = config_utils.get_config_field_value("authentication", user_config_map, base_rule_map)
    if auth:
        output_config["authentication"] = auth
        
    # Hosts & DNS
    hosts = config_utils.get_config_field_value("hosts", user_config_map, base_rule_map)
    if hosts:
        output_config["hosts"] = hosts
        
    dns = config_utils.get_config_field_value("dns", user_config_map, base_rule_map)
    if dns:
        output_config["dns"] = dns
        
    # Rules
    output_config["rules"] = config_utils.get_config_field_merge_value_arr("rules", user_config_map, base_rule_map)
    
    # Rule Providers
    output_config["rule-providers"] = config_utils.get_config_field_merge_value_map("rule-providers", user_config_map, base_rule_map)
    
    # Proxy Providers
    output_config["proxy-providers"] = config_utils.get_config_field_merge_value_map("proxy-providers", user_config_map, base_rule_map)
    
    filter_proxy_provider = user_config_map.get("filter-proxy-providers", [])
    if output_config.get("proxy-providers"):
        for provider_name in list(output_config["proxy-providers"].keys()):
            if provider_name in filter_proxy_provider:
                del output_config["proxy-providers"][provider_name]

    # Proxies
    user_proxies = user_config_map.get("proxies", [])
    output_user_proxies_map = []
    if user_proxies:
        output_user_proxies_map.extend(user_proxies)
        
    output_user_proxies_map.extend(proxy_arr)
    output_config["proxies"] = output_user_proxies_map
    
    # Proxy Groups
    filter_proxy_group = user_config_map.get("filter-proxy-groups", [])
    output_proxy_group_map = []
    
    output_proxy_group_map.extend(proxy_group_arr)
    
    user_config_proxy_groups = user_config_map.get("proxy-groups")
    if user_config_proxy_groups:
        user_config_proxy_group_map_arr = parse_utils.generate_proxy_name_to_group(user_config_proxy_groups, proxy_name_arr, filter_proxy_group)
        output_proxy_group_map.extend(user_config_proxy_group_map_arr)
        
    base_rule_proxy_groups = base_rule_map.get("proxy-groups")
    if base_rule_proxy_groups:
        base_rule_proxy_group_map_arr = parse_utils.generate_proxy_name_to_group(base_rule_proxy_groups, proxy_name_arr, filter_proxy_group)
        
        none_select_group_name = []
        for proxy_group_map in base_rule_proxy_group_map_arr:
            if proxy_group_map.get("type") != "select":
                none_select_group_name.append(proxy_group_map.get("name"))
                
        for idx, proxy_group_map in enumerate(base_rule_proxy_group_map_arr):
            if proxy_group_map.get("type") == "select":
                current_proxies = base_rule_proxy_group_map_arr[idx].get("proxies", [])
                # Prepend none_select_group_name
                new_proxies = list(none_select_group_name)
                new_proxies.extend(current_proxies)
                base_rule_proxy_group_map_arr[idx]["proxies"] = new_proxies
                
        output_proxy_group_map.extend(base_rule_proxy_group_map_arr)
        
    output_config["proxy-groups"] = output_proxy_group_map
    
    # Custom YAML dumper to handle None values as empty or omit them?
    # Standard yaml dump should be fine, but let's make sure it looks good
    return Response(yaml.dump(output_config, allow_unicode=True, sort_keys=False), mimetype='text/yaml')

if __name__ == '__main__':
    port = 6789
    if len(sys.argv) >= 2:
        port = int(sys.argv[1])
        
    print(f"Service started, port: {port}")
    print("parse service started")
    app.run(host='0.0.0.0', port=port)
