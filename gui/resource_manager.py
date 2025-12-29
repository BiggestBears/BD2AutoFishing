import os
import sys
import shutil
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QListWidget, QLabel, QFileDialog, QMessageBox,
                             QProgressBar, QTextEdit, QGroupBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap


class ResourceManager(QDialog):
    def __init__(self, parent=None, bot=None):
        super().__init__(parent)
        self.setWindowTitle("资源文件管理器")
        self.setModal(True)
        self.resize(600, 500)

        self.bot = bot

        self.resource_dir = self.get_resource_path()
        self.templates_dir = os.path.join(self.resource_dir, "images", "templates")

        self.init_ui()
        self.load_template_files()

    def get_resource_path(self):
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        resource_path = os.path.join(base_path, "resources")

        if not os.path.exists(resource_path):
            exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else base_path
            resource_path = os.path.join(exe_dir, "resources")

        return resource_path

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 标题和说明
        title_label = QLabel("📁 资源文件管理器")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)

        info_label = QLabel(f"资源目录: {self.resource_dir}")
        info_label.setStyleSheet("color: #666666; font-size: 11px;")
        layout.addWidget(info_label)

        # 文件列表组
        group_files = QGroupBox("模板图片文件")
        files_layout = QVBoxLayout(group_files)

        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.on_file_selected)
        files_layout.addWidget(self.file_list)

        # 按钮区域
        btn_layout = QHBoxLayout()

        self.btn_replace = QPushButton("🔄 替换选中文件")
        self.btn_replace.setEnabled(False)
        self.btn_replace.clicked.connect(self.replace_selected_file)
        btn_layout.addWidget(self.btn_replace)

        self.btn_add = QPushButton("➕ 添加新文件")
        self.btn_add.clicked.connect(self.add_new_file)
        btn_layout.addWidget(self.btn_add)

        self.btn_delete = QPushButton("🗑️ 删除文件")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self.delete_selected_file)
        btn_layout.addWidget(self.btn_delete)

        self.btn_reload = QPushButton("🔄 重新加载模板")
        self.btn_reload.setToolTip("重新加载所有模板图片到内存中")
        self.btn_reload.clicked.connect(self.reload_templates)
        btn_layout.addWidget(self.btn_reload)

        files_layout.addLayout(btn_layout)
        layout.addWidget(group_files)

        # 预览区域
        group_preview = QGroupBox("文件预览")
        preview_layout = QVBoxLayout(group_preview)

        self.preview_label = QLabel("选择文件查看预览")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(150)
        self.preview_label.setStyleSheet("border: 1px solid #ccc; background-color: #f5f5f5;")
        preview_layout.addWidget(self.preview_label)

        layout.addWidget(group_preview)

        # 日志区域
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(100)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background-color: #f0f0f0; font-family: Consolas;")
        layout.addWidget(self.log_text)

        # 底部按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.btn_close = QPushButton("关闭")
        self.btn_close.clicked.connect(self.close)
        bottom_layout.addWidget(self.btn_close)

        layout.addLayout(bottom_layout)

    def load_template_files(self):
        """加载模板文件列表"""
        self.file_list.clear()

        if not os.path.exists(self.templates_dir):
            self.log("⚠️ 模板目录不存在，将尝试创建...")
            try:
                os.makedirs(self.templates_dir, exist_ok=True)
                self.log("✅ 模板目录创建成功")
            except Exception as e:
                self.log(f"❌ 创建模板目录失败: {e}")
                return

        try:
            files = os.listdir(self.templates_dir)
            image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]

            for file in sorted(image_files):
                self.file_list.addItem(file)

            self.log(f"📄 找到 {len(image_files)} 个模板文件")

        except Exception as e:
            self.log(f"❌ 读取模板目录失败: {e}")

    def on_file_selected(self, item):
        """文件被选中时的处理"""
        if not item:
            return

        self.btn_replace.setEnabled(True)
        self.btn_delete.setEnabled(True)

        # 显示预览
        file_path = os.path.join(self.templates_dir, item.text())
        self.show_preview(file_path)

    def show_preview(self, file_path):
        """显示文件预览"""
        try:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                # 缩放到合适大小
                scaled_pixmap = pixmap.scaled(200, 150, Qt.AspectRatioMode.KeepAspectRatio,
                                             Qt.TransformationMode.SmoothTransformation)
                self.preview_label.setPixmap(scaled_pixmap)

                # 显示文件信息
                file_info = f"{os.path.basename(file_path)}\n大小: {pixmap.width()}x{pixmap.height()}"
                self.preview_label.setToolTip(file_info)
            else:
                self.preview_label.setText("无法预览此文件")
                self.preview_label.setPixmap(QPixmap())
        except Exception as e:
            self.preview_label.setText(f"预览错误: {e}")
            self.preview_label.setPixmap(QPixmap())

    def replace_selected_file(self):
        """替换选中的文件"""
        current_item = self.file_list.currentItem()
        if not current_item:
            return

        current_file = current_item.text()
        target_path = os.path.join(self.templates_dir, current_file)

        # 打开文件选择对话框
        source_file, _ = QFileDialog.getOpenFileName(
            self,
            f"选择替换 {current_file} 的新文件",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp);;所有文件 (*)"
        )

        if source_file:
            try:
                # 备份原文件
                backup_path = target_path + ".backup"
                if os.path.exists(target_path):
                    shutil.copy2(target_path, backup_path)
                    self.log(f"📋 已备份原文件: {current_file}.backup")

                # 复制新文件
                shutil.copy2(source_file, target_path)
                self.log(f"✅ 成功替换文件: {current_file}")

                # 刷新预览
                self.show_preview(target_path)

                QMessageBox.information(self, "成功", f"文件 {current_file} 已成功替换！")

            except Exception as e:
                self.log(f"❌ 替换文件失败: {e}")
                QMessageBox.critical(self, "错误", f"替换文件失败：\n{e}")

    def add_new_file(self):
        """添加新文件"""
        source_file, _ = QFileDialog.getOpenFileName(
            self,
            "选择要添加的图片文件",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp);;所有文件 (*)"
        )

        if source_file:
            # 获取文件名
            filename = os.path.basename(source_file)
            target_path = os.path.join(self.templates_dir, filename)

            # 检查是否已存在
            if os.path.exists(target_path):
                reply = QMessageBox.question(
                    self, "文件已存在",
                    f"文件 {filename} 已存在，是否覆盖？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

            try:
                shutil.copy2(source_file, target_path)
                self.log(f"✅ 成功添加文件: {filename}")

                # 刷新列表
                self.load_template_files()

                QMessageBox.information(self, "成功", f"文件 {filename} 已成功添加！")

            except Exception as e:
                self.log(f"❌ 添加文件失败: {e}")
                QMessageBox.critical(self, "错误", f"添加文件失败：\n{e}")

    def delete_selected_file(self):
        """删除选中的文件"""
        current_item = self.file_list.currentItem()
        if not current_item:
            return

        current_file = current_item.text()
        target_path = os.path.join(self.templates_dir, current_file)

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除文件 {current_file} 吗？\n此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(target_path)
                self.log(f"🗑️ 已删除文件: {current_file}")

                # 刷新列表和预览
                self.load_template_files()
                self.preview_label.clear()
                self.preview_label.setText("选择文件查看预览")
                self.btn_replace.setEnabled(False)
                self.btn_delete.setEnabled(False)

                QMessageBox.information(self, "成功", f"文件 {current_file} 已删除！")

            except Exception as e:
                self.log(f"❌ 删除文件失败: {e}")
                QMessageBox.critical(self, "错误", f"删除文件失败：\n{e}")

    def log(self, message):
        """添加日志消息"""
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def reload_templates(self):
        """重新加载所有模板图片到内存"""
        try:
            if self.bot and hasattr(self.bot, 'vision'):
                self.bot.vision.reload_templates()
                self.log("🔄 模板图片已重新加载到内存")
                QMessageBox.information(self, "成功", "模板图片已重新加载！\n新的模板将在下次识别时生效。")
            else:
                self.log("⚠️ 无法重新加载模板：未找到vision实例")
                QMessageBox.warning(self, "警告", "无法重新加载模板：未找到vision实例")
        except Exception as e:
            self.log(f"❌ 重新加载模板失败: {e}")
            QMessageBox.critical(self, "错误", f"重新加载模板失败：\n{e}")
