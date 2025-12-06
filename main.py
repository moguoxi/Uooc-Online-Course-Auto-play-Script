# main.py (答题安全 + 交替保活版)
import time
import os
import logging
import datetime
import sys
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.errors import ElementLostError

from config import (
    CHROME_DEBUG_PORT, 
    NAV_CHECK_INTERVAL, WATCHDOG_TIMEOUT, INJECT_INTERVAL, 
    PAGE_LOAD_WAIT, FORCE_REFRESH_INTERVAL
)
from answer_logic import QuizSolver 
from navigator_logic import get_navigation_action

# --- 日志配置 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
current_time_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_FILE = os.path.join(LOG_DIR, f"monitor_{current_time_str}.txt")

class DualLogger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout  
        self.log = open(filename, "a", encoding="utf-8") 
    def write(self, message):
        self.terminal.write(message) 
        self.log.write(message)      
        self.log.flush()            
    def flush(self):
        self.terminal.flush()
        self.log.flush()

sys.stdout = DualLogger(LOG_FILE)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S', handlers=[logging.StreamHandler(sys.stdout)])

def log_main(msg):
    logging.info(msg)

# --- 防暂停 JS ---
ANTI_PAUSE_JS = """
(function() {
    if (window.__anti_ts && (Date.now() - window.__anti_ts < 5000)) return;
    window.__anti_ts = Date.now();
    Object.defineProperty(document, 'hidden', {value: false, writable: true});
    Object.defineProperty(document, 'visibilityState', {value: 'visible', writable: true});
    var vids = document.getElementsByTagName('video');
    for(var i=0; i<vids.length; i++) {
        var vid = vids[i];
        if(vid.paused && !vid.ended) { vid.play().catch(()=>{}); }
        vid.muted = true;
    }
})();
"""

def keep_alive_action(tab):
    try:
        tab.run_js(ANTI_PAUSE_JS)
        for frame in tab.eles('tag:iframe'):
            try: frame.run_js(ANTI_PAUSE_JS)
            except: pass
    except: pass

def check_video_status(tab):
    try:
        btn = tab.ele('.vjs-big-play-button', timeout=0.1)
        if btn and btn.states.is_displayed: return True
        poster = tab.ele('.vjs-poster-ad', timeout=0.1)
        if poster and "display: block" in (poster.attr("style") or ""): return True
    except: pass
    return False

def get_browser():
    co = ChromiumOptions().set_local_port(CHROME_DEBUG_PORT)
    try: return ChromiumPage(co)
    except Exception as e:
        log_main(f"❌ 浏览器连接失败: {e}")
        return None

def is_valid_quiz(tab):
    try:
        ele = tab.ele('css:div.layui-layer #quizLayer', timeout=0.1)
        if not ele or not ele.states.is_displayed: return False
        hint = ele.ele('xpath:.//*[contains(text(), "正确答案")]', timeout=0.1)
        if hint and hint.states.is_displayed: return False
        return True
    except: return False

def safe_scan_and_click(tab):
    """安全点击逻辑"""
    MAX_RETRIES = 6
    for i in range(MAX_RETRIES):
        try:
            nav_needed, target, desc = get_navigation_action(tab, quiet=True)
            if not nav_needed or not target:
                return False, False, desc
            
            op_type = "EXPAND" if "展开" in desc else "ENTER"
            prefix = "📂 [展开]" if op_type == "EXPAND" else "🚀 [进入]"
            
            log_main(f"{prefix} {desc}")
            target.click()
            return True, (op_type == "EXPAND"), desc
        except (ElementLostError, Exception) as e:
            if i == MAX_RETRIES - 1:
                log_main(f"❌ 操作最终失败: {e}")
            else:
                time.sleep(1.0) 
            continue
    return False, False, None

# ============================
# 🚀 主程序 (状态机)
# ============================

def main():
    print("===========================================")
    print(f"   优课全自动挂机脚本 (答题安全 + 交替保活) ")
    print("===========================================")
    
    page = get_browser()
    if not page: return
    tab = page.latest_tab
    log_main(f"✅ 已接管页面: {tab.title}")
    
    # 状态: "SCAN", "SWITCH", "WATCH", "QUIZ_MODE"
    current_state = "SCAN"
    
    last_force_refresh = time.time()
    last_action_time = time.time()
    
    # 答题安全期计时器
    last_quiz_end_time = 0 
    QUIZ_SAFETY_BUFFER = 5.0 
    
    solver = None
    last_op_was_expand = False 

    try:
        while True:
            current_ts = time.time()
            
            # --- 0. 全局守护: 强制刷新 ---
            if current_ts - last_force_refresh > FORCE_REFRESH_INTERVAL:
                log_main("🔄 [维护] 强制刷新页面...")
                tab.refresh()
                time.sleep(PAGE_LOAD_WAIT)
                last_force_refresh = current_ts
                current_state = "SCAN"
                continue

            # --- 1. 全局守护: 答题检测 (最高优先级) ---
            if current_state != "QUIZ_MODE" and is_valid_quiz(tab):
                log_main("🚨 检测到答题框，进入答题安全模式...")
                current_state = "QUIZ_MODE"
                last_quiz_end_time = time.time()
                continue

            # ========================================================
            # 🔴 状态: QUIZ_MODE (答题与安全缓冲)
            # ========================================================
            if current_state == "QUIZ_MODE":
                # A. 还有题目？ -> 答题
                if is_valid_quiz(tab):
                    if not solver: solver = QuizSolver(); solver.page=page; solver.tab=tab
                    solver.run()
                    last_quiz_end_time = time.time()
                    log_main(f"⏸️ 答题结束，进入 {QUIZ_SAFETY_BUFFER}s 安全观察期...")
                
                # B. 没题目了，检查是否过了安全期
                elif time.time() - last_quiz_end_time > QUIZ_SAFETY_BUFFER:
                    log_main("✅ 安全期结束 (无新题)，恢复挂机。")
                    current_state = "SCAN"
                    last_action_time = time.time()
                
                # C. 没题目，但在安全期内 -> 等待
                else:
                    time.sleep(0.5)

            # ========================================================
            # 🟢 状态: SCAN
            # ========================================================
            elif current_state == "SCAN":
                success, is_expand, desc = safe_scan_and_click(tab)
                
                if success:
                    last_op_was_expand = is_expand
                    current_state = "SWITCH"
                elif desc and "正在播放" in desc:
                    log_main(f"▶️ [状态:校验] 初始即为视频页 -> 进入挂机")
                    current_state = "WATCH"
                else:
                    time.sleep(2) 

            # ========================================================
            # 🟡 状态: SWITCH
            # ========================================================
            elif current_state == "SWITCH":
                log_main(f"⏳ 等待加载 ({PAGE_LOAD_WAIT}s)...")
                time.sleep(PAGE_LOAD_WAIT)
                
                if last_op_was_expand:
                    log_main("⏩ [分流] 目录已展开，继续扫描...")
                    current_state = "SCAN"
                    continue

                log_main("🔍 正在核验当前页面类型...")
                nav_needed, target, desc = get_navigation_action(tab, quiet=True)
                
                if not nav_needed and desc and "正在播放" in desc:
                    log_main("✅ [核验通过] 确认为视频页面")
                    log_main("⚡ 执行启动脚本 (Keep-Alive x3)...")
                    for i in range(3):
                        keep_alive_action(tab)
                        try: tab.actions.move_to((960, 450)).click()
                        except: pass
                        time.sleep(0.5)
                    
                    last_action_time = time.time()
                    current_state = "WATCH"
                    log_main("✅ 视频已启动，进入保活监控模式")
                else:
                    log_main("⏩ [核验跳过] 非视频页面，继续扫描...")
                    current_state = "SCAN"

            # ========================================================
            # 🔵 状态: WATCH (严格交替版)
            # ========================================================
            elif current_state == "WATCH":
                
                # --- 步骤 1: 视频保活 ---
                if check_video_status(tab):
                    log_main("⚠️ 检测到视频暂停，正在尝试点击恢复...")
                    try: tab.actions.move_to((960, 450)).click()
                    except: pass
                
                keep_alive_action(tab)
                
                # 间隔 (2秒)
                time.sleep(2)

                # --- 步骤 2: 检测是否完成 (每轮必查) ---
                # 这里不使用 NAV_CHECK_INTERVAL，而是强制交替执行
                nav_needed, target, desc = get_navigation_action(tab, quiet=True)
                
                if nav_needed:
                    log_main(f"✅ 当前视频完成，准备切换 -> {desc}")
                    current_state = "SCAN"
                else:
                    status_desc = desc if desc else "播放中"
                    if "正在播放: " in status_desc:
                        status_desc = status_desc.replace("正在播放: ", "")
                    log_main(f"▶️ 监控中 | {status_desc} | 视频状态正常")
                    
                    last_action_time = time.time() # 刷新防卡死时间
                    
                    # 间隔 (2秒)
                    time.sleep(2)

            # --- 卡死检测 ---
            # 排除 QUIZ_MODE，因为答题可能需要很久
            if current_state != "QUIZ_MODE" and (current_ts - last_action_time > WATCHDOG_TIMEOUT):
                log_main("💤 [监控] 长时间无有效操作，重置...")
                tab.refresh()
                time.sleep(PAGE_LOAD_WAIT)
                last_action_time = current_ts
                current_state = "SCAN"

    except KeyboardInterrupt:
        log_main("🛑 用户停止脚本。")
        input("按回车退出...")
        sys.exit(0)
    except Exception as e:
        log_main(f"⚠️ 发生错误: {e}")
        input("按回车退出...")
        sys.exit(1)

if __name__ == '__main__':
    main()