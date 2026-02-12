#!/bin/bash
# Test Data Management Script for Spatial Intelligence Data Factory
# Manages test data: validation, checksums, and catalog updates

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TESTDATA_DIR="${PROJECT_ROOT}/testdata"
FIXTURES_DIR="${TESTDATA_DIR}/fixtures"
CATALOG_FILE="${TESTDATA_DIR}/catalog.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate JSON fixture file
validate_fixture() {
    local fixture_file="$1"
    if ! jq empty "$fixture_file" 2>/dev/null; then
        log_error "Invalid JSON in $fixture_file"
        return 1
    fi
    log_info "✓ Valid JSON: $fixture_file"
    return 0
}

# Generate SHA256 checksum for fixture
generate_checksum() {
    local fixture_file="$1"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        shasum -a 256 "$fixture_file" | awk '{print $1}'
    else
        sha256sum "$fixture_file" | awk '{print $1}'
    fi
}

# Validate all fixtures
validate_all_fixtures() {
    log_info "Validating all test data fixtures..."
    local failed=0
    for fixture in "$FIXTURES_DIR"/*.json; do
        if [ -f "$fixture" ]; then
            if ! validate_fixture "$fixture"; then
                ((failed++))
            fi
        fi
    done

    if [ $failed -gt 0 ]; then
        log_error "$failed fixture(s) validation failed"
        return 1
    fi
    log_info "All fixtures validated successfully"
    return 0
}

# Update checksums in fixtures
update_checksums() {
    log_info "Updating checksums for all fixtures..."
    for fixture in "$FIXTURES_DIR"/*.json; do
        if [ -f "$fixture" ]; then
            local checksum=$(generate_checksum "$fixture")
            log_info "Checksum for $(basename "$fixture"): $checksum"
        fi
    done
}

# List all fixtures
list_fixtures() {
    log_info "Available test data fixtures:"
    for fixture in "$FIXTURES_DIR"/*.json; do
        if [ -f "$fixture" ]; then
            local size=$(wc -c < "$fixture" | xargs)
            local records=$(jq '.datasets | length' "$fixture")
            echo "  - $(basename "$fixture") ($records datasets, ${size} bytes)"
        fi
    done
}

# Show usage
usage() {
    cat << EOF
Usage: testdata.sh [COMMAND]

Commands:
    validate    - Validate all JSON fixtures
    checksums   - Update and show checksums for all fixtures
    list        - List all available fixtures
    help        - Show this help message

Examples:
    ./testdata.sh validate
    ./testdata.sh checksums
    ./testdata.sh list
EOF
}

# Main
case "${1:-help}" in
    validate)
        validate_all_fixtures
        ;;
    checksums)
        update_checksums
        ;;
    list)
        list_fixtures
        ;;
    help)
        usage
        ;;
    *)
        log_error "Unknown command: $1"
        usage
        exit 1
        ;;
esac
