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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BrownDust II Auto Fishing System v2.0")
        self.resize(600, 500)
        
        # 1. 初始化核心组件
        self.cfg = ConfigManager()
        self.bot = FishingBot(self.cfg)
        self.roi_selector = None
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
        
        self.btn_start = QPushButton("启动挂机")
        self.btn_start.setMinimumHeight(40)
        self.btn_start.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
        self.btn_start.clicked.connect(self.toggle_bot)
        
        self.btn_stop = QPushButton("停止")
        self.btn_stop.setMinimumHeight(40)
        self.btn_stop.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_bot)

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
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

    @pyqtSlot()
    def toggle_bot(self):
        if not self.bot.isRunning():
            self.bot.start()
            self.btn_start.setText("暂停挂机") # 逻辑上这里可以是暂停，但为了简单先只做启停
            self.btn_start.setEnabled(False) # 暂时禁用，防止重复点
            self.btn_stop.setEnabled(True)
            self.status_label.setText("正在运行...")

    @pyqtSlot()
    def stop_bot(self):
        if self.bot.isRunning():
            self.bot.stop()
            self.btn_stop.setEnabled(False)
            self.status_label.setText("正在停止...")

    @pyqtSlot(str)
    def append_log(self, msg):
        self.log_text.append(msg)
        # 自动滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)

    @pyqtSlot(str)
    def update_status_label(self, status):
        self.status_label.setText(status)

    @pyqtSlot()
    def on_bot_finished(self):
        self.btn_start.setText("启动挂机")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_label.setText("已停止")
        self.append_log("--- 脚本已结束 ---")
