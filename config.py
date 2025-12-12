# config.py

# --- 浏览器配置 ---
CHROME_DEBUG_PORT = 9222

# --- 导航过滤 ---
KEYWORDS_SKIP = ["课前学习", "附件", "测试", "测验", "考试", "点击下方继续学习"]

# ==========================================
# ⏱️ 全局时间参数配置 (单位: 秒)
# ==========================================

# 1. 运行生命周期
WATCHDOG_TIMEOUT = 300.0    # 监控超时时间    
FORCE_REFRESH_INTERVAL = 600.0  # 每10分钟强制刷新一次页面

# 2. 视频监控与防暂停
NAV_CHECK_INTERVAL = 10.0       # 导航检查间隔
INJECT_INTERVAL = 3.0       # 页面注入间隔
HEARTBEAT_INTERVAL = 30     # 心跳间隔
PAGE_LOAD_WAIT = 1.0        # 【修改】极速模式，仅等待1秒

# 3. 答题逻辑
QUIZ_COOLDOWN = 5.0         # 答题后冷却时间
QUIZ_CHECK_RETRIES = 5      # 答题检查重试次数
DOM_WAIT = 0.5              # DOM 元素加载等待时间
DOM_CLICK_WAIT = 0.3        # DOM 点击后等待时间