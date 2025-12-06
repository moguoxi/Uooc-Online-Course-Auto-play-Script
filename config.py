# config.py

# --- 浏览器配置 ---
CHROME_DEBUG_PORT = 9222

# --- 导航过滤 ---
KEYWORDS_SKIP = ["课前学习", "附件", "测试", "测验", "考试", "点击下方继续学习"]

# ==========================================
# ⏱️ 全局时间参数配置 (单位: 秒)
# ==========================================

# 1. 运行生命周期
WATCHDOG_TIMEOUT = 300.0    
FORCE_REFRESH_INTERVAL = 1800.0

# 2. 视频监控与防暂停
NAV_CHECK_INTERVAL = 10.0   
INJECT_INTERVAL = 3.0       
HEARTBEAT_INTERVAL = 30     
PAGE_LOAD_WAIT = 1.0        # 【修改】极速模式，仅等待1秒

# 3. 答题逻辑
QUIZ_COOLDOWN = 5.0         
QUIZ_CHECK_RETRIES = 5      
DOM_WAIT = 0.5              
DOM_CLICK_WAIT = 0.3