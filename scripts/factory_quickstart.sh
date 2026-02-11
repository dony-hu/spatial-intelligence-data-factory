#!/bin/bash

# Factory Demo Quickstart Script
# Automated setup and execution of the factory demonstration system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_header() {
    echo -e "\n${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}\n"
}

print_step() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}  $1${NC}"
}

# Check Python installation
print_header "检查依赖环境"

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 未找到"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
print_step "Python 版本: $PYTHON_VERSION"

# Check SQLite
if ! command -v sqlite3 &> /dev/null; then
    print_error "SQLite 未找到"
    exit 1
fi

print_step "SQLite 已安装"

# Create output directory
print_step "创建输出目录"
mkdir -p output
mkdir -p database
mkdir -p logs

# Run demo workflow
print_header "执行工厂演示工作流"

echo "选择演示场景:"
echo "  1. quick_test       - 快速测试 (3个地址)"
echo "  2. address_cleaning - 地址清洗 (10个地址)"
echo "  3. entity_fusion    - 实体融合 (5个实体)"
echo "  4. relationship_extraction - 关系抽取 (10个地址)"
echo "  5. multi - 多工作流并行执行"
echo ""

# Get user input or use default
SCENARIO=${1:-"quick_test"}

if [ "$SCENARIO" = "multi" ]; then
    print_info "运行多工作流演示..."
    python3 scripts/factory_demo_workflow.py --multi
else
    print_info "运行演示场景: $SCENARIO"
    python3 scripts/factory_demo_workflow.py --scenario "$SCENARIO"
fi

# Generate dashboard
print_header "生成工厂看板"

python3 tools/factory_dashboard.py
print_step "看板已生成: output/factory_dashboard.html"

# Print completion message
print_header "演示完成"

print_info "已生成文件:"
print_info "  - database/factory.db              (工厂运营数据库)"
print_info "  - output/factory_dashboard.html    (交互式看板)"

echo ""
print_step "下一步:"
print_info "  1. 打开看板在浏览器中查看:"
print_info "     open output/factory_dashboard.html"
print_info ""
print_info "  2. 查询数据库统计信息:"
print_info "     sqlite3 database/factory.db \"SELECT * FROM factory_metrics ORDER BY timestamp DESC LIMIT 1;\""
print_info ""
print_info "  3. 导出工厂状态为JSON:"
print_info "     python3 -c \"from tools.factory_workflow import FactoryWorkflow; wf = FactoryWorkflow(); print(wf.export_state_to_json())\" > output/factory_state.json"
print_info ""
print_info "  4. 运行其他演示场景:"
print_info "     bash scripts/factory_quickstart.sh address_cleaning"
print_info "     bash scripts/factory_quickstart.sh entity_fusion"
print_info "     bash scripts/factory_quickstart.sh multi"

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  🎉 数据工厂演示系统演示完成！${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}\n"
