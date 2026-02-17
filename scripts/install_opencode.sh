#!/bin/bash

# OpenCode CLI 安装脚本
# 用于安装 OpenCode - 开源 AI 编程代理

set -e

echo "======================================"
echo "  空间智能数据工厂 - OpenCode 安装"
echo "======================================"
echo ""

# 检测操作系统
OS=$(uname -s)
ARCH=$(uname -m)

echo "检测操作系统: $OS $ARCH"
echo ""

# 检查是否已安装
if command -v opencode &amp;&gt; /dev/null; then
    echo "✅ OpenCode 已安装"
    opencode --version
    echo ""
    echo "跳过安装"
    exit 0
fi

echo "OpenCode 未安装，开始安装..."
echo ""

# 尝试使用 Homebrew 安装 (macOS/Linux)
if command -v brew &amp;&gt; /dev/null; then
    echo "检测到 Homebrew，尝试通过 brew 安装..."
    echo ""
    
    if brew install opencode-ai/tap/opencode; then
        echo ""
        echo "✅ OpenCode 安装成功！"
        opencode --version
        echo ""
        exit 0
    fi
fi

# 尝试使用官方安装脚本
echo "尝试使用官方安装脚本..."
echo ""

if curl -fsSL https://raw.githubusercontent.com/opencode-ai/opencode/refs/heads/main/install | bash; then
    echo ""
    echo "✅ OpenCode 安装成功！"
    if command -v opencode &amp;&gt; /dev/null; then
        opencode --version
    fi
    echo ""
    exit 0
fi

echo ""
echo "⚠️  自动安装失败，请参考以下方式手动安装："
echo ""
echo "方式 1: Homebrew (macOS/Linux)"
echo "  brew install opencode-ai/tap/opencode"
echo ""
echo "方式 2: 官方安装脚本"
echo "  curl -fsSL https://raw.githubusercontent.com/opencode-ai/opencode/refs/heads/main/install | bash"
echo ""
echo "方式 3: Go 安装"
echo "  go install github.com/opencode-ai/opencode@latest"
echo ""
echo "安装后运行: opencode --version"
echo ""
exit 1
