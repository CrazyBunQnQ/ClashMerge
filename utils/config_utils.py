import yaml
import os

# 配置工具函数：读取配置文件并进行字段合并

def load_config(config_path):
    # 读取 YAML 配置文件为字典
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error reading config file {config_path}: {e}")
        return None

def get_config_field_value(field_name, user_config_map, base_rule_config_map):
    # 单值字段：优先使用用户配置，其次基础规则
    if user_config_map and field_name in user_config_map:
        return user_config_map[field_name]
    elif base_rule_config_map and field_name in base_rule_config_map:
        return base_rule_config_map[field_name]
    return None

def get_config_field_merge_value_arr(field_name, user_config_map, base_rule_config_map):
    # 数组字段合并：将用户配置或基础规则中的列表合并（保持顺序）
    value_slice = []
    if user_config_map and field_name in user_config_map and user_config_map[field_name]:
        value_slice.extend(user_config_map[field_name])
    elif base_rule_config_map and field_name in base_rule_config_map and base_rule_config_map[field_name]:
        value_slice.extend(base_rule_config_map[field_name])
    return value_slice

def get_config_field_merge_value_map(field_name, user_config_map, base_rule_config_map):
    # 映射字段合并：以基础规则为底，用户配置覆盖同名键
    value_map = {}
    if base_rule_config_map and field_name in base_rule_config_map and base_rule_config_map[field_name]:
        value_map.update(base_rule_config_map[field_name])
    
    if user_config_map and field_name in user_config_map and user_config_map[field_name]:
        value_map.update(user_config_map[field_name])
    
    return value_map
