import os
import sys
import yaml
import logging
from flask import Flask

# Add the parent directory to sys.path to allow imports from utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import config_utils
from utils import http_utils
from utils import parse_utils
from routes.parse import parse_bp

app = Flask(__name__)

# Setup logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    datefmt='%Y/%m/%d %H:%M:%S',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'log.txt')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
app.register_blueprint(parse_bp)

if __name__ == '__main__':
    port = 6789
    if len(sys.argv) >= 2:
        port = int(sys.argv[1])
        
    print(f"服务启动，端口: {port}")
    print("规则解析服务已启动")
    app.run(host='0.0.0.0', port=port)
