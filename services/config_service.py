import os
import yaml
import logging

logger = logging.getLogger(__name__)

def _config_dir():
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config"))

def _sanitize_name(name):
    if not name:
        return None
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
    if all(c in allowed for c in name):
        return name
    return None

def _config_path(name):
    n = _sanitize_name(name)
    if not n:
        return None
    base = _config_dir()
    path = os.path.abspath(os.path.join(base, f"{n}.yaml"))
    if not path.startswith(base):
        return None
    return path

def load_config_text(name):
    path = _config_path(name)
    if not path:
        return None, "文件名不合法"
    if not os.path.exists(path):
        return "", None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read(), None
    except Exception as e:
        logger.error(f"读取配置失败: name={name}, 错误={e}")
        return None, "读取配置失败"

def save_config_text(name, content):
    path = _config_path(name)
    if not path:
        return False, "文件名不合法"
    try:
        yaml.safe_load(content)
    except Exception as e:
        return False, "YAML 格式校验失败"
    try:
        os.makedirs(_config_dir(), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True, None
    except Exception as e:
        logger.error(f"保存配置失败: name={name}, 错误={e}")
        return False, "保存配置失败"

