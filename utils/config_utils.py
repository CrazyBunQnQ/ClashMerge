import yaml
import os

def load_config(config_path):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error reading config file {config_path}: {e}")
        return None

def get_config_field_value(field_name, user_config_map, base_rule_config_map):
    if user_config_map and field_name in user_config_map:
        return user_config_map[field_name]
    elif base_rule_config_map and field_name in base_rule_config_map:
        return base_rule_config_map[field_name]
    return None

def get_config_field_merge_value_arr(field_name, user_config_map, base_rule_config_map):
    value_slice = []
    if user_config_map and field_name in user_config_map and user_config_map[field_name]:
        value_slice.extend(user_config_map[field_name])
    elif base_rule_config_map and field_name in base_rule_config_map and base_rule_config_map[field_name]:
        value_slice.extend(base_rule_config_map[field_name])
    return value_slice

def get_config_field_merge_value_map(field_name, user_config_map, base_rule_config_map):
    value_map = {}
    if base_rule_config_map and field_name in base_rule_config_map and base_rule_config_map[field_name]:
        value_map.update(base_rule_config_map[field_name])
    
    if user_config_map and field_name in user_config_map and user_config_map[field_name]:
        value_map.update(user_config_map[field_name])
    
    return value_map
