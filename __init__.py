"""
ComfyUI-ScheduledTask
簡化版排程任務系統
"""

import os
import threading
import time
import atexit

# 匯入節點類別和排程管理器
from .scheduler import SchedulerManager, TimeToSeedList, DailyPromptScheduler, ShutdownNode

# 匯入web處理器 (如果存在的話)
try:
    from .web_handler import setup_routes
    HAS_WEB_HANDLER = True
except ImportError:
    HAS_WEB_HANDLER = False
    print("Warning: web_handler not found, web interface will be disabled")

# 全域排程管理器
scheduler_manager = None

def get_scheduler():
    global scheduler_manager
    if scheduler_manager is None:
        scheduler_manager = SchedulerManager()
    return scheduler_manager

# 延遲初始化
def delayed_init():
    try:
        time.sleep(3)  # 等待ComfyUI完全啟動
        get_scheduler()
    except Exception as e:
        print(f"Error in delayed initialization: {e}")

# 啟動初始化執行緒
init_thread = threading.Thread(target=delayed_init, daemon=True)
init_thread.start()

# 設定web路由 (如果可用)
if HAS_WEB_HANDLER:
    try:
        setup_routes()
    except Exception as e:
        print(f"Error setting up web routes: {e}")

# 清理函數
def cleanup():
    global scheduler_manager
    if scheduler_manager:
        try:
            scheduler_manager.stop()
        except Exception as e:
            print(f"Error during cleanup: {e}")

atexit.register(cleanup)

# 節點類別映射 - 這是關鍵！
NODE_CLASS_MAPPINGS = {
    "TimeToSeedList": TimeToSeedList,
    "DailyPromptScheduler": DailyPromptScheduler,
    "ShutdownNode": ShutdownNode,
}

# 節點顯示名稱映射
NODE_DISPLAY_NAME_MAPPINGS = {
    "TimeToSeedList": "Time to Seed List",
    "DailyPromptScheduler": "Daily Prompt Scheduler",
    "ShutdownNode": "Shutdown Computer",
}

# Web擴展映射
WEB_DIRECTORY = "./web"

# 確保必要的匯出
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']