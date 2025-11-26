import requests

def http_get(url):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Error fetching URL {url}: {e}")
        return None

def get_request_ip(request):
    if not request:
        return ""
    
    forwarded = request.headers.get("X-FORWARDED-FOR")
    if forwarded:
        return forwarded
    
    return request.remote_addr
