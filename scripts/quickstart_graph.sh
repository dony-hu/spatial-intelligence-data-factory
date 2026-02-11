#!/bin/bash

# Spatial Entity Relationship Graph - Quick Start
# Builds and visualizes address data structure as entity relationship graph

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║  Spatial Entity Relationship Graph - Quick Start                  ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Check prerequisites
echo -e "${BLUE}[1/4] Checking prerequisites...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 found ($(python3 --version | cut -d' ' -f2))${NC}"

# Create output directory
echo -e "\n${BLUE}[2/4] Setting up directories...${NC}"
mkdir -p output database
mkdir -p testdata
echo -e "${GREEN}✓ Output directories created${NC}"

# Generate sample data if not exists
echo -e "\n${BLUE}[3/4] Preparing address samples...${NC}"
python3 -c "from testdata.address_samples_50 import save_to_json; save_to_json()"

# Build entity graph
echo -e "\n${BLUE}[4/4] Building entity relationship graph...${NC}"
python3 scripts/build_entity_graph.py

# Show results
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Entity Relationship Graph Generated Successfully!            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}📊 Output Files:${NC}"
echo "  • JSON Format:      output/graph.json"
echo "  • GraphML Format:   output/graph.graphml"
echo "  • Visualization:    output/entity_relationship_graph.html"
echo "  • Database:         database/entity_graph.db"
echo ""

echo -e "${YELLOW}🎯 Next Steps:${NC}"
echo "  1. Open visualization in browser:"
echo -e "     ${BLUE}open output/entity_relationship_graph.html${NC}"
echo ""
echo "  2. Query the database:"
echo -e "     ${BLUE}sqlite3 database/entity_graph.db${NC}"
echo ""
echo "  3. View JSON graph:"
echo -e "     ${BLUE}cat output/graph.json | jq . | head -50${NC}"
echo ""

echo -e "${GREEN}✨ Graph generation complete!${NC}"
echo ""
