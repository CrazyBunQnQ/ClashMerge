from flask import Blueprint, request
import logging

from services import parser_service

logger = logging.getLogger(__name__)

parse_bp = Blueprint("parse", __name__)

@parse_bp.route("/parse")
def parse_rule():
    user_config_map, base_rule_map, done = parser_service.parse_request_params(request)
    if done:
        return "解析请求参数失败", 400
    proxy_arr, proxy_group_arr, proxy_name_arr, done2 = parser_service.get_proxies(user_config_map, request)
    if done2:
        return "获取代理信息失败", 500
    return parser_service.output_clash(user_config_map, base_rule_map, proxy_arr or [], proxy_group_arr or [], proxy_name_arr or [])
