import time
import random
import cv2
import numpy as np
import pydirectinput
import win32gui
import win32con
from PyQt6.QtCore import QThread, pyqtSignal

from core.vision import Vision
from utils.config_manager import ConfigManager

class FishingBot(QThread):
    # 信号定义：用于通知 GUI 更新
    log_signal = pyqtSignal(str)      # 日志消息
    status_signal = pyqtSignal(str)   # 状态变更 (e.g. "运行中", "暂停")
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.cfg = config_manager
        self.vision = Vision(config_manager)
        
        # 运行控制标志
        self.is_running = False
        
        # 优化输入延迟
        # 极速模式：降低底层输入库的默认延迟
        pydirectinput.PAUSE = 0.001
        
    def log(self, message):
        """发送日志信号"""
        self.log_signal.emit(message)

    def stop(self):
        """外部停止指令"""
        self.is_running = False
        self.log("🛑 正在停止脚本...")

    def activate_window(self):
        """尝试激活游戏窗口"""
        title = self.cfg.get("window_title", default="BrownDust II")
        hwnd = win32gui.FindWindow(None, title)
        if hwnd:
            try:
                # 如果最小化了，先还原
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                
                # 尝试置顶
                # 注意：Windows 限制应用抢占焦点，有时需要 Alt 键辅助或多次尝试
                try:
                    win32gui.SetForegroundWindow(hwnd)
                except Exception:
                    # 如果常规置顶失败，尝试用 shell 方式
                    pydirectinput.press('alt')
                    win32gui.SetForegroundWindow(hwnd)
                
                time.sleep(0.5) # 给窗口动画一点时间
                return True
            except Exception as e:
                self.log(f"❌ 窗口激活失败: {e}")
        return False

    # ================= 🎭 拟人化动作 =================

    def _random_sleep(self, base_time, variance_key='reaction_delay'):
        """
        拟人化延迟
        :param base_time: 基础时间 (秒)
        :param variance_key: 配置文件中的拟人化参数键名
        """
        human_cfg = self.cfg.get('humanization')
        
        # 如果关闭了随机延迟，直接 sleep
        if not human_cfg.get('enable_random_delay', True):
            time.sleep(base_time)
            return

        # 获取波动范围
        jitter = 0.0
        if variance_key == 'reaction_delay':
            # 反应时间波动
            mn = human_cfg.get('reaction_delay_min', 0.05)
            mx = human_cfg.get('reaction_delay_max', 0.15)
            jitter = random.uniform(mn, mx)
        elif variance_key == 'cast':
            # 抛竿时间波动 (百分比)
            var = human_cfg.get('cast_variance', 0.1)
            jitter = random.uniform(-var, var) * base_time
            
        final_time = max(0, base_time + jitter)
        time.sleep(final_time)

    def _human_press(self, key, duration=None):
        """拟人化按键"""
        if duration is None:
            # 快速点击，但也有一点点持续时间
            duration = random.uniform(0.05, 0.1)
        
        pydirectinput.keyDown(key)
        time.sleep(duration)
        pydirectinput.keyUp(key)

    def _human_click(self, point):
        """拟人化鼠标点击"""
        if not point: return
        
        offset = self.cfg.get('humanization', 'click_offset_pixels', 5)
        
        # 生成高斯分布的随机偏移，这样点击点会集中在中心，但也偶尔会偏一点
        dx = int(random.gauss(0, offset/2))
        dy = int(random.gauss(0, offset/2))
        
        # 限制最大偏移，防止点歪太远
        dx = max(-offset, min(offset, dx))
        dy = max(-offset, min(offset, dy))
        
        target_x = point[0] + dx
        target_y = point[1] + dy
        
        pydirectinput.click(target_x, target_y)

    # ================= 🎮 核心业务逻辑 =================

    def play_minigame(self, region):
        """小游戏循环 (高性能模式)"""
        self.log("🎮 进入小游戏模式")
        
        # 缓存参数，避免循环内频繁读取字典
        game_params = self.cfg.get('game_params')
        hit_cooldown = game_params.get('hit_cooldown', 0.02)
        timeout = game_params.get('cursor_timeout', 1.0)
        
        y_low, y_high = self.cfg.get_color_bounds('yellow')
        c_low, c_high = self.cfg.get_color_bounds('cursor')
        
        last_hit_time = 0
        cursor_missing_start = 0

        # [性能优化] 预计算 mss 截图区域，避免在循环中重复创建字典，减少 GC 压力
        monitor = {
            "left": int(region[0]),
            "top": int(region[1]),
            "width": int(region[2]),
            "height": int(region[3])
        }
        
        # 极速检测循环 (High Performance Loop)
        while self.is_running:
            # 1. 屏幕捕获 (Direct MSS Call)
            # 直接调用 mss.grab 绕过封装层，减少函数调用开销
            sct_img = self.vision.sct.grab(monitor)
            img_np = np.array(sct_img)
            
            # 2. 色彩空间转换 (BGRA -> BGR -> HSV)
            # 移除透明通道并转换为 HSV 空间，为颜色阈值过滤做准备
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
            img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
            
            # 3. 识别游标
            mask_cursor = cv2.inRange(img_hsv, c_low, c_high)
            contours_c, _ = cv2.findContours(mask_cursor, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            cursor_x = -1
            cursor_w = 0
            
            # 找最大轮廓作为游标
            if contours_c:
                # 使用 max key 快速找到最大轮廓
                max_cnt = max(contours_c, key=cv2.contourArea)
                if cv2.contourArea(max_cnt) > 20:
                    x, y, w, h = cv2.boundingRect(max_cnt)
                    if h > 5: # 简单过滤
                        cursor_x = x
                        cursor_w = w

            # === 退出判定: 游标消失超时 ===
            if cursor_x == -1:
                if cursor_missing_start == 0:
                    cursor_missing_start = time.time()
                elif time.time() - cursor_missing_start > timeout:
                    self.log("🏁 小游戏结束 (游标消失)")
                    return
            else:
                cursor_missing_start = 0

            # 4. 命中判定
            now = time.time()
            if cursor_x != -1 and (now - last_hit_time > hit_cooldown):
                mask_yellow = cv2.inRange(img_hsv, y_low, y_high)
                contours_y, _ = cv2.findContours(mask_yellow, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                cursor_center = cursor_x + cursor_w // 2
                
                is_hit = False
                for cnt in contours_y:
                    if cv2.contourArea(cnt) > 20:
                        yx, yy, yw, yh = cv2.boundingRect(cnt)
                        # 判定：游标中心点是否在黄条横坐标范围内
                        if yx <= cursor_center <= yx + yw:
                            is_hit = True
                            break
                
                if is_hit:
                    # 🎯 命中！执行拟人化按键
                    # 计算按压时长：稍微随机一点，0.02s - 0.05s
                    press_duration = random.uniform(0.02, 0.05)
                    self._human_press('space', press_duration)
                    
                    self.log(f"⚡️ HIT! (dur: {press_duration:.3f}s)")
                    last_hit_time = time.time()

            # 极短休眠让出CPU，但不能太长否则掉帧
            # time.sleep(0.001) 

    def handle_selling(self):
        """自动贩卖流程"""
        self.log("🎒 背包已满，尝试清理...")
        self._human_press('t', 0.1)
        time.sleep(2.5) # 等待UI打开
        
        # 步骤列表: (图片key, 描述, 延迟)
        steps = [
            ('btn_sell_mode', "点击贩卖模式", 1.0),
            ('btn_select_all', "点击全选", 0.5),
            ('btn_check', "点击确认选择", 1.0),
            ('btn_confirm', "确认贩卖", 2.0)
        ]
        
        for key, desc, delay in steps:
            if not self.is_running: return False
            
            loc = self.vision.find_template(key)
            if loc:
                self.log(f"   -> {desc}")
                self._human_click(loc)
                time.sleep(delay)
            else:
                if key == 'btn_sell_mode':
                    self.log("❌ 未找到贩卖按钮，可能在错误的界面")
                    self._human_press('esc')
                    return False
                # 后续步骤没找到可能是不需要点（比如全选已经是全选状态），继续尝试
        
        # 退出背包
        self._human_press('esc')
        time.sleep(1.5)
        self.log("✅ 清理完成")
        return True

    def run(self):
        """工作线程主入口"""
        # 1. 在子线程内部初始化 mss
        self.vision.init_manager()
        
        self.is_running = True
        self.status_signal.emit("运行中")
        
        # 2. 强制激活游戏窗口 (解决焦点在脚本导致误触停止的问题)
        if not self.activate_window():
            self.log("❌ 未找到游戏窗口！请确保游戏已启动。")
            self.status_signal.emit("启动失败")
            self.vision.release()
            return

        self.log("🚀 自动化系统已启动")
        
        waiting_for_game = False
        
        try:
            while self.is_running:
                # 1. 异常检测 (结算界面、错误提示)
                # 使用灰度匹配加快速度
                if self.vision.find_template('result', confidence=0.7, grayscale=True):
                    self.log("💰 检测到结算画面")
                    self._human_press('esc')
                    time.sleep(2.0)
                    waiting_for_game = False
                    continue

                # 优先使用配置的提示信息区域
                msg_roi = self.cfg.get('rois', 'msg_tips')

                if self.vision.find_template('pos_error', region=msg_roi, confidence=0.7):
                    self.log("⚠️ 位置错误，尝试修正...")
                    self._human_press('s', 0.3) # 后退一步
                    time.sleep(1.0)
                    waiting_for_game = False
                    continue
                
                # 2. 背包满检测
                if self.vision.find_template('full_warning', region=msg_roi, confidence=0.75):
                    if not self.handle_selling():
                        # 贩卖失败，停止脚本保护现场
                        self.log("❌ 无法清理背包，脚本停止")
                        self.stop()
                        self.status_signal.emit("异常停止")
                        break
                    waiting_for_game = False
                    continue

                # 3. 咬钩检测
                # 咬钩图标通常颜色鲜艳，用彩色匹配
                # 优先使用配置的局部区域，提高速度和抗干扰能力
                bite_roi = self.cfg.get('rois', 'bite')
                if self.vision.find_template('bite', region=bite_roi):
                    self.log("🎣 咬钩！拉杆！")
                    self._human_press('space')
                    
                    # 获取小游戏区域 (从配置读取)
                    roi = self.cfg.get('rois', 'minigame')
                    if roi:
                        self.play_minigame(roi)
                    else:
                        self.log("❌ 未配置小游戏区域 ROI")
                    
                    waiting_for_game = True
                    continue

                # 4. 抛竿检测
                # 只有在还没进入“等待上钩”状态时才抛竿
                # 或者如果等太久了(waiting_for_game逻辑需要在外面加个超时重置，这里简化处理)
                if self.vision.find_template('cast', confidence=0.7, grayscale=True):
                    # 如果之前在等鱼，说明鱼脱钩了或者上一轮结束了，重置状态
                    if waiting_for_game:
                        waiting_for_game = False
                    
                    self.log("🌊 抛竿...")
                    
                    # 蓄力抛竿
                    cast_duration = self.cfg.get('game_params', 'cast_duration', 0.5)
                    self._human_press('space', duration=cast_duration)
                    
                    # 抛竿后会有动画，休息一下
                    time.sleep(2.0)
                    continue

                # 没什么事发生，稍微休息，降低CPU占用
                time.sleep(0.1)

        except Exception as e:
            self.log(f"❌ 发生未捕获异常: {e}")
            time.sleep(1)
        finally:
            # 关键：无论如何退出（包括报错），都释放 mss 资源
            # 防止下次启动时出现 '_thread._local' object has no attribute 'srcdc'
            self.vision.release()
            self.status_signal.emit("已停止")
            self.log("🛑 脚本已结束 (资源已释放)")
