from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizeGrip
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint
from PyQt6.QtGui import QColor, QPalette, QCursor

class ROISelector(QWidget):
    """
    可视化区域选择器
    特点：无边框、半透明、可拖拽、可缩放
    """
    roi_confirmed = pyqtSignal(list)  # 信号：发送 [x, y, w, h]

    def __init__(self, default_rect=None):
        super().__init__()
        
        # 1. 窗口属性设置
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 2. 设置初始位置和大小
        if default_rect and len(default_rect) == 4:
            self.setGeometry(*default_rect)
        else:
            self.setGeometry(100, 100, 400, 100)
            
        # 3. UI 布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # 背景容器 (用于显示边框和半透明色)
        self.container = QWidget(self)
        self.container.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 255, 0, 40);
                border: 2px solid #00FF00;
            }
            QLabel {
                color: #00FF00;
                font-weight: bold;
                background-color: rgba(0, 0, 0, 150);
                padding: 4px;
                border: none;
            }
        """)
        self.layout.addWidget(self.container)
        
        # 内部布局
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # 提示标签
        self.lbl_info = QLabel("【拖拽】移动位置  【右下角】调整大小\n【双击】保存区域  【ESC】取消")
        self.lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.lbl_info, 0, Qt.AlignmentFlag.AlignCenter)
        
        # 右下角缩放手柄
        # 注意：在Frameless模式下，需要手动添加QSizeGrip才能缩放
        self.grip = QSizeGrip(self.container)
        # 将手柄固定在右下角
        container_layout.addWidget(self.grip, 0, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)

        # 拖拽相关变量
        self.old_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def mouseDoubleClickEvent(self, event):
        """双击确认选择"""
        if event.button() == Qt.MouseButton.LeftButton:
            rect = self.geometry()
            # 转换为 [x, y, w, h] 格式
            final_roi = [rect.x(), rect.y(), rect.width(), rect.height()]
            print(f"[ROI Selector] Selected: {final_roi}")
            self.roi_confirmed.emit(final_roi)
            self.close()

    def keyPressEvent(self, event):
        """ESC 取消"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()