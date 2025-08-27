"""
Address Storage module for managing monitored Ethereum addresses.
Provides functionality to dynamically add, remove, and list monitored addresses.
"""

import json
import os
import asyncio
import logging
from typing import List, Set, Optional, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

class AddressStorage:
    """Manages storage and retrieval of monitored Ethereum addresses with multi-user support."""
    
    def __init__(self, storage_file: str = "monitored_addresses.json"):
        """
        Initialize address storage.
        
        Args:
            storage_file: Path to the JSON file storing addresses
        """
        self.storage_file = Path(storage_file)
        self._addresses: Dict[str, List[int]] = {}  # address -> list of chat_ids
        self._lock = asyncio.Lock()
        
    async def load_addresses(self) -> Dict[str, List[int]]:
        """
        Load addresses from storage file.
        
        Returns:
            Dict of monitored addresses with their subscribers
        """
        async with self._lock:
            try:
                if self.storage_file.exists():
                    with open(self.storage_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Support both old format (list) and new format (dict)
                        if isinstance(data.get('addresses'), list):
                            # Old format: convert to new format
                            old_addresses = data.get('addresses', [])
                            self._addresses = {}
                            for addr in old_addresses:
                                if self._is_valid_address(addr):
                                    self._addresses[addr.lower()] = []
                        else:
                            # New format: dict with chat_ids
                            addresses_data = data.get('addresses', {})
                            self._addresses = {}
                            for addr, chat_ids in addresses_data.items():
                                if self._is_valid_address(addr):
                                    self._addresses[addr.lower()] = chat_ids if isinstance(chat_ids, list) else []
                        logger.info(f"从存储文件加载了 {len(self._addresses)} 个地址")
                else:
                    self._addresses = {}
                    logger.info("存储文件不存在，初始化空地址列表")
            except Exception as e:
                logger.error(f"加载地址存储文件失败: {e}")
                self._addresses = {}
            
            return self._addresses.copy()
    
    async def save_addresses(self) -> bool:
        """
        Save addresses to storage file.
        
        Returns:
            bool: True if save successful, False otherwise
        """
        async with self._lock:
            return await self._save_addresses_unlocked()
    
    async def _save_addresses_unlocked(self) -> bool:
        """
        Save addresses to storage file without acquiring lock.
        This method should only be called when the lock is already held.
        
        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            data = {
                'addresses': self._addresses,
                'count': len(self._addresses),
                'last_updated': self._get_timestamp()
            }
            
            # Create backup of existing file
            if self.storage_file.exists():
                backup_file = self.storage_file.with_suffix('.json.bak')
                self.storage_file.rename(backup_file)
            
            # Write new data
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"成功保存 {len(self._addresses)} 个地址到存储文件")
            return True
            
        except Exception as e:
            logger.error(f"保存地址到存储文件失败: {e}")
            return False
    
    async def add_address(self, address: str, chat_id: int) -> tuple[bool, str]:
        """
        Add a new address to monitoring list for a specific user.
        
        Args:
            address: Ethereum address to add
            chat_id: Telegram chat ID of the user
        
        Returns:
            tuple: (success: bool, message: str)
        """
        if not self._is_valid_address(address):
            return False, f"无效的以太坊地址格式: {address}"
        
        address_lower = address.lower()
        
        async with self._lock:
            # Check if user already subscribed to this address
            if address_lower in self._addresses and chat_id in self._addresses[address_lower]:
                return False, f"您已经订阅了该地址: {address}"
            
            # Add address and chat_id
            if address_lower not in self._addresses:
                self._addresses[address_lower] = []
            
            self._addresses[address_lower].append(chat_id)
            
            if await self._save_addresses_unlocked():
                logger.info(f"成功添加地址: {address} for chat_id: {chat_id}")
                return True, f"成功添加地址: {address}"
            else:
                # Rollback on save failure
                if address_lower in self._addresses:
                    if chat_id in self._addresses[address_lower]:
                        self._addresses[address_lower].remove(chat_id)
                    if not self._addresses[address_lower]:
                        del self._addresses[address_lower]
                return False, f"添加地址失败，无法保存到存储文件: {address}"
    
    async def remove_address(self, address: str, chat_id: int) -> tuple[bool, str]:
        """
        Remove an address from monitoring list for a specific user.
        
        Args:
            address: Ethereum address to remove
            chat_id: Telegram chat ID of the user
        
        Returns:
            tuple: (success: bool, message: str)
        """
        address_lower = address.lower()
        
        async with self._lock:
            if address_lower not in self._addresses or chat_id not in self._addresses[address_lower]:
                return False, f"您没有订阅该地址: {address}"
            
            # Store original for rollback
            original_chat_ids = self._addresses[address_lower].copy()
            
            # Remove chat_id from address subscribers
            self._addresses[address_lower].remove(chat_id)
            
            # If no more subscribers, remove the address entirely
            if not self._addresses[address_lower]:
                del self._addresses[address_lower]
            
            if await self._save_addresses_unlocked():
                logger.info(f"成功移除地址: {address} for chat_id: {chat_id}")
                return True, f"成功移除地址: {address}"
            else:
                # Rollback on save failure
                self._addresses[address_lower] = original_chat_ids
                return False, f"移除地址失败，无法保存到存储文件: {address}"
    
    async def get_addresses(self) -> List[str]:
        """
        Get all monitored addresses.
        
        Returns:
            List of monitored addresses
        """
        async with self._lock:
            return sorted(list(self._addresses.keys()))
    
    async def get_user_addresses(self, chat_id: int) -> List[str]:
        """
        Get addresses subscribed by a specific user.
        
        Args:
            chat_id: Telegram chat ID of the user
        
        Returns:
            List of addresses subscribed by the user
        """
        async with self._lock:
            user_addresses = []
            for address, subscribers in self._addresses.items():
                if chat_id in subscribers:
                    user_addresses.append(address)
            return sorted(user_addresses)
    
    async def get_address_subscribers(self, address: str) -> List[int]:
        """
        Get all subscribers for a specific address.
        
        Args:
            address: Ethereum address
        
        Returns:
            List of chat IDs subscribed to the address
        """
        address_lower = address.lower()
        async with self._lock:
            return self._addresses.get(address_lower, []).copy()
    
    async def get_address_count(self) -> int:
        """
        Get count of monitored addresses.
        
        Returns:
            Number of monitored addresses
        """
        async with self._lock:
            return len(self._addresses)
    
    async def clear_addresses(self, chat_id: int = None) -> tuple[bool, str]:
        """
        Clear monitored addresses. If chat_id is provided, only clear addresses for that user.
        
        Args:
            chat_id: Optional chat ID to clear addresses for specific user
        
        Returns:
            tuple: (success: bool, message: str)
        """
        async with self._lock:
            if chat_id is None:
                # Clear all addresses (admin operation)
                original_count = len(self._addresses)
                original_addresses = self._addresses.copy()
                self._addresses.clear()
                
                if await self._save_addresses_unlocked():
                    logger.info(f"成功清空所有地址，共移除 {original_count} 个地址")
                    return True, f"成功清空所有地址，共移除 {original_count} 个地址"
                else:
                    # Rollback
                    self._addresses = original_addresses
                    return False, "清空地址失败，无法保存到存储文件"
            else:
                # Clear addresses for specific user
                original_addresses = self._addresses.copy()
                removed_count = 0
                
                # Remove user from all address subscriptions
                addresses_to_remove = []
                for address, subscribers in self._addresses.items():
                    if chat_id in subscribers:
                        subscribers.remove(chat_id)
                        removed_count += 1
                        if not subscribers:
                            addresses_to_remove.append(address)
                
                # Remove addresses with no subscribers
                for address in addresses_to_remove:
                    del self._addresses[address]
                
                if await self._save_addresses_unlocked():
                    logger.info(f"成功清空用户 {chat_id} 的所有地址，共移除 {removed_count} 个订阅")
                    return True, f"成功清空您的所有地址订阅，共移除 {removed_count} 个地址"
                else:
                    # Rollback
                    self._addresses = original_addresses
                    return False, "清空地址失败，无法保存到存储文件"
    
    def _is_valid_address(self, address: str) -> bool:
        """
        Validate Ethereum address format.
        
        Args:
            address: Address to validate
        
        Returns:
            bool: True if valid Ethereum address
        """
        if not isinstance(address, str):
            return False
        
        # Remove 0x prefix if present
        if address.startswith('0x') or address.startswith('0X'):
            address = address[2:]
        
        # Check if it's 40 characters of valid hex
        if len(address) != 40:
            return False
        
        try:
            int(address, 16)
            return True
        except ValueError:
            return False
    
    def _get_timestamp(self) -> str:
        """Get current timestamp string."""
        from datetime import datetime
        return datetime.now().isoformat()

# Global address storage instance
_address_storage = None

def get_address_storage() -> AddressStorage:
    """Get the global address storage instance."""
    global _address_storage
    if _address_storage is None:
        _address_storage = AddressStorage()
    return _address_storage

async def initialize_address_storage() -> AddressStorage:
    """Initialize and load address storage."""
    storage = get_address_storage()
    await storage.load_addresses()
    return storage
