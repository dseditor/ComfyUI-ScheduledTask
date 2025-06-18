"""
ComfyUI-ScheduledTask
簡化版排程任務系統
"""

import os
from .scheduler import SchedulerManager, TimeToSeedList
from .web_handler import setup_routes
import threading
import time

# 全域排程管理器
scheduler_manager = None

def get_scheduler():
    global scheduler_manager
    if scheduler_manager is None:
        scheduler_manager = SchedulerManager()
    return scheduler_manager

# 延遲初始化
def delayed_init():
    time.sleep(3)  # 等待ComfyUI完全啟動
    get_scheduler()

# 啟動初始化執行緒
init_thread = threading.Thread(target=delayed_init, daemon=True)
init_thread.start()

# 設定web路由
setup_routes()

# 清理函數
import atexit
def cleanup():
    global scheduler_manager
    if scheduler_manager:
        scheduler_manager.stop()

atexit.register(cleanup)

# ComfyUI節點映射
NODE_CLASS_MAPPINGS = {
    "TimeToSeedList": TimeToSeedList,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TimeToSeedList": "Time to Seed List",
}

# Web擴展映射 - 這是關鍵！
WEB_DIRECTORY = "./web"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']