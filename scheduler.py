import os
import json
import schedule
import time
import threading
import requests
import logging
import subprocess
import platform
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import random
from datetime import datetime
import hashlib

class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False

any_typ = AnyType("*")

class DailyPromptScheduler:
    def __init__(self):
        self.node_dir = os.path.dirname(os.path.abspath(__file__))
        self.prompt_dir = os.path.join(self.node_dir, "Prompt")
        
        # Ensure Prompt folder exists
        if not os.path.exists(self.prompt_dir):
            os.makedirs(self.prompt_dir)
            
    def get_txt_files(self):
        """Get all txt files in the Prompt folder"""
        if not os.path.exists(self.prompt_dir):
            return ["Please place txt files in Prompt folder"]
        
        # Only get .txt files, exclude .json files
        txt_files = [f for f in os.listdir(self.prompt_dir) 
                    if f.endswith('.txt') and not f.endswith('_time_seed.json')]
        if not txt_files:
            return ["Please place txt files in Prompt folder"]
        
        return txt_files
    
    def get_seed_file_path(self, txt_filename):
        """Get the seed file path for specific txt file"""
        # Remove .txt extension and add _time_seed.json
        base_name = os.path.splitext(txt_filename)[0]
        seed_filename = f"{base_name}_time_seed.json"
        return os.path.join(self.prompt_dir, seed_filename)
    
    def load_time_seed(self, txt_filename):
        """Load time seed for specific txt file"""
        seed_file = self.get_seed_file_path(txt_filename)
        if os.path.exists(seed_file):
            try:
                with open(seed_file, 'r', encoding='utf-8') as f:
                    seed_data = json.load(f)
                    return seed_data.get('seed_date', None)
            except:
                return None
        return None
    
    def save_time_seed(self, txt_filename, seed_date):
        """Save time seed for specific txt file"""
        seed_file = self.get_seed_file_path(txt_filename)
        seed_data = {'seed_date': seed_date}
        with open(seed_file, 'w', encoding='utf-8') as f:
            json.dump(seed_data, f, ensure_ascii=False)
    
    @classmethod
    def INPUT_TYPES(cls):
        instance = cls()
        txt_files = instance.get_txt_files()
        
        return {
            "required": {
                "txt_file": (txt_files, {"default": txt_files[0] if txt_files else ""}),
                "daily_count": ("INT", {
                    "default": 3,
                    "min": 1,
                    "max": 5000,
                    "step": 1
                }),
                "scheduled": ("BOOLEAN", {
                    "default": False,
                    "label_on": "Set Time Seed",
                    "label_off": "Random Mode"
                }),
            }
        }
    
    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("daily_prompts", "total_index")
    OUTPUT_IS_LIST = (True, False)
    FUNCTION = "get_daily_prompts"
    CATEGORY = "text/scheduled"
    
    def IS_CHANGED(self, txt_file, daily_count, scheduled):
        """Ensure node is not cached"""
        current_time = datetime.now()
        current_date = current_time.strftime("%Y%m%d")
        
        # If file doesn't exist, return current timestamp
        txt_path = os.path.join(self.prompt_dir, txt_file)
        if not os.path.exists(txt_path):
            return str(current_time.timestamp())
        
        # Combine file modification time, current date and settings to generate identifier
        try:
            file_mtime = os.path.getmtime(txt_path)
            unique_id = f"{file_mtime}_{current_date}_{daily_count}_{scheduled}_{txt_file}"
            return hashlib.md5(unique_id.encode()).hexdigest()
        except:
            return str(current_time.timestamp())
    
    def read_txt_file(self, filename):
        """Read and parse txt file"""
        txt_path = os.path.join(self.prompt_dir, filename)
        
        if not os.path.exists(txt_path):
            return []
        
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by newlines, filter empty lines
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            return lines
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return []
    
    def get_daily_prompts(self, txt_file, daily_count, scheduled):
        # Check if file exists
        if txt_file == "Please place txt files in Prompt folder":
            return (["Error: Please place txt files in Prompt folder"], 0)
        
        # Read prompt list
        all_prompts = self.read_txt_file(txt_file)
        
        if not all_prompts:
            error_msg = f"Error: Unable to read file {txt_file} or file is empty"
            return ([error_msg], 0)
        
        current_time = datetime.now()
        current_date = current_time.strftime("%Y%m%d")
        
        # Ensure not exceeding available prompts count
        actual_count = min(daily_count, len(all_prompts))
        
        # Handle scheduling logic
        if scheduled:
            # Scheduled mode with time seed
            seed_date = self.load_time_seed(txt_file)
            
            if seed_date is None:
                # First time setting seed
                self.save_time_seed(txt_file, current_date)
                seed_date = current_date
                status = f"Time seed set: {seed_date} for {txt_file}"
            else:
                status = f"Using time seed: {seed_date} for {txt_file}"
            
            # Calculate days difference from seed date
            try:
                seed_datetime = datetime.strptime(seed_date, "%Y%m%d")
                current_datetime = datetime.strptime(current_date, "%Y%m%d")
                days_diff = (current_datetime - seed_datetime).days
            except:
                days_diff = 0
            
            # Calculate starting index for sequential selection
            total_prompts = len(all_prompts)
            start_index = (days_diff * actual_count) % total_prompts
            
            # Sequential selection with wrapping
            selected_prompts = []
            for i in range(actual_count):
                index = (start_index + i) % total_prompts
                selected_prompts.append(all_prompts[index])
            
        else:
            # Random mode: use different random seed each day
            random_seed = int(current_date) + hash(txt_file)
            random.seed(random_seed)
            status = f"Random mode - Date seed: {current_date} for {txt_file}"
            
            # Randomly select prompts without replacement
            selected_prompts = random.sample(all_prompts, actual_count)
        
        # Output debug information
        logger.info(f"DailyPromptScheduler: {status}")
        logger.info(f"DailyPromptScheduler: Selected {actual_count} from {len(all_prompts)} prompts")
        logger.info(f"DailyPromptScheduler: Selected prompts: {selected_prompts}")
        
        return (selected_prompts, actual_count)


class TimeToSeedList:
    """
    Generate random seed list based on current time
    """
    
    def __init__(self):
        self.last_execution_time = None
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "count": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 100000,
                    "step": 1,
                    "display": "number"
                }),
            }
        }
    
    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("seed_list",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "generate_seed_list"
    CATEGORY = "utils"
    
    @classmethod
    def IS_CHANGED(cls, count):
        """
        Method used by ComfyUI to determine if node needs re-execution
        Always return different value to force re-execution
        """
        now = datetime.now()
        # Use timestamp to ensure re-calculation every execution
        timestamp = now.strftime("%Y%m%d%H%M%S%f")
        return timestamp
    
    def generate_seed_list(self, count):
        """
        Generate random seed list based on current time
        
        Args:
            count (int): Number of random seeds to generate
            
        Returns:
            tuple: Tuple containing random seed list
        """
        try:
            # Get current time
            now = datetime.now()
            
            # Convert to numeric format (HHMMSS)
            time_seed = int(now.strftime("%H%M%S"))
            
            # Record execution time
            self.last_execution_time = now.strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
            
            # Use time as random seed
            random.seed(time_seed)
            
            # Generate random seed list
            seed_list = []
            for i in range(count):
                # Generate random number between 0 and 4294967295 (32-bit unsigned int max)
                seed = random.randint(0, 4294967295)
                seed_list.append(seed)
            
            logger.info(f"TimeToSeedList: Execution time={self.last_execution_time}, Time seed={time_seed}, Generated {count} random seeds")
            
            return (seed_list,)
            
        except Exception as e:
            logger.error(f"TimeToSeedList generation failed: {e}")
            # Return default value
            return ([42] * count,)

class ShutdownNode:
    """
    Shutdown node - shuts down computer when workflow completes
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "trigger": (any_typ, {"forceInput": True}),
                "delay_seconds": ("INT", {
                    "default": 5,
                    "min": 0,
                    "max": 300,
                    "step": 1,
                    "display": "number"
                }),
                "force_shutdown": ("BOOLEAN", {
                    "default": False,
                    "label_on": "Force Shutdown",
                    "label_off": "Normal Shutdown"
                }),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status",)
    FUNCTION = "shutdown_computer"
    CATEGORY = "system/shutdown"
    
    def shutdown_computer(self, trigger, delay_seconds, force_shutdown):
        """
        Shutdown computer with specified delay
        
        Args:
            trigger: Any input to trigger shutdown (can be any type)
            delay_seconds (int): Delay before shutdown in seconds
            force_shutdown (bool): Whether to force shutdown without saving
            
        Returns:
            tuple: Status message
        """
        try:
            system = platform.system().lower()
            
            if delay_seconds > 0:
                logger.info(f"Shutdown scheduled in {delay_seconds} seconds...")
                time.sleep(delay_seconds)
            
            if system == "windows":
                # Windows shutdown command
                if force_shutdown:
                    cmd = ["shutdown", "/s", "/f", "/t", "0"]
                else:
                    cmd = ["shutdown", "/s", "/t", "0"]
                
                logger.info("Executing Windows shutdown command...")
                subprocess.run(cmd, check=True)
                
            elif system == "linux" or system == "darwin":  # Linux or macOS
                # Unix-like systems shutdown command
                if force_shutdown:
                    cmd = ["sudo", "shutdown", "-h", "now"]
                else:
                    cmd = ["shutdown", "-h", "now"]
                
                logger.info("Executing Unix shutdown command...")
                subprocess.run(cmd, check=True)
                
            else:
                error_msg = f"Unsupported operating system: {system}"
                logger.error(error_msg)
                return (error_msg,)
            
            success_msg = f"Shutdown command executed successfully (System: {system}, Delay: {delay_seconds}s, Force: {force_shutdown})"
            logger.info(success_msg)
            return (success_msg,)
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Shutdown command failed: {e}"
            logger.error(error_msg)
            return (error_msg,)
        except Exception as e:
            error_msg = f"Unexpected error during shutdown: {e}"
            logger.error(error_msg)
            return (error_msg,)

class SchedulerManager:
    def __init__(self):
        self.running = False
        self.thread = None
        self.base_dir = os.path.dirname(__file__)
        self.workflow_dir = os.path.join(self.base_dir, "Workflow")
        self.config_file = os.path.join(self.base_dir, "schedules.json")
        self.comfyui_url = "http://127.0.0.1:8188"
        self.global_enabled = False
        
        # 確保工作流資料夾存在
        os.makedirs(self.workflow_dir, exist_ok=True)
        
        # 自動啟動
        self.load_and_start()
        
    def load_and_start(self):
        """Load settings and auto-start"""
        config = self.load_config()
        schedules = config.get('schedules', [])
        self.global_enabled = config.get('globalEnabled', False)
        
        if schedules and self.global_enabled:
            self.setup_schedules(schedules)
            self.start()
            active_count = len([s for s in schedules if s.get('enabled', False)])
            logger.info(f"Auto-loaded {active_count}/{len(schedules)} active schedules and started service")
        else:
            logger.info("Scheduler service disabled or no active schedules")
    
    def get_workflows(self):
        """Get all json files in Workflow folder"""
        workflows = []
        try:
            if os.path.exists(self.workflow_dir):
                for filename in os.listdir(self.workflow_dir):
                    if filename.endswith('.json'):
                        name = filename.replace('.json', '')
                        workflows.append({
                            'name': name,
                            'filename': filename
                        })
        except Exception as e:
            logger.error(f"Failed to scan workflow folder: {e}")
        
        return workflows
    
    def load_config(self):
        """Load complete settings from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
        return {}
    
    def load_schedules(self):
        """Load schedule settings from file (for compatibility)"""
        config = self.load_config()
        return config.get('schedules', [])
    
    def save_schedules(self, schedules, global_enabled=None):
        """Save schedule settings"""
        try:
            # Update global_enabled if provided
            if global_enabled is not None:
                self.global_enabled = global_enabled
            
            # Prepare data for saving
            data = {
                'schedules': schedules,
                'globalEnabled': self.global_enabled,
                'updated_at': datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Reconfigure schedules
            if self.global_enabled:
                self.setup_schedules(schedules)
                # Start service if not running and has enabled schedules
                if not self.running and any(s.get('enabled', False) for s in schedules):
                    self.start()
            else:
                # Stop all schedules if globally disabled
                self.stop()
            
            active_count = len([s for s in schedules if s.get('enabled', False)]) if self.global_enabled else 0
            logger.info(f"Settings saved - Global status: {'Enabled' if self.global_enabled else 'Disabled'}, Active schedules: {active_count}/{len(schedules)}")
            return True
        except Exception as e:
            logger.error(f"Failed to save schedule settings: {e}")
            return False
    
    def load_workflow_json(self, filename):
        """Load workflow JSON file"""
        try:
            filepath = os.path.join(self.workflow_dir, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load workflow file {filename}: {e}")
        return None
    
    def execute_workflow(self, workflow_filename):
        """Execute workflow using HTTP POST"""
        # Check global switch
        if not self.global_enabled:
            logger.warning(f"Scheduler system disabled, skipping workflow execution: {workflow_filename}")
            return False
            
        try:
            # Load workflow JSON
            workflow_data = self.load_workflow_json(workflow_filename)
            if not workflow_data:
                logger.error(f"Cannot load workflow: {workflow_filename}")
                return False
            
            # Prepare ComfyUI API request
            payload = {
                "prompt": workflow_data,
                "client_id": "scheduled_task"
            }
            
            # Send HTTP POST request
            response = requests.post(
                f"{self.comfyui_url}/prompt",
                json=payload,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                prompt_id = result.get('prompt_id', 'unknown')
                logger.info(f"✅ Successfully executed workflow: {workflow_filename} (ID: {prompt_id})")
                return True
            else:
                logger.error(f"❌ Failed to execute workflow: {workflow_filename} (Status: {response.status_code})")
                return False
                
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Cannot connect to ComfyUI service ({self.comfyui_url})")
            return False
        except Exception as e:
            logger.error(f"❌ Error occurred while executing workflow: {e}")
            return False
    
    def create_job(self, schedule_item):
        """Create scheduled task"""
        def job():
            # Check global switch and individual enable status again
            if not self.global_enabled:
                logger.warning(f"Scheduler system disabled, skipping task: {schedule_item['workflow']}")
                return
                
            if not schedule_item.get('enabled', False):
                logger.info(f"Schedule disabled, skipping task: {schedule_item['workflow']}")
                return
                
            logger.info(f"🕒 Executing schedule: {schedule_item['time']} - {schedule_item['workflow']}")
            self.execute_workflow(schedule_item['workflow'])
        
        schedule.every().day.at(schedule_item['time']).do(job)
        logger.info(f"📅 Schedule set: Daily at {schedule_item['time']} execute {schedule_item['workflow']} (Enabled: {schedule_item.get('enabled', False)})")
    
    def setup_schedules(self, schedules):
        """Setup all scheduled tasks"""
        schedule.clear()  # Clear existing schedules
        
        if not self.global_enabled:
            logger.info("Scheduler system disabled, no schedules will be set")
            return
        
        active_schedules = 0
        for item in schedules:
            if item.get('time') and item.get('workflow'):
                self.create_job(item)
                if item.get('enabled', False):
                    active_schedules += 1
        
        logger.info(f"📋 Set up {len(schedules)} scheduled tasks, {active_schedules} are enabled")
    
    def run_loop(self):
        """Schedule execution loop"""
        logger.info("🚀 Scheduler service started")
        while self.running:
            try:
                if self.global_enabled:
                    schedule.run_pending()
                else:
                    logger.debug("Scheduler system disabled, skipping execution check")
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Schedule execution error: {e}")
                time.sleep(60)
        logger.info("⏹️ Scheduler service stopped")
    
    def start(self):
        """Start scheduler service"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run_loop, daemon=True)
            self.thread.start()
            return True
        return False
    
    def stop(self):
        """Stop scheduler service"""
        if self.running:
            self.running = False
            schedule.clear()
            logger.info("Scheduler service stopped, all schedules cleared")
            return True
        return False
    
    def get_status(self):
        """Get service status"""
        config = self.load_config()
        schedules = config.get('schedules', [])
        enabled_count = len([s for s in schedules if s.get('enabled', False)])
        
        return {
            'running': self.running,
            'globalEnabled': self.global_enabled,
            'schedule_count': len(schedule.jobs),
            'total_schedules': len(schedules),
            'enabled_schedules': enabled_count,
            'next_run': str(schedule.next_run()) if schedule.jobs else None
        }