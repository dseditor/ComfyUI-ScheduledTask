from aiohttp import web
import json
import logging

logger = logging.getLogger(__name__)

def setup_routes():
    """Setup simplified web routes"""
    try:
        import server
        from . import get_scheduler
        
        @server.PromptServer.instance.routes.get("/scheduledtask/get_workflows")
        async def get_workflows(request):
            """Get workflow list"""
            try:
                scheduler = get_scheduler()
                workflows = scheduler.get_workflows()
                return web.json_response({'workflows': workflows})
            except Exception as e:
                logger.error(f"Failed to get workflow list: {e}")
                return web.json_response({'error': str(e)}, status=500)
        
        @server.PromptServer.instance.routes.get("/scheduledtask/get_schedules")
        async def get_schedules(request):
            """Get schedule settings"""
            try:
                scheduler = get_scheduler()
                config = scheduler.load_config()
                return web.json_response({
                    'schedules': config.get('schedules', []),
                    'globalEnabled': config.get('globalEnabled', False)
                })
            except Exception as e:
                logger.error(f"Failed to get schedule settings: {e}")
                return web.json_response({'error': str(e)}, status=500)
        
        @server.PromptServer.instance.routes.post("/scheduledtask/save_schedules")
        async def save_schedules(request):
            """Save schedule settings"""
            try:
                data = await request.json()
                schedules = data.get('schedules', [])
                global_enabled = data.get('globalEnabled', False)
                
                scheduler = get_scheduler()
                success = scheduler.save_schedules(schedules, global_enabled)
                
                if success:
                    return web.json_response({
                        'status': 'success',
                        'message': f"Saved {len(schedules)} schedule settings, Global status: {'Enabled' if global_enabled else 'Disabled'}"
                    })
                else:
                    return web.json_response({'error': 'Save failed'}, status=500)
            except Exception as e:
                logger.error(f"Failed to save schedule settings: {e}")
                return web.json_response({'error': str(e)}, status=500)
        
        @server.PromptServer.instance.routes.get("/scheduledtask/status")
        async def get_status(request):
            """Get service status"""
            try:
                scheduler = get_scheduler()
                status = scheduler.get_status()
                return web.json_response(status)
            except Exception as e:
                logger.error(f"Failed to get status: {e}")
                return web.json_response({'error': str(e)}, status=500)
        
        @server.PromptServer.instance.routes.post("/scheduledtask/toggle_global")
        async def toggle_global(request):
            """Toggle global switch"""
            try:
                data = await request.json()
                enabled = data.get('enabled', False)
                
                scheduler = get_scheduler()
                schedules = scheduler.load_schedules()
                success = scheduler.save_schedules(schedules, enabled)
                
                if success:
                    return web.json_response({
                        'status': 'success', 
                        'globalEnabled': enabled,
                        'message': f"Scheduler system {'enabled' if enabled else 'disabled'}"
                    })
                else:
                    return web.json_response({'error': 'Toggle failed'}, status=500)
            except Exception as e:
                logger.error(f"Failed to toggle global switch: {e}")
                return web.json_response({'error': str(e)}, status=500)
        
        @server.PromptServer.instance.routes.post("/scheduledtask/save_workflow")
        async def save_workflow(request):
            """Save workflow as task file"""
            try:
                data = await request.json()
                workflow_name = data.get('name', '').strip()
                workflow_data = data.get('workflow', {})
                
                if not workflow_name:
                    return web.json_response({'error': 'Workflow name cannot be empty'}, status=400)
                
                if not workflow_data:
                    return web.json_response({'error': 'Workflow data cannot be empty'}, status=400)
                
                # Ensure safe filename
                import re
                safe_name = re.sub(r'[<>:"/\\|?*]', '_', workflow_name)
                if not safe_name.endswith('.json'):
                    safe_name += '.json'
                
                scheduler = get_scheduler()
                workflow_dir = scheduler.workflow_dir
                
                # Ensure folder exists
                import os
                os.makedirs(workflow_dir, exist_ok=True)
                
                # Save file
                filepath = os.path.join(workflow_dir, safe_name)
                
                # Check if file already exists
                if os.path.exists(filepath):
                    return web.json_response({
                        'error': f'File {safe_name} already exists, please use a different name'
                    }, status=400)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(workflow_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Successfully saved workflow: {safe_name}")
                
                return web.json_response({
                    'status': 'success',
                    'message': f'Workflow saved as {safe_name}',
                    'filename': safe_name
                })
                
            except Exception as e:
                logger.error(f"Failed to save workflow: {e}")
                return web.json_response({'error': str(e)}, status=500)
        
        logger.info("✅ Web routes setup completed")
        
    except ImportError:
        logger.warning("⚠️ ComfyUI server module not loaded yet, will retry later")
    except Exception as e:
        logger.error(f"❌ Failed to setup web routes: {e}")