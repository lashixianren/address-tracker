"""Webhook server for receiving Telegram bot updates."""

import asyncio
import logging
import json
from aiohttp import web, ClientSession
from typing import Optional
from config import config
from telegram_bot import get_telegram_bot, setup_bot_commands

logger = logging.getLogger(__name__)

class WebhookServer:
    """HTTP server for handling Telegram webhook requests."""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 8080):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.site = None
        
        # Setup routes
        self.app.router.add_post('/webhook', self.handle_webhook)
        self.app.router.add_get('/health', self.health_check)
    
    async def handle_webhook(self, request: web.Request) -> web.Response:
        """Handle incoming webhook requests from Telegram."""
        try:
            # Parse JSON payload
            update = await request.json()
            logger.info(f"收到webhook更新: {update.get('update_id')}")
            
            # Get bot instance and process update
            bot = await get_telegram_bot()
            if bot:
                await bot.process_webhook_update(update)
            else:
                logger.error("无法获取Telegram bot实例")
                return web.Response(status=500, text="Bot not available")
            
            return web.Response(status=200, text="OK")
            
        except json.JSONDecodeError:
            logger.error("无效的JSON数据")
            return web.Response(status=400, text="Invalid JSON")
        except Exception as e:
            logger.error(f"处理webhook请求时发生错误: {e}")
            return web.Response(status=500, text="Internal server error")
    
    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.Response(status=200, text="Webhook server is running")
    
    async def start(self) -> bool:
        """Start the webhook server."""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()
            
            logger.info(f"Webhook服务器启动成功: http://{self.host}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"启动webhook服务器失败: {e}")
            return False
    
    async def stop(self):
        """Stop the webhook server."""
        try:
            if self.site:
                await self.site.stop()
                self.site = None
            
            if self.runner:
                await self.runner.cleanup()
                self.runner = None
            
            logger.info("Webhook服务器已停止")
            
        except Exception as e:
            logger.error(f"停止webhook服务器时发生错误: {e}")

# Global webhook server instance
webhook_server = None

async def get_webhook_server(host: str = '0.0.0.0', port: int = 8080) -> Optional[WebhookServer]:
    """Get the global webhook server instance."""
    global webhook_server
    
    if webhook_server is None:
        webhook_server = WebhookServer(host, port)
    
    return webhook_server

async def start_webhook_server(host: str = '0.0.0.0', port: int = 8080) -> Optional[WebhookServer]:
    """Start the webhook server."""
    server = await get_webhook_server(host, port)
    
    if server:
        success = await server.start()
        if success:
            return server
        else:
            return None
    
    return None

async def stop_webhook_server():
    """Stop the webhook server."""
    global webhook_server
    
    if webhook_server:
        await webhook_server.stop()
        webhook_server = None

async def setup_webhook(webhook_url: str) -> bool:
    """Setup webhook with Telegram."""
    try:
        bot = await get_telegram_bot()
        if not bot:
            logger.error("无法获取Telegram bot实例")
            return False
        
        # Delete existing webhook first
        await bot.delete_webhook()
        
        # Set new webhook
        success = await bot.set_webhook(webhook_url)
        if success:
            logger.info(f"Webhook设置成功: {webhook_url}")
            # Setup bot commands for webhook mode
            await setup_bot_commands(bot)
            logger.info("Webhook模式下命令已注册")
        else:
            logger.error(f"Webhook设置失败: {webhook_url}")
        
        return success
        
    except Exception as e:
        logger.error(f"设置webhook时发生错误: {e}")
        return False

async def cleanup_webhook() -> bool:
    """Clean up webhook configuration."""
    try:
        bot = await get_telegram_bot()
        if not bot:
            logger.error("无法获取Telegram bot实例")
            return False
        
        success = await bot.delete_webhook()
        if success:
            logger.info("Webhook清理成功")
        else:
            logger.error("Webhook清理失败")
        
        return success
        
    except Exception as e:
        logger.error(f"清理webhook时发生错误: {e}")
        return False