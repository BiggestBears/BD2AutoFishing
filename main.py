import sys
import traceback
from PyQt6.QtWidgets import QApplication

# 确保能找到包
sys.path.append(".")

from gui.main_window import MainWindow

def main():
    # 高分屏适配 (High DPI Scaling)
    try:
        from PyQt6.QtCore import Qt
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except Exception:
        pass

    app = QApplication(sys.argv)
    
    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
        
    except Exception as e:
        # 严重错误捕获，防止直接闪退看不到报错
        print("❌ 致命错误:")
        traceback.print_exc()
        input("按 Enter 键退出...")

if __name__ == "__main__":
    main()