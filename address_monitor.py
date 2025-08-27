"""
Address Monitor module for tracking Ethereum addresses and transactions.
"""

import asyncio
import json
import websockets
import ssl
from typing import List, Set, Optional, Dict, Any
import logging
from config import config
from telegram_bot import send_transaction_notification, send_status_notification, send_error_notification
from address_storage import get_address_storage

logger = logging.getLogger(__name__)

class AddressMonitor:
    """Monitor Ethereum addresses for transactions."""
    
    def __init__(self):
        """Initialize the address monitor."""
        self.websocket = None
        self.subscription_id = None
        self.wss_url = config.INFURA_WSS_URL
        self.storage = get_address_storage()
        self._addresses: Set[str] = set()
        
    async def update_addresses(self):
        """Update the monitored addresses from storage."""
        addresses = await self.storage.get_addresses()
        self._addresses = {addr.lower() for addr in addresses}
        logger.debug(f"更新监听地址列表，当前监听 {len(self._addresses)} 个地址")
        
    async def get_current_addresses(self) -> Set[str]:
        """Get current monitored addresses."""
        await self.update_addresses()
        return self._addresses.copy()
        
    async def connect(self) -> bool:
        """
        Connect to WebSocket.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Create SSL context
            ssl_context = ssl.create_default_context()
            if not config.SSL_VERIFY:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                logger.warning("SSL证书验证已禁用（仅用于开发/测试）")
            
            # Set max_size to handle large block data (default is 1MB, increase to 10MB)
            self.websocket = await websockets.connect(
                self.wss_url, 
                ssl=ssl_context,
                max_size=10 * 1024 * 1024  # 10MB limit for large blocks
            )
            logger.info(f"已连接到WebSocket: {self.wss_url}")
            
            return True
        except Exception as e:
            error_msg = f"连接WebSocket失败: {e}"
            logger.error(error_msg)
            if config.is_channel_mode():
                await send_error_notification(error_msg)
            return False
    
    async def subscribe_to_new_blocks(self) -> bool:
        """
        Subscribe to new blocks.
        
        Returns:
            bool: True if subscription successful, False otherwise
        """
        try:
            # Subscribe to new block headers
            subscription_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_subscribe",
                "params": ["newHeads"]
            }
            
            await self.websocket.send(json.dumps(subscription_request))
            response = await self.websocket.recv()
            response_data = json.loads(response)
            
            if "result" in response_data:
                self.subscription_id = response_data["result"]
                logger.info(f"成功订阅新区块，订阅ID: {self.subscription_id}")
                
                # Send subscription notification only in channel mode
                if config.is_channel_mode():
                    await send_status_notification(f"✅ 成功订阅新区块通知\n🆔 订阅ID: {self.subscription_id}")
                
                logger.info("📝 订阅处理完成，准备返回True")
                return True
            else:
                error_msg = f"订阅失败: {response_data}"
                logger.error(error_msg)
                if config.is_channel_mode():
                    await send_error_notification(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"订阅新区块失败: {e}"
            logger.error(error_msg)
            if config.is_channel_mode():
                await send_error_notification(error_msg)
            return False
    
    async def get_block_transactions(self, block_hash: str) -> List[Dict[str, Any]]:
        """
        Get all transactions in a block.
        
        Args:
            block_hash: Hash of the block to get transactions from
        
        Returns:
            List of transaction dictionaries
        """
        try:
            request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "eth_getBlockByHash",
                "params": [block_hash, True]  # True for full transaction info
            }
            
            await self.websocket.send(json.dumps(request))
            response = await self.websocket.recv()
            response_data = json.loads(response)
            
            if "result" in response_data and response_data["result"]:
                return response_data["result"].get("transactions", [])
            return []
            
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"获取区块交易失败，WebSocket连接已关闭: {e}")
            # Try to reconnect
            if await self.connect():
                logger.info("WebSocket重连成功，重新订阅新区块")
                await self.subscribe_to_new_blocks()
            return []
        except Exception as e:
            logger.error(f"获取区块交易失败: {e}")
            return []
    
    def check_transaction_relevance(self, transaction: Dict[str, Any]) -> bool:
        """
        Check if a transaction is relevant to monitored addresses.
        
        Args:
            transaction: Transaction dictionary
        
        Returns:
            bool: True if transaction involves monitored addresses
        """
        tx_from = transaction.get("from", "").lower()
        tx_to = transaction.get("to", "").lower() if transaction.get("to") else ""
        
        return tx_from in self._addresses or tx_to in self._addresses
    
    def format_transaction_info(self, transaction: Dict[str, Any]) -> str:
        """
        Format transaction information for console output.
        
        Args:
            transaction: Transaction dictionary
        
        Returns:
            Formatted transaction string
        """
        tx_hash = transaction.get("hash", "")
        tx_from = transaction.get("from", "")
        tx_to = transaction.get("to", "")
        value = transaction.get("value", "0")
        gas_price = transaction.get("gasPrice", "0")
        
        # Convert Wei to ETH
        try:
            value_eth = int(value, 16) / 10**18 if value != "0x0" else 0
        except (ValueError, TypeError):
            value_eth = 0
        
        # Convert Wei to Gwei for gas price
        try:
            gas_price_gwei = int(gas_price, 16) / 10**9 if gas_price != "0x0" else 0
        except (ValueError, TypeError):
            gas_price_gwei = 0
        
        return (
            f"🔗 新交易检测到!\n"
            f"   交易哈希: {tx_hash}\n"
            f"   发送方: {tx_from}\n"
            f"   接收方: {tx_to}\n"
            f"   金额: {value_eth:.6f} ETH\n"
            f"   Gas价格: {gas_price_gwei:.2f} Gwei\n"
            f"   {'='*50}"
        )
    
    async def send_transaction_notification_to_user(self, transaction_info: dict, chat_id: str) -> bool:
        """
        Send transaction notification to a specific user.
        
        Args:
            transaction_info: Dictionary containing transaction details
            chat_id: Target chat ID
        
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        try:
            from telegram_bot import send_reply_message
            
            # Format transaction info for Telegram
            tx_hash = transaction_info.get("hash", "")
            tx_from = transaction_info.get("from", "")
            tx_to = transaction_info.get("to", "")
            value = transaction_info.get("value", "0")
            gas_price = transaction_info.get("gasPrice", "0")
            block_number = transaction_info.get("blockNumber", "")
            
            # Convert Wei to ETH
            try:
                value_eth = int(value, 16) / 10**18 if value != "0x0" else 0
            except (ValueError, TypeError):
                value_eth = 0
            
            # Convert Wei to Gwei for gas price
            try:
                gas_price_gwei = int(gas_price, 16) / 10**9 if gas_price != "0x0" else 0
            except (ValueError, TypeError):
                gas_price_gwei = 0
            
            # Create formatted message
            message = (
                f"🔗 <b>新交易检测到!</b>\n\n"
                f"📊 <b>区块号:</b> {block_number}\n"
                f"🔑 <b>交易哈希:</b>\n<code>{tx_hash}</code>\n\n"
                f"📤 <b>发送方:</b>\n<code>{tx_from}</code>\n\n"
                f"📥 <b>接收方:</b>\n<code>{tx_to}</code>\n\n"
                f"💰 <b>金额:</b> {value_eth:.6f} ETH\n"
                f"⛽ <b>Gas价格:</b> {gas_price_gwei:.2f} Gwei\n\n"
                f"🔍 <a href='https://sepolia.etherscan.io/tx/{tx_hash}'>在 Etherscan 上查看</a>"
            )
            
            return await send_reply_message(chat_id, message)
            
        except Exception as e:
            logger.error(f"向用户 {chat_id} 发送交易通知时发生错误: {e}")
            return False
    
    async def process_transaction(self, transaction: Dict[str, Any], block_number: str):
        """
        Process a relevant transaction and notify all subscribers.
        
        Args:
            transaction: Transaction dictionary
            block_number: Block number containing the transaction
        """
        # Add block number to transaction info for Telegram notification
        transaction_with_block = transaction.copy()
        transaction_with_block["blockNumber"] = block_number
        
        # Print to console
        console_output = self.format_transaction_info(transaction)
        print(console_output)
        logger.info(f"检测到相关交易: {transaction.get('hash', '')}")
        
        # Find all subscribers for the relevant addresses
        relevant_addresses = set()
        tx_from = transaction.get('from', '').lower()
        tx_to = transaction.get('to', '').lower()
        
        if tx_from in self._addresses:
            relevant_addresses.add(tx_from)
        if tx_to in self._addresses:
            relevant_addresses.add(tx_to)
        
        # Collect all unique subscribers
        all_subscribers = set()
        for address in relevant_addresses:
            subscribers = await self.storage.get_address_subscribers(address)
            all_subscribers.update(subscribers)
        
        logger.info(f"向 {len(all_subscribers)} 个用户发送交易通知")
        
        # Send notifications to all subscribers
        success_count = 0
        for chat_id in all_subscribers:
            success = await self.send_transaction_notification_to_user(transaction_with_block, str(chat_id))
            if success:
                success_count += 1
        
        logger.info(f"交易通知发送完成: {success_count}/{len(all_subscribers)} 成功")
        
        # Also send to default notification (if configured) for backward compatibility
        if not all_subscribers:  # Only if no specific subscribers
            success = await send_transaction_notification(transaction_with_block)
            if success:
                logger.debug("默认Telegram通知发送成功")
            else:
                logger.warning("默认Telegram通知发送失败")
    
    async def listen_for_transactions(self):
        """Listen for transactions on monitored addresses."""
        # Update addresses from storage
        await self.update_addresses()
        
        logger.info(f"开始监听 {len(self._addresses)} 个地址的交易...")
        if self._addresses:
            logger.info(f"监听地址: {', '.join(list(self._addresses)[:3])}{'...' if len(self._addresses) > 3 else ''}")
        
        # Send simple monitoring start notification (only if in channel mode)
        if config.is_channel_mode():
            await send_status_notification("🚀 地址监听器已启动，开始监控区块链交易")
        
        try:
            last_address_update = 0
            address_update_interval = 30  # Update addresses every 30 seconds
            
            logger.info("💫 进入监听循环，等待新区块...")
            while True:
                # Periodically update monitored addresses
                current_time = asyncio.get_event_loop().time()
                if current_time - last_address_update > address_update_interval:
                    old_count = len(self._addresses)
                    await self.update_addresses()
                    new_count = len(self._addresses)
                    
                    if old_count != new_count:
                        logger.info(f"监听地址数量已更新: {old_count} -> {new_count}")
                    
                    last_address_update = current_time
                
                # Use timeout to avoid blocking too long
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.debug("WebSocket接收超时，继续监听...")
                    continue  # Continue loop to check for address updates
                except websockets.exceptions.ConnectionClosed as e:
                    if "message too big" in str(e):
                        logger.error(f"接收到过大的消息，WebSocket连接关闭: {e}")
                        logger.info("尝试重新连接WebSocket...")
                        if await self.connect() and await self.subscribe_to_new_blocks():
                            logger.info("WebSocket重连成功，继续监听")
                            continue
                        else:
                            logger.error("WebSocket重连失败，退出监听")
                            break
                    else:
                        logger.error(f"WebSocket连接意外关闭: {e}")
                        break
                
                logger.debug(f"收到WebSocket消息: {message[:200]}...")
                data = json.loads(message)
                
                # Check if this is a new block notification
                if (data.get("method") == "eth_subscription" and 
                    data.get("params", {}).get("subscription") == self.subscription_id):
                    
                    block_data = data["params"]["result"]
                    block_hash = block_data.get("hash")
                    block_number = block_data.get("number")
                    
                    logger.info(f"检测到新区块: {block_number} ({block_hash})")
                    
                    # Skip processing if no addresses to monitor
                    if not self._addresses:
                        logger.debug(f"跳过区块 {block_number}：没有监听地址")
                        continue
                    
                    # Get all transactions in the block
                    transactions = await self.get_block_transactions(block_hash)
                    
                    # Check each transaction for relevance to monitored addresses
                    relevant_transactions = 0
                    for tx in transactions:
                        if self.check_transaction_relevance(tx):
                            await self.process_transaction(tx, block_number)
                            relevant_transactions += 1
                    
                    if not transactions:
                        logger.debug(f"区块 {block_number} 中没有交易")
                    elif relevant_transactions == 0:
                        logger.debug(f"区块 {block_number} 中没有相关交易")
                        
        except websockets.exceptions.ConnectionClosed:
            error_msg = "WebSocket连接已关闭"
            logger.error(error_msg)
            if config.is_channel_mode():
                await send_error_notification(error_msg)
        except Exception as e:
            error_msg = f"监听交易时发生错误: {e}"
            logger.error(error_msg)
            if config.is_channel_mode():
                await send_error_notification(error_msg)
    
    async def start_monitoring(self):
        """Start the monitoring process."""
        logger.info("🚀 开始启动监听进程...")
        
        if not await self.connect():
            logger.error("❌ WebSocket连接失败，退出监听")
            return
        
        logger.info("✅ WebSocket连接成功，开始订阅新区块")
        if not await self.subscribe_to_new_blocks():
            logger.error("❌ 订阅新区块失败，退出监听")
            return
        
        logger.info("✅ 新区块订阅成功，开始监听交易")
        await self.listen_for_transactions()
    
    async def close(self):
        """Close the WebSocket connection."""
        if self.websocket:
            await self.websocket.close()
            logger.info("WebSocket连接已关闭")
            if config.is_channel_mode():
                await send_status_notification("⏹️ 地址监听器已停止")

async def create_address_monitor() -> AddressMonitor:
    """
    Create an AddressMonitor instance.
    
    Returns:
        AddressMonitor instance
    """
    monitor = AddressMonitor()
    
    # Initialize address storage
    await monitor.storage.load_addresses()
    
    # Load addresses from config if storage is empty
    if await monitor.storage.get_address_count() == 0 and config.MONITORED_ADDRESSES:
        logger.info("从配置文件导入初始监听地址...")
        for address in config.MONITORED_ADDRESSES:
            success, msg = await monitor.storage.add_address(address)
            if success:
                logger.info(f"从配置导入地址: {address}")
            else:
                logger.warning(f"导入地址失败: {msg}")
    
    return monitor
