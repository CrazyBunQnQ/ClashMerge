import base64
import json
import re
import yaml
import logging
from urllib.parse import urlparse, parse_qs, unquote
logger = logging.getLogger(__name__)

def get_base64_decode(s):
    # 尝试解码 Base64（自动补齐 padding，支持 URL 安全）
    try:
        # Add padding if needed
        padding = 4 - (len(s) % 4)
        if padding != 4:
            s += "=" * padding
        
        # Try standard base64 decoding
        try:
            return base64.b64decode(s, validate=True)
        except:
            pass
            
        # Try URL-safe base64 decoding
        return base64.urlsafe_b64decode(s)
    except Exception as e:
        return None

def parse_base64_proxy(proxy_body, filter_proxy_name, filter_proxy_server):
    try:
        base64_proxy_arr = parse_base64_proxy_arr(proxy_body)
        if base64_proxy_arr is None:
            return None, Exception("订阅代理信息 Base64 解析失败")
        filter_proxy_arr = filter_un_add_proxy_server(base64_proxy_arr, filter_proxy_name, filter_proxy_server)
        return filter_proxy_arr, None
    except Exception as e:
        return None, e

def parse_yaml_proxy(proxy_body, filter_proxy_name, filter_proxy_server):
    # 解析 YAML 订阅并进行过滤
    try:
        try:
            proxy_rule = yaml.safe_load(proxy_body)
        except Exception as e:
            print(f"YAML 解析错误: {e}")
            return None, Exception("订阅代理信息 YAML 解析失败")
            
        if not proxy_rule:
             return None, Exception("订阅代理信息 YAML 解析失败（空内容）")

        proxy_server_arr = []
        if proxy_rule.get("proxies"):
            proxy_server_arr.extend(proxy_rule["proxies"])
        
        if proxy_rule.get("Proxy"):
            proxy_server_arr.extend(proxy_rule["Proxy"])
            
        filter_proxy_arr = filter_un_add_proxy_server(proxy_server_arr, filter_proxy_name, filter_proxy_server)
        return filter_proxy_arr, None
    except Exception as e:
        return None, e

def parse_base64_proxy_arr(base64_proxy_bytes):
    # 将 Base64 订阅文本逐行解析为代理节点
    try:
        base64_proxy_str = base64_proxy_bytes.decode('utf-8')
        proxy_str_arr = base64_proxy_str.split('\n')
        proxy_arr = []
        proxy_name_set = set()
        
        for proxy_str in proxy_str_arr:
            proxy_str = proxy_str.strip()
            if not proxy_str:
                continue
                
            if proxy_str.startswith("vmess://"):
                proxy_str = proxy_str[8:]
                vmess_proxy = get_base64_decode(proxy_str)
                if vmess_proxy:
                    try:
                        vmess_proxy_map = json.loads(vmess_proxy)
                        
                        alert_id = 0
                        if "aid" in vmess_proxy_map:
                            try:
                                alert_id = int(vmess_proxy_map["aid"])
                            except:
                                pass
                        
                        proxy_name = vmess_proxy_map.get("ps", "")
                        while proxy_name in proxy_name_set:
                            proxy_name += "$"
                        proxy_name_set.add(proxy_name)
                        
                        proxy_map = {
                            "name": proxy_name,
                            "type": "vmess",
                            "server": vmess_proxy_map.get("add"),
                            "port": vmess_proxy_map.get("port"),
                            "cipher": "auto",
                            "uuid": vmess_proxy_map.get("id"),
                            "alterId": alert_id,
                            "network": vmess_proxy_map.get("net"),
                            "ws-path": vmess_proxy_map.get("path"),
                        }
                        
                        if vmess_proxy_map.get("tls"):
                            proxy_map["tls"] = True
                            
                        if vmess_proxy_map.get("host"):
                            proxy_map["ws-headers"] = {"Host": vmess_proxy_map["host"]}
                            
                        proxy_arr.append(proxy_map)
                    except Exception as e:
                        print(f"解析 vmess 节点失败: {e}")
                        
            elif proxy_str.startswith("vless://"):
                try:
                    parsed_url = urlparse(proxy_str)
                    query_params = parse_qs(parsed_url.query)
                    
                    proxy_map = {
                        "name": unquote(parsed_url.fragment),
                        "type": "vless",
                        "server": parsed_url.hostname,
                        "port": parsed_url.port,
                        "uuid": parsed_url.username,
                        "udp": True
                    }
                    
                    if "sni" in query_params:
                        proxy_map["sni"] = query_params["sni"][0]
                    
                    if "security" in query_params:
                        proxy_map["tls"] = query_params["security"][0] == "tls"
                        
                    if "fp" in query_params:
                        proxy_map["client-fingerprint"] = query_params["fp"][0]
                        
                    if "flow" in query_params:
                        proxy_map["flow"] = query_params["flow"][0]
                        
                    if "type" in query_params:
                        proxy_map["network"] = query_params["type"][0]
                        
                    if proxy_map.get("network") == "ws":
                        ws_map = {}
                        if "path" in query_params:
                            ws_map["path"] = unquote(query_params["path"][0])
                            
                        if "host" in query_params:
                            ws_map["headers"] = {"host": query_params["host"][0]}
                            
                        if ws_map:
                            proxy_map["ws-opts"] = ws_map
                            
                    proxy_map["tfo"] = False
                    proxy_map["skip-cert-verify"] = False
                    
                    proxy_arr.append(proxy_map)
                except Exception as e:
                    print(f"解析 vless 节点失败: {e}")

            elif proxy_str.startswith("trojan://"):
                try:
                    parsed_url = urlparse(proxy_str)
                    query_params = parse_qs(parsed_url.query)
                    
                    proxy_map = {
                        "name": unquote(parsed_url.fragment),
                        "type": "trojan",
                        "server": parsed_url.hostname,
                        "port": parsed_url.port,
                        "password": parsed_url.username,
                        "udp": True
                    }
                    
                    if "sni" in query_params:
                        proxy_map["sni"] = query_params["sni"][0]
                        
                    proxy_arr.append(proxy_map)
                except Exception as e:
                    print(f"解析 trojan 节点失败: {e}")
                    
            elif proxy_str.startswith("ss://"):
                try:
                    parsed_url = urlparse(proxy_str)
                    user_info = parsed_url.username
                    
                    # Try to decode if it looks like base64 (no colon)
                    if user_info and ':' not in user_info:
                        decoded_user_info = get_base64_decode(user_info)
                        if decoded_user_info:
                            user_info = decoded_user_info.decode('utf-8')
                            
                    if user_info and ':' in user_info:
                        method, password = user_info.split(':', 1)
                        
                        proxy_map = {
                            "name": unquote(parsed_url.fragment),
                            "type": "ss",
                            "server": parsed_url.hostname,
                            "port": parsed_url.port,
                            "password": password,
                            "cipher": method
                        }
                        
                        proxy_arr.append(proxy_map)
                except Exception as e:
                    print(f"解析 ss 节点失败: {e}")
                    
        return proxy_arr
    except Exception as e:
        print(f"解析 Base64 订阅失败: {e}")
        return None

def filter_un_add_proxy_server(proxy_server_arr, filter_proxy_name, filter_proxy_server):
    proxy_arr = []
    
    for proxy in proxy_server_arr:
        should_filter = False
        
        # Filter by name regex
        if filter_proxy_name:
            for filter_name in filter_proxy_name:
                try:
                    if re.search(filter_name, proxy.get("name", "")):
                        logger.info(f"过滤代理名称: 模式={filter_name}, 节点={proxy.get('name','')}")
                        should_filter = True
                        break
                except Exception as e:
                    logger.warning(f"代理名称过滤正则无效: 模式={filter_name}, 错误={e}")
        
        if should_filter:
            continue
            
        # Filter by server address
        if filter_proxy_server:
            for server in filter_proxy_server:
                if server == proxy.get("server"):
                    logger.info(f"过滤代理服务器: server={server}, 节点={proxy.get('name','')}")
                    should_filter = True
                    break
        
        if should_filter:
            continue
            
        proxy_arr.append(proxy)
        
    return proxy_arr

def generate_group_and_proxy_name_arr(proxy_server_arr, proxy_source_name):
    temp_proxy_name_arr = []
    for proxy in proxy_server_arr:
        temp_proxy_name_arr.append(proxy.get("name"))
        
    proxy_group_map = {
        "name": proxy_source_name,
        "type": "select",
        "proxies": temp_proxy_name_arr
    }
    
    return proxy_group_map, temp_proxy_name_arr

def generate_proxy_name_to_group(proxy_groups, proxy_name_arr, filter_proxy_group_arr):
    output_proxy_group_map = []
    
    for proxy_group in proxy_groups:
        should_filter = False
        if filter_proxy_group_arr:
            for filter_name in filter_proxy_group_arr:
                if filter_name == proxy_group.get("name"):
                    logger.info(f"过滤代理组: 组名={proxy_group.get('name','')}")
                    should_filter = True
                    break
        
        if should_filter:
            continue
            
        # Create a copy to modify
        new_proxy_group = proxy_group.copy()
        
        if "use" not in new_proxy_group:
            proxies = new_proxy_group.get("proxies")
            if proxies is None:
                proxies = []
            if not isinstance(proxies, list):
                proxies = [proxies]

            static_names = []
            regex_list = []
            for item in proxies:
                if isinstance(item, dict) and "regex" in item:
                    pattern = item.get("regex")
                    if isinstance(pattern, str) and pattern:
                        try:
                            regex_list.append(re.compile(pattern))
                        except Exception as e:
                            logger.warning(f"代理组正则无效: 组名={new_proxy_group.get('name','')}, 模式={pattern}, 错误={e}")
                elif isinstance(item, str):
                    static_names.append(item)

            matched = []
            if regex_list:
                for name in proxy_name_arr:
                    for rgx in regex_list:
                        try:
                            if rgx.search(name):
                                matched.append(name)
                                break
                        except Exception as e:
                            logger.warning(f"代理组正则匹配异常: 组名={new_proxy_group.get('name','')}, 错误={e}")
            else:
                matched = list(proxy_name_arr)

            result = []
            seen = set()
            for n in static_names + matched:
                if n not in seen:
                    seen.add(n)
                    result.append(n)

            new_proxy_group["proxies"] = result
                
        output_proxy_group_map.append(new_proxy_group)
        
    return output_proxy_group_map
