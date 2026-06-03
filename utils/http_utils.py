import http.client
import logging
import ssl
from urllib.parse import urlsplit

import requests

logger = logging.getLogger(__name__)


def http_get(url, verify=True, log_error=True, raise_error=False):
    try:
        headers = {
            "User-Agent": "FlClash/v0.8.90 clash-verge"
        }
        response = requests.get(url, headers=headers, timeout=30, verify=verify)
        response.raise_for_status()
        return response.content
    except Exception as e:
        if log_error:
            logger.error(f"请求订阅失败: url={url}, 错误={e}")
        if raise_error:
            raise
        return None


def http_get_preserve_host_case(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc:
        logger.error(f"保留域名大小写请求失败: url={url}, 错误=仅支持 HTTPS URL")
        return None

    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    headers = {
        "User-Agent": "FlClash/v0.8.90 clash-verge",
        "Host": parsed.netloc,
    }
    context = ssl._create_unverified_context()
    connection = http.client.HTTPSConnection(parsed.netloc, timeout=30, context=context)
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        body = response.read()
        if response.status < 200 or response.status >= 300:
            logger.error(f"保留域名大小写请求失败: url={url}, 状态码={response.status}")
            return None
        return body
    except Exception as e:
        logger.error(f"保留域名大小写请求失败: url={url}, 错误={e}")
        return None
    finally:
        connection.close()


def get_request_ip(request):
    if not request:
        return ""
    
    forwarded = request.headers.get("X-FORWARDED-FOR")
    if forwarded:
        return forwarded
    
    return request.remote_addr
