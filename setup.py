#!/usr/bin/env python3
"""
Setup script for Ethereum Address Transaction Monitor
"""

import os
import sys
import subprocess

def create_env_file():
    """Create .env file from .env.example if it doesn't exist."""
    env_example = ".env.example"
    env_file = ".env"
    
    # Create .env.example if it doesn't exist
    if not os.path.exists(env_example):
        env_content = """# Infura WebSocket URL Configuration
INFURA_WSS_URL=wss://sepolia.infura.io/ws/v3/your_project_id_here

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Monitored Addresses (comma-separated)
MONITORED_ADDRESSES=0x8d7cad018f0900439374a36b1db9672b737f816a,0x38bd85f6746e1b47cabc384cd3bdaa44f96b2cb4

# Logging Configuration
LOG_LEVEL=INFO

# SSL Configuration
SSL_VERIFY=false
"""
        with open(env_example, 'w', encoding='utf-8') as f:
            f.write(env_content)
        print(f"✅ 已创建 {env_example} 文件")
    
    # Create .env from .env.example if it doesn't exist
    if not os.path.exists(env_file):
        try:
            with open(env_example, 'r', encoding='utf-8') as f:
                content = f.read()
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 已创建 {env_file} 文件")
            print(f"⚠️  请编辑 {env_file} 文件并填入正确的配置值")
        except Exception as e:
            print(f"❌ 创建 {env_file} 失败: {e}")
    else:
        print(f"ℹ️  {env_file} 文件已存在")

def install_dependencies():
    """Install required dependencies."""
    print("📦 安装依赖包...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ 依赖包安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖包安装失败: {e}")
        return False

def main():
    """Main setup function."""
    print("🚀 设置以太坊地址交易监听器")
    print("=" * 50)
    
    # Install dependencies
    if not install_dependencies():
        return 1
    
    # Create environment files
    create_env_file()
    
    print("\n" + "=" * 50)
    print("✅ 设置完成!")
    print("\n📋 下一步:")
    print("1. 编辑 .env 文件，填入正确的配置值")
    print("2. 运行 python main.py 启动监听器")
    print("\n💡 需要帮助?")
    print("   查看 README.md 文件获取详细配置说明")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
