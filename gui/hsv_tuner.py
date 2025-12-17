import cv2
import numpy as np
import mss
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSlider, QPushButton, QGroupBox, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QImage, QPixmap

class HSVTuner(QWidget):
    def __init__(self, config_manager, color_key='yellow'):
        super().__init__()
        self.cfg = config_manager
        self.color_key = color_key
        self.setWindowTitle(f"HSV 颜色调校器 - {color_key}")
        self.resize(800, 600)
        
        # 1. 获取初始截图 (截取 ROI 区域)
        self.roi = self.cfg.get('rois', 'minigame')
        self.original_img = self._capture_roi()
        self.processed_img = None
        
        # 如果截图失败（比如 ROI 没设置），就创建一个黑图防止报错
        if self.original_img is None:
            self.original_img = np.zeros((100, 400, 3), dtype=np.uint8)

        # 2. 读取当前配置的初始值
        lower, upper = self.cfg.get_color_bounds(color_key)
        if lower is None:
            lower = np.array([0, 0, 0])
            upper = np.array([180, 255, 255])
            
        self.init_hsv = (lower, upper)

        # 3. 构建 UI
        self.init_ui()
        
        # 4. 首次渲染
        self.update_preview()

    def _capture_roi(self):
        """截取当前配置的 ROI 区域"""
        if not self.roi:
            return None
            
        with mss.mss() as sct:
            monitor = {
                "left": int(self.roi[0]),
                "top": int(self.roi[1]),
                "width": int(self.roi[2]),
                "height": int(self.roi[3])
            }
            img = sct.grab(monitor)
            img_np = np.array(img)
            # BGRA -> BGR
            return cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # === 顶部：图像预览区 ===
        preview_layout = QHBoxLayout()
        
        # 左侧：原图
        self.lbl_original = QLabel()
        self.lbl_original.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_original.setStyleSheet("border: 1px solid #555; background: #000;")
        self._set_image(self.lbl_original, self.original_img)
        
        # 右侧：二值图 (Mask)
        self.lbl_result = QLabel()
        self.lbl_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_result.setStyleSheet("border: 1px solid #0f0; background: #000;")
        
        preview_layout.addWidget(QLabel("原图:"))
        preview_layout.addWidget(self.lbl_original)
        preview_layout.addWidget(QLabel("识别结果 (白=选中):"))
        preview_layout.addWidget(self.lbl_result)
        
        main_layout.addLayout(preview_layout)

        # === 中部：滑块控制区 ===
        sliders_group = QGroupBox("HSV 阈值调节")
        sliders_layout = QVBoxLayout()
        
        self.sliders = {}
        # H: 0-180, S: 0-255, V: 0-255
        ranges = [('H', 180), ('S', 255), ('V', 255)]
        
        # 下限滑块 (Lower)
        sliders_layout.addWidget(QLabel("--- 下限 (Lower) ---"))
        for i, (name, max_val) in enumerate(ranges):
            row = self._create_slider_row(f"{name} Min", 0, max_val, int(self.init_hsv[0][i]))
            sliders_layout.addLayout(row)
            self.sliders[f"{name}_min"] = row.itemAt(1).widget()

        # 上限滑块 (Upper)
        sliders_layout.addWidget(QLabel("--- 上限 (Upper) ---"))
        for i, (name, max_val) in enumerate(ranges):
            row = self._create_slider_row(f"{name} Max", 0, max_val, int(self.init_hsv[1][i]))
            sliders_layout.addLayout(row)
            self.sliders[f"{name}_max"] = row.itemAt(1).widget()

        sliders_group.setLayout(sliders_layout)
        main_layout.addWidget(sliders_group)

        # === 底部：按钮区 ===
        btn_layout = QHBoxLayout()
        
        self.btn_save = QPushButton("💾 保存应用")
        self.btn_save.setMinimumHeight(40)
        self.btn_save.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
        self.btn_save.clicked.connect(self.save_settings)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        
        main_layout.addLayout(btn_layout)

    def _create_slider_row(self, label, min_val, max_val, init_val):
        layout = QHBoxLayout()
        lbl_name = QLabel(f"{label}:")
        lbl_name.setFixedWidth(60)
        
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(init_val)
        slider.valueChanged.connect(self.update_preview)
        
        lbl_val = QLabel(str(init_val))
        lbl_val.setFixedWidth(40)
        slider.valueChanged.connect(lambda v, l=lbl_val: l.setText(str(v)))
        
        layout.addWidget(lbl_name)
        layout.addWidget(slider)
        layout.addWidget(lbl_val)
        return layout

    def update_preview(self):
        # 1. 获取滑块当前值
        h_min = self.sliders['H_min'].value()
        s_min = self.sliders['S_min'].value()
        v_min = self.sliders['V_min'].value()
        
        h_max = self.sliders['H_max'].value()
        s_max = self.sliders['S_max'].value()
        v_max = self.sliders['V_max'].value()
        
        lower = np.array([h_min, s_min, v_min])
        upper = np.array([h_max, s_max, v_max])
        
        # 2. 图像处理
        hsv = cv2.cvtColor(self.original_img, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower, upper)
        
        # 3. 显示结果 (Mask 是灰度图)
        h, w = mask.shape
        bytes_per_line = w
        q_img = QImage(mask.data, w, h, bytes_per_line, QImage.Format.Format_Grayscale8)
        self.lbl_result.setPixmap(QPixmap.fromImage(q_img))

    def _set_image(self, label, cv_img):
        """将 OpenCV 图像显示到 Label"""
        # BGR -> RGB
        rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_img.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        label.setPixmap(QPixmap.fromImage(q_img))

    def save_settings(self):
        lower = [
            self.sliders['H_min'].value(),
            self.sliders['S_min'].value(),
            self.sliders['V_min'].value()
        ]
        upper = [
            self.sliders['H_max'].value(),
            self.sliders['S_max'].value(),
            self.sliders['V_max'].value()
        ]
        
        self.cfg.set_color(self.color_key, lower, upper)
        self.cfg.save_config()
        QMessageBox.information(self, "成功", f"颜色 [{self.color_key}] 配置已保存！")
        self.close()