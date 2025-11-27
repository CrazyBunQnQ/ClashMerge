import os
import sys
import yaml
import logging
from flask import Response
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import config_utils
from utils import http_utils
from utils import parse_utils

logger = logging.getLogger(__name__)

def parse_request_params(req):
    config_file_name = req.args.get("name")
    if not config_file_name:
        return None, None, True

    try:
        config_path = os.path.abspath(os.path.join(os.getcwd(), "config", f"{config_file_name}.yaml"))
        if not os.path.exists(config_path):
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", f"{config_file_name}.yaml")
        user_config_map = config_utils.load_config(config_path)
        if user_config_map is None:
            logger.error("读取配置文件失败")
            return None, None, True
    except Exception as e:
        logger.error(f"错误: {e}")
        return None, None, True

    base_config_name = req.args.get("baseName")
    base_config_request_url = ""

    if base_config_name:
        if "base-config" in user_config_map:
            found = False
            for base_config in user_config_map["base-config"]:
                if base_config.get("name") == base_config_name:
                    base_config_request_url = base_config.get("url")
                    logger.info(f"基础配置已选择: 名称={base_config_name}, 地址={base_config_request_url}")
                    found = True
                    break
            if not found:
                logger.error(f"请求URL: {req.url}, IP: {http_utils.get_request_ip(req)}, 基础配置未找到: 名称={base_config_name}")
                return None, None, True
        # 当提供了 baseName 但未能解析到 URL 时，认为错误
        if not base_config_request_url:
            logger.error(f"请求URL: {req.url}, IP: {http_utils.get_request_ip(req)}, 未找到基础规则源")
            return None, None, True
    else:
        logger.info("未提供基础规则名称，使用内置基础规则模板")

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
  ipv6: true

  nameserver:
    - 223.5.5.5
    - 114.114.114.114
    - 119.29.29.29

  fallback:
    - 8.8.8.8
    - 1.1.1.1

  fallback-filter:
    geoip: true
    ipcidr:
      - 240.0.0.0/4
"""

    base_rule_map = None
    if base_config_request_url:
        body_bytes = http_utils.http_get(base_config_request_url)
        if body_bytes is not None:
            try:
                base_rule_map = yaml.safe_load(body_bytes.decode('utf-8', errors='ignore'))
                logger.info(f"使用远程基础规则: 名称={base_config_name}, 地址={base_config_request_url}")
            except Exception as e:
                logger.error(f"解析远程基础规则失败: 错误={e}")
        else:
            logger.error(f"拉取远程基础规则失败: 地址={base_config_request_url}")

    if base_rule_map is None:
        try:
            base_rule_map = yaml.safe_load(base_rule_body)
            logger.info("使用内置基础规则模板进行合并输出")
        except Exception as e:
            logger.error(f"错误: {e}")
            logger.error("解析基础规则失败")
            return None, None, True

    return user_config_map, base_rule_map, False

def get_proxies(user_config_map, req):
    pull_proxy_source = user_config_map.get("pull-proxy-source")
    if not pull_proxy_source:
        return None, None, None, True

    proxy_arr = []
    proxy_group_arr = []
    proxy_name_arr = []

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
                logger.error(f"订阅源异常: 名称={source.get('name')}, 错误={exc}")

    return proxy_arr, proxy_group_arr, proxy_name_arr, False

def process_proxy_source(proxy_source, user_config_map, req):
    url = proxy_source.get("url")
    name = proxy_source.get("name")

    content = http_utils.http_get(url)
    if content is None:
        logger.error(f"请求URL: {req.url}, IP: {http_utils.get_request_ip(req)}, 订阅地址: {url}, 拉取订阅失败")
        return None, None, None

    logger.info(f"订阅拉取成功: 名称={name}, 地址={url}")

    filter_proxy_name = user_config_map.get("filter-proxy-name", [])
    filter_proxy_server = user_config_map.get("filter-proxy-server", [])

    decoded_content = parse_utils.get_base64_decode(content.decode('utf-8', errors='ignore'))

    if decoded_content is None:
        yaml_proxy_arr, err = parse_utils.parse_yaml_proxy(content, filter_proxy_name, filter_proxy_server)
        if err:
            logger.error(f"请求URL: {req.url}, IP: {http_utils.get_request_ip(req)}, 订阅地址: {url}, 解析为 Base64 或 YAML 失败")
            return None, None, None
        proxy_group_map, temp_proxy_name_arr = parse_utils.generate_group_and_proxy_name_arr(yaml_proxy_arr, name)
        if proxy_group_map.get("proxies"):
            return yaml_proxy_arr, proxy_group_map, temp_proxy_name_arr
        return None, None, None

    base64_proxy_arr, err = parse_utils.parse_base64_proxy(content, filter_proxy_name, filter_proxy_server)
    if err:
        return None, None, None
    proxy_group_map, temp_proxy_name_arr = parse_utils.generate_group_and_proxy_name_arr(base64_proxy_arr, name)
    if proxy_group_map.get("proxies"):
        return base64_proxy_arr, proxy_group_map, temp_proxy_name_arr
    return None, None, None

def output_clash(user_config_map, base_rule_map, proxy_arr, proxy_group_arr, proxy_name_arr):
    output_config = {}
    for field in ["port", "socks-port", "redir-port", "mixed-port", "allow-lan", "bind-address", "mode", "log-level", "ipv6", "external-controller", "external-ui", "secret", "interface-name"]:
        val = config_utils.get_config_field_value(field, user_config_map, base_rule_map)
        if val is not None:
            output_config[field] = val
    auth = config_utils.get_config_field_value("authentication", user_config_map, base_rule_map)
    if auth:
        output_config["authentication"] = auth
    hosts = config_utils.get_config_field_value("hosts", user_config_map, base_rule_map)
    if hosts:
        output_config["hosts"] = hosts
    dns = config_utils.get_config_field_value("dns", user_config_map, base_rule_map)
    if dns:
        output_config["dns"] = dns
    output_config["rules"] = config_utils.get_config_field_merge_value_arr("rules", user_config_map, base_rule_map)
    output_config["rule-providers"] = config_utils.get_config_field_merge_value_map("rule-providers", user_config_map, base_rule_map)
    output_config["proxy-providers"] = config_utils.get_config_field_merge_value_map("proxy-providers", user_config_map, base_rule_map)
    filter_proxy_provider = user_config_map.get("filter-proxy-providers", [])
    if output_config.get("proxy-providers"):
        for provider_name in list(output_config["proxy-providers"].keys()):
            if provider_name in filter_proxy_provider:
                del output_config["proxy-providers"][provider_name]
    user_proxies = user_config_map.get("proxies", [])
    output_user_proxies_map = []
    if user_proxies:
        output_user_proxies_map.extend(user_proxies)
    output_user_proxies_map.extend(proxy_arr)
    output_config["proxies"] = output_user_proxies_map
    filter_proxy_group = user_config_map.get("filter-proxy-groups", [])
    output_proxy_group_map = []
    user_config_proxy_groups = user_config_map.get("proxy-groups")
    if user_config_proxy_groups:
        user_config_proxy_group_map_arr = parse_utils.generate_proxy_name_to_group(user_config_proxy_groups, proxy_name_arr, filter_proxy_group)
        output_proxy_group_map.extend(user_config_proxy_group_map_arr)
    def _dedupe_groups(groups):
        name_index = {}
        result = []
        for g in groups:
            name = g.get("name")
            if name not in name_index:
                result.append(g)
                name_index[name] = len(result) - 1
                continue
            idx = name_index[name]
            prev = result[idx]
            if prev.get("type") == g.get("type"):
                p1 = prev.get("proxies", [])
                p2 = g.get("proxies", [])
                if not isinstance(p1, list):
                    p1 = [p1]
                if not isinstance(p2, list):
                    p2 = [p2]
                merged = list(dict.fromkeys(p1 + p2))
                prev["proxies"] = merged
                logger.warning(f"代理组重复: 组名={name}, 已合并代理列表")
            else:
                new_name = name
                while new_name in name_index:
                    new_name += "$"
                g["name"] = new_name
                result.append(g)
                name_index[new_name] = len(result) - 1
                logger.warning(f"代理组重复: 原组名={name}, 类型冲突，已重命名为 {new_name}")
        return result
    output_config["proxy-groups"] = _dedupe_groups(output_proxy_group_map)
    return Response(yaml.dump(output_config, allow_unicode=True, sort_keys=False), mimetype='text/yaml')
