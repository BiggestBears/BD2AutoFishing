import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTextEdit, QLabel, QTabWidget, 
                             QGroupBox, QFormLayout, QDoubleSpinBox, QMessageBox,
                             QApplication)
from PyQt6.QtCore import pyqtSlot, Qt
from PyQt6.QtGui import QIcon, QTextCursor, QColor

from utils.config_manager import ConfigManager
from core.bot_logic import FishingBot
from gui.roi_selector import ROISelector
from gui.hsv_tuner import HSVTuner
from gui.resource_manager import ResourceManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BrownDust II Auto Fishing System v2.0")
        self.resize(600, 500)
        
        # 1. 初始化核心组件
        self.cfg = ConfigManager()
        self.bot = FishingBot(self.cfg)
        self.roi_selector = None
        self.hsv_tuner = None       # 保持 HSV 窗口引用
        self.current_roi_key = None # 标记当前正在设置哪个 ROI

        # 2. 构建界面
        self.init_ui()

        # 3. 连接信号
        self.connect_signals()

        # 4. 加载初始日志
        self.append_log("本软件完全免费！\n开源地址：https://github.com/BiggestBears/BD2AutoFishing\n如果你是付费购买的，请立即退款并举报商家。")
        self.append_log("----")
        self.append_log("系统就绪。请确认游戏窗口已打开，并配置好 ROI 区域。")

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # === 顶部 Tab 页 ===
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: 运行控制台
        self.tab_console = QWidget()
        self._init_console_tab()
        self.tabs.addTab(self.tab_console, "🎣 运行控制")

        # Tab 2: 参数设置
        self.tab_settings = QWidget()
        self._init_settings_tab()
        self.tabs.addTab(self.tab_settings, "⚙️ 参数设置")

        # === 底部状态栏 ===
        self.status_label = QLabel("就绪")
        self.statusBar().addWidget(self.status_label)

    def _init_console_tab(self):
        layout = QVBoxLayout(self.tab_console)

        # 日志显示区
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: Consolas;")
        layout.addWidget(self.log_text)

        # 按钮区
        btn_layout = QHBoxLayout()
        
        self.btn_toggle = QPushButton("启动挂机")
        self.btn_toggle.setMinimumHeight(40)
        self.btn_toggle.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
        self.btn_toggle.clicked.connect(self.toggle_bot)

        btn_layout.addWidget(self.btn_toggle)
        layout.addLayout(btn_layout)

    def _init_settings_tab(self):
        layout = QVBoxLayout(self.tab_settings)

        # --- ROI 设置 ---
        group_roi = QGroupBox("区域检测 (ROI)")
        roi_layout = QVBoxLayout()
        
        # 1. 小游戏区域
        self.lbl_roi_minigame = QLabel("🎮 小游戏: " + str(self.cfg.get('rois', 'minigame')))
        roi_layout.addWidget(self.lbl_roi_minigame)
        
        self.btn_set_roi_game = QPushButton("🎯 设置小游戏区域")
        self.btn_set_roi_game.clicked.connect(lambda: self.open_roi_selector('minigame'))
        roi_layout.addWidget(self.btn_set_roi_game)

        # 2. 咬钩区域
        self.lbl_roi_bite = QLabel("🎣 咬钩点: " + str(self.cfg.get('rois', 'bite') or "全屏"))
        roi_layout.addWidget(self.lbl_roi_bite)

        self.btn_set_roi_bite = QPushButton("🎯 设置咬钩检测区域")
        self.btn_set_roi_bite.clicked.connect(lambda: self.open_roi_selector('bite'))
        roi_layout.addWidget(self.btn_set_roi_bite)

        # 3. 提示信息区域 (新增)
        self.lbl_roi_msg = QLabel("💬 提示信息 (背包/位置): " + str(self.cfg.get('rois', 'msg_tips') or "全屏"))
        roi_layout.addWidget(self.lbl_roi_msg)

        self.btn_set_roi_msg = QPushButton("🎯 设置提示信息区域")
        self.btn_set_roi_msg.setToolTip("框选屏幕上会出现【背包已满】或【位置错误】文字的区域")
        self.btn_set_roi_msg.clicked.connect(lambda: self.open_roi_selector('msg_tips'))
        roi_layout.addWidget(self.btn_set_roi_msg)
        
        group_roi.setLayout(roi_layout)
        layout.addWidget(group_roi)

        # --- 游戏参数 ---
        group_params = QGroupBox("游戏参数微调")
        form_layout = QFormLayout()
        
        self.spin_cast = QDoubleSpinBox()
        self.spin_cast.setRange(0.1, 2.0)
        self.spin_cast.setSingleStep(0.1)
        self.spin_cast.setValue(self.cfg.get('game_params', 'cast_duration', 0.5))
        form_layout.addRow("抛竿蓄力 (秒):", self.spin_cast)

        self.spin_conf = QDoubleSpinBox()
        self.spin_conf.setRange(0.1, 1.0)
        self.spin_conf.setSingleStep(0.05)
        self.spin_conf.setValue(self.cfg.get('game_params', 'confidence_common', 0.8))
        form_layout.addRow("图像识别置信度:", self.spin_conf)
        
        group_params.setLayout(form_layout)
        layout.addWidget(group_params)

        # --- 颜色校准 ---
        group_color = QGroupBox("视觉识别校准")
        color_layout = QVBoxLayout()
        
        self.btn_tune_yellow = QPushButton("🎨 校准黄色命中区域")
        self.btn_tune_yellow.setToolTip("弹出可视化的颜色阈值调节窗口")
        self.btn_tune_yellow.clicked.connect(lambda: self.open_hsv_tuner('yellow'))
        color_layout.addWidget(self.btn_tune_yellow)
        
        group_color.setLayout(color_layout)
        layout.addWidget(group_color)

        # --- 资源管理 ---
        group_resources = QGroupBox("资源文件管理")
        resource_layout = QVBoxLayout()

        self.btn_replace_templates = QPushButton("📁 替换模板图片")
        self.btn_replace_templates.setToolTip("选择新的模板图片文件来替换resources/images/templates/中的文件")
        self.btn_replace_templates.clicked.connect(self.open_template_replacer)
        resource_layout.addWidget(self.btn_replace_templates)

        self.lbl_resource_info = QLabel("点击上方按钮可替换识别用的模板图片文件")
        self.lbl_resource_info.setStyleSheet("color: #666666; font-size: 11px;")
        resource_layout.addWidget(self.lbl_resource_info)

        group_resources.setLayout(resource_layout)
        layout.addWidget(group_resources)

        # --- 保存按钮 ---
        self.btn_save = QPushButton("💾 保存配置")
        self.btn_save.clicked.connect(self.save_settings)
        layout.addWidget(self.btn_save)
        
        layout.addStretch() # 顶上去

    def connect_signals(self):
        # Bot 信号
        self.bot.log_signal.connect(self.append_log)
        self.bot.status_signal.connect(self.update_status_label)
        self.bot.finished.connect(self.on_bot_finished)

    # ================= 槽函数 (Slots) =================

    def open_hsv_tuner(self, color_key):
        """打开颜色调校窗口"""
        # 检查是否配置了 ROI，因为截图依赖它
        if not self.cfg.get('rois', 'minigame'):
            QMessageBox.warning(self, "警告", "请先配置【小游戏区域】，否则无法截取样本图片！")
            return

        # 创建并显示窗口 (必须保存为成员变量 self.hsv_tuner，否则会被垃圾回收)
        self.hsv_tuner = HSVTuner(self.cfg, color_key)
        self.hsv_tuner.show()

    def open_roi_selector(self, key):
        """打开 ROI 选择器，并记录当前正在设置的 key"""
        self.current_roi_key = key
        current_roi = self.cfg.get('rois', key)
        
        self.roi_selector = ROISelector(current_roi)
        self.roi_selector.roi_confirmed.connect(self.on_roi_selected)
        self.roi_selector.show()
        self.append_log(f"正在设置区域: {key} ...")

    @pyqtSlot(list)
    def on_roi_selected(self, roi):
        if self.current_roi_key:
            self.cfg.set('rois', self.current_roi_key, roi)
            
            # 更新对应的 Label 显示
            if self.current_roi_key == 'minigame':
                self.lbl_roi_minigame.setText(f"🎮 小游戏: {roi} (未保存)")
            elif self.current_roi_key == 'bite':
                self.lbl_roi_bite.setText(f"🎣 咬钩点: {roi} (未保存)")
            elif self.current_roi_key == 'msg_tips':
                self.lbl_roi_msg.setText(f"💬 提示信息: {roi} (未保存)")
                
            self.append_log(f"[{self.current_roi_key}] 区域已更新，请点击保存。")

    @pyqtSlot()
    def save_settings(self):
        # 更新参数到内存
        self.cfg.set('game_params', 'cast_duration', self.spin_cast.value())
        self.cfg.set('game_params', 'confidence_common', self.spin_conf.value())
        
        # 写入文件
        self.cfg.save_config()
        self.append_log("✅ 配置已保存到 settings.json")
        
        # 刷新 Label 移除 (未保存) 字样
        self.lbl_roi_minigame.setText(f"🎮 小游戏: {self.cfg.get('rois', 'minigame')}")
        self.lbl_roi_bite.setText(f"🎣 咬钩点: {self.cfg.get('rois', 'bite')}")
        self.lbl_roi_msg.setText(f"💬 提示信息: {self.cfg.get('rois', 'msg_tips')}")

    @pyqtSlot()
    def toggle_bot(self):
        if not self.bot.isRunning():
            # 启动逻辑
            self.bot.start()
            self.btn_toggle.setText("停止运行")
            self.btn_toggle.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold;")
            self.status_label.setText("正在运行...")
        else:
            # 停止逻辑
            self.bot.stop()
            self.btn_toggle.setEnabled(False) # 防止重复点击，等待线程结束
            self.status_label.setText("正在停止...")

    @pyqtSlot(str)
    def append_log(self, msg):
        self.log_text.append(msg)
        # 自动滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)

    def open_template_replacer(self):
        """打开资源模板替换器"""
        try:
            self.resource_manager = ResourceManager(self, self.bot)
            self.resource_manager.show()
            self.append_log("📁 打开资源文件管理器")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开资源管理器失败：\n{e}")
            self.append_log(f"❌ 打开资源管理器失败: {e}")

    @pyqtSlot(str)
    def update_status_label(self, status):
        self.status_label.setText(status)

    @pyqtSlot()
    def on_bot_finished(self):
        self.btn_toggle.setText("启动挂机")
        self.btn_toggle.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
        self.btn_toggle.setEnabled(True)
        self.status_label.setText("已停止")
        self.append_log("--- 脚本已结束 ---")