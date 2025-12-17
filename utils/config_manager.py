import json
import os
import numpy as np

class ConfigManager:
    def __init__(self, config_path="config/settings.json"):
        self.config_path = config_path
        self.config = {}
        self.load_config()

    def load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件未找到: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except json.JSONDecodeError as e:
            print(f"配置文件格式错误: {e}")
            self.config = {}

    def save_config(self):
        """保存当前配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            print("配置已保存")
        except Exception as e:
            print(f"保存配置失败: {e}")

    def get(self, section, key=None, default=None):
        """
        获取配置项
        :param section: 一级键 (e.g., 'game_params')
        :param key: 二级键 (e.g., 'cast_duration'), 如果为None则返回整个section
        :param default: 默认值
        """
        sec_data = self.config.get(section, {})
        if key is None:
            return sec_data
        return sec_data.get(key, default)

    def set(self, section, key, value):
        """更新配置项"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value

    def get_color_bounds(self, color_name):
        """
        获取颜色的HSV阈值，并自动转换为 numpy array
        :param color_name: e.g., 'yellow' -> 读取 'yellow_lower' 和 'yellow_upper'
        :return: (lower_np, upper_np)
        """
        colors = self.config.get('colors', {})
        lower = colors.get(f"{color_name}_lower")
        upper = colors.get(f"{color_name}_upper")
        
        if lower and upper:
            return (
                np.array(lower, dtype=np.uint8),
                np.array(upper, dtype=np.uint8)
            )
        return None, None

    def set_color(self, color_name, lower, upper):
        """
        更新颜色阈值
        :param color_name: 'yellow' or 'cursor'
        :param lower: list [h, s, v]
        :param upper: list [h, s, v]
        """
        if 'colors' not in self.config:
            self.config['colors'] = {}
            
        self.config['colors'][f"{color_name}_lower"] = lower
        self.config['colors'][f"{color_name}_upper"] = upper