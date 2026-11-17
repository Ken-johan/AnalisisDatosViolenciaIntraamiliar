"""Utility functions for the project"""
import yaml, os

def load_config():
    cfg_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    if not os.path.exists(cfg_path):
        return {}
    with open(cfg_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
