#!/bin/bash
# Quick Start Script for Spatial Intelligence Data Factory
# Sets up and validates the project for development and testing

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Spatial Intelligence Data Factory - Quick Start             ║"
echo "╚═══════════════════════════════════════════════════════════════╝"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check prerequisites
check_prerequisites() {
    echo -e "\n${BLUE}Checking prerequisites...${NC}"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 not found. Please install Python 3.9+"
        exit 1
    fi
    echo -e "${GREEN}✓ Python 3 found$(python3 --version)${NC}"

    # Check Git
    if ! command -v git &> /dev/null; then
        echo "❌ Git not found. Please install Git"
        exit 1
    fi
    echo -e "${GREEN}✓ Git found ($(git --version | cut -d' ' -f3))${NC}"

    # Check jq for JSON validation
    if ! command -v jq &> /dev/null; then
        echo -e "${YELLOW}⚠ jq not found. JSON validation skipped (optional)${NC}"
    else
        echo -e "${GREEN}✓ jq found${NC}"
    fi
}

# Setup directories
setup_directories() {
    echo -e "\n${BLUE}Setting up project directories...${NC}"

    mkdir -p logs/daily logs/members logs/summary
    mkdir -p testdata/downloads testdata/seeds
    echo -e "${GREEN}✓ Directories created${NC}"
}

# Validate schemas
validate_schemas() {
    echo -e "\n${BLUE}Validating database schemas...${NC}"

    schemas=(
        "schemas/shanghai-address-24-level.schema.sql"
        "schemas/wujiang-public-security.schema.sql"
        "schemas/changzhou-urban-command.schema.sql"
    )

    for schema in "${schemas[@]}"; do
        if [ -f "$schema" ]; then
            echo -e "${GREEN}✓ Found: $schema${NC}"
        else
            echo "❌ Missing: $schema"
            exit 1
        fi
    done
}

# Validate test data
validate_testdata() {
    echo -e "\n${BLUE}Validating test data fixtures...${NC}"

    if command -v jq &> /dev/null; then
        fixtures=(
            "testdata/fixtures/shanghai-address-samples.json"
            "testdata/fixtures/wujiang-samples.json"
            "testdata/fixtures/changzhou-samples.json"
        )

        for fixture in "${fixtures[@]}"; do
            if [ -f "$fixture" ]; then
                if jq empty "$fixture" 2>/dev/null; then
                    local records=$(jq '.datasets | length' "$fixture")
                    echo -e "${GREEN}✓ Valid: $fixture ($records datasets)${NC}"
                else
                    echo "❌ Invalid JSON: $fixture"
                    exit 1
                fi
            else
                echo "❌ Missing: $fixture"
                exit 1
            fi
        done
    else
        echo -e "${YELLOW}⚠ Skipping JSON validation (jq not installed)${NC}"
    fi
}

# Validate Python modules
validate_python_modules() {
    echo -e "\n${BLUE}Validating Python modules...${NC}"

    modules=(
        "tools/agent_framework.py"
        "tools/address_governance.py"
    )

    for module in "${modules[@]}"; do
        if [ -f "$module" ]; then
            if python3 -m py_compile "$module" 2>/dev/null; then
                echo -e "${GREEN}✓ Valid Python: $module${NC}"
            else
                echo "❌ Python syntax error: $module"
                exit 1
            fi
        else
            echo "❌ Missing: $module"
            exit 1
        fi
    done
}

# Display project summary
show_summary() {
    echo -e "\n${BLUE}Project Summary:${NC}"
    echo ""
    echo "📊 Database Schemas:"
    echo "   • Shanghai Address Governance: 10 tables (24-level hierarchy)"
    echo "   • Wujiang Public Security: 10 tables"
    echo "   • Changzhou Urban Command: 10 tables"
    echo ""
    echo "🤖 Agent Framework:"
    echo "   • 9 core agents (Requirements, Exploration, Modeling, Quality, etc.)"
    echo "   • Async execution with audit trail"
    echo "   • Agent orchestrator for workflow management"
    echo ""
    echo "📍 Address Governance Module:"
    echo "   • Parser, Standardizer, EntityMapper, Quality Assessment"
    echo "   • Support for multi-source entity fusion"
    echo ""
    echo "🧪 Test Data:"
    echo "   • Shanghai: 31 sample records"
    echo "   • Wujiang: 25 sample records"
    echo "   • Changzhou: 19 sample records"
    echo ""
    echo "📚 Documentation:"
    echo "   • System Design: specs/001-system-design-spec/"
    echo "   • Architecture: docs/architecture-alignment-*.md"
    echo "   • Cloud Setup: docs/cloud-bootstrap-runbook.md"
    echo ""
}

# Display next steps
show_next_steps() {
    echo -e "\n${BLUE}Next Steps:${NC}"
    echo ""
    echo "1. Review test data:"
    echo "   ${YELLOW}bash scripts/testdata/testdata.sh list${NC}"
    echo ""
    echo "2. Setup cloud infrastructure (optional):"
    echo "   ${YELLOW}bash docs/cloud-bootstrap-runbook.md${NC}"
    echo ""
    echo "3. Import database schemas (requires database):"
    echo "   ${YELLOW}mysql -u user -p < schemas/shanghai-address-24-level.schema.sql${NC}"
    echo ""
    echo "4. Run tests and validation:"
    echo "   ${YELLOW}python3 -c \"from tools.agent_framework import *; print('Agent framework loaded')\"${NC}"
    echo ""
    echo "5. Review architecture documentation:"
    echo "   ${YELLOW}cat docs/architecture-alignment-spatial-intelligence-data-factory-2026-02-11.md${NC}"
    echo ""
}

# Main execution
main() {
    check_prerequisites
    setup_directories
    validate_schemas
    validate_testdata
    validate_python_modules
    show_summary
    show_next_steps

    echo -e "\n${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ Project setup completed successfully!                     ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

main
