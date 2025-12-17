import cv2
import numpy as np
import mss
import os
from utils.config_manager import ConfigManager

class Vision:
    def __init__(self, config_manager: ConfigManager):
        self.cfg = config_manager
        self.sct = None # 延迟初始化，避免多线程冲突
        self.templates = {} # 图片缓存
        
        # 预加载所有模板图片
        self._load_all_templates()

    def _get_image_path(self, filename):
        """构建图片绝对路径"""
        base_path = os.getcwd() # 假定在项目根目录运行
        return os.path.join(base_path, "resources", "images", "templates", filename)

    def _load_all_templates(self):
        """加载配置中定义的所有图片到内存"""
        img_dict = self.cfg.get("images")
        if not img_dict:
            return

        for key, filename in img_dict.items():
            path = self._get_image_path(filename)
            if os.path.exists(path):
                #以此模式读取：完整保留颜色，不自动转灰度（某些按钮可能区分颜色）
                img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
                if img is None:
                    print(f"[Vision] 警告: 无法解码图片 {path}")
                    continue
                
                # 如果是透明PNG，去掉Alpha通道，转为BGR，避免匹配出错
                if img.shape[2] == 4:
                    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                
                self.templates[key] = img
            else:
                print(f"[Vision] 错误: 图片文件不存在 {path}")

    def init_manager(self):
        """在工作线程内初始化 mss 实例"""
        if self.sct is None:
            self.sct = mss.mss()

    def capture_screen(self, region=None):
        """
        截取屏幕
        :param region: (x, y, w, h) 或 None (全屏)
        :return: BGR格式的 numpy array
        """
        # 确保已初始化
        if self.sct is None:
            self.init_manager()

        if region:
            monitor = {
                "left": int(region[0]),
                "top": int(region[1]),
                "width": int(region[2]),
                "height": int(region[3])
            }
            img = self.sct.grab(monitor)
        else:
            # 全屏截取 (通常不建议，性能较差)
            img = self.sct.grab(self.sct.monitors[1])
            
        img_np = np.array(img)
        # MSS 返回的是 BGRA，转换为 OpenCV 标准 BGR
        return cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)

    def find_template(self, key, region=None, confidence=None, grayscale=False):
        """
        在屏幕或指定区域寻找模板
        :param key: 模板图片的key (如 'cast', 'bite')
        :param region: 搜索区域 (x, y, w, h)
        :param confidence: 置信度，如果不传则使用配置默认值
        :param grayscale: 是否灰度匹配 (速度快，适合形状匹配)
        :return: (center_x, center_y) or None
        """
        if key not in self.templates:
            return None

        # 1. 获取屏幕截图
        screen = self.capture_screen(region)
        template = self.templates[key]

        # 2. 预处理 (灰度化)
        if grayscale:
            screen = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
            if len(template.shape) == 3:
                template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        # 3. 匹配
        # 如果置信度未指定，根据 key 类型智能选择默认值
        if confidence is None:
            if 'text' in key or 'btn' in key:
                confidence = self.cfg.get('game_params', 'confidence_text', 0.7)
            else:
                confidence = self.cfg.get('game_params', 'confidence_common', 0.8)

        res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        if max_val >= confidence:
            # 计算中心坐标
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            
            # 如果指定了区域，需要把局部坐标转换回全局坐标
            if region:
                center_x += region[0]
                center_y += region[1]
                
            return (int(center_x), int(center_y))
        
        return None

    def detect_color_rect(self, region, color_name):
        """
        在指定区域检测特定颜色的矩形轮廓 (用于小游戏游标识别)
        :return: list of bounding boxes [(x, y, w, h), ...] (相对于 region)
        """
        img = self.capture_screen(region)
        img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        lower, upper = self.cfg.get_color_bounds(color_name)
        if lower is None:
            return []
            
        mask = cv2.inRange(img_hsv, lower, upper)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        results = []
        for cnt in contours:
            if cv2.contourArea(cnt) > 20: # 过滤噪点
                results.append(cv2.boundingRect(cnt))
                
        return results