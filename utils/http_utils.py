import requests
import logging
logger = logging.getLogger(__name__)

def http_get(url):
    try:
        headers = {
            "User-Agent": "FlClash/v0.8.90 clash-verge"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.error(f"请求订阅失败: url={url}, 错误={e}")
        return None

def get_request_ip(request):
    if not request:
        return ""
    
    forwarded = request.headers.get("X-FORWARDED-FOR")
    if forwarded:
        return forwarded
    
    return request.remote_addr
