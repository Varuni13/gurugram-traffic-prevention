#!/bin/bash

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║         REFACTORING VERIFICATION SCRIPT                           ║"
echo "║         Traffic Forecasting Emulator - January 12, 2026           ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS_COUNT=0
FAIL_COUNT=0

# Function to check file exists
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1 exists"
        ((PASS_COUNT++))
    else
        echo -e "${RED}✗${NC} $1 missing"
        ((FAIL_COUNT++))
    fi
}

# Function to check syntax
check_syntax() {
    if python3 -m py_compile "$1" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $1 syntax valid"
        ((PASS_COUNT++))
    else
        echo -e "${RED}✗${NC} $1 syntax error"
        ((FAIL_COUNT++))
    fi
}

echo "📁 CHECKING NEW FILES..."
echo "───────────────────────────────────────────────────────────────────"
check_file "config.py"
check_file "server/utils.py"
check_file "server/handlers/__init__.py"
check_file "server/handlers/flood_handler.py"
check_file "server/handlers/traffic_handler.py"
check_file "ARCHITECTURE.md"
check_file "REFACTORING_SUMMARY.md"
check_file "QUICKSTART.md"
check_file "REFACTORING_COMPLETE.md"
check_file "INDEX.md"
echo ""

echo "🔍 CHECKING SYNTAX..."
echo "───────────────────────────────────────────────────────────────────"
check_syntax "config.py"
check_syntax "serve.py"
check_syntax "server/api.py"
check_syntax "server/routing.py"
check_syntax "server/utils.py"
check_syntax "server/handlers/flood_handler.py"
check_syntax "server/handlers/traffic_handler.py"
check_syntax "collector/config.py"
echo ""

echo "🔧 CHECKING FIXES..."
echo "───────────────────────────────────────────────────────────────────"

# Check typo fixed
if grep -q "global _graph, _graphml_path_used$" server/routing.py; then
    echo -e "${GREEN}✓${NC} Typo in routing.py fixed"
    ((PASS_COUNT++))
else
    echo -e "${RED}✗${NC} Typo in routing.py still present"
    ((FAIL_COUNT++))
fi

# Check CORS configured
if grep -q "CORS_ENABLED\|CORS_ORIGINS" config.py; then
    echo -e "${GREEN}✓${NC} CORS properly configured in config.py"
    ((PASS_COUNT++))
else
    echo -e "${RED}✗${NC} CORS configuration missing"
    ((FAIL_COUNT++))
fi

# Check handlers imported
if grep -q "from server.handlers" server/api.py; then
    echo -e "${GREEN}✓${NC} Handlers imported in api.py"
    ((PASS_COUNT++))
else
    echo -e "${RED}✗${NC} Handlers not imported"
    ((FAIL_COUNT++))
fi

# Check global config used
if grep -q "import config as global_config" server/api.py; then
    echo -e "${GREEN}✓${NC} Global config imported in api.py"
    ((PASS_COUNT++))
else
    echo -e "${RED}✗${NC} Global config not imported"
    ((FAIL_COUNT++))
fi

echo ""

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                    VERIFICATION RESULTS                           ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}✓ PASSED: $PASS_COUNT${NC}"
echo -e "${RED}✗ FAILED: $FAIL_COUNT${NC}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ ALL CHECKS PASSED - REFACTORING COMPLETE!                     ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "📚 Next steps:"
    echo "  1. Read: INDEX.md"
    echo "  2. Read: QUICKSTART.md"
    echo "  3. Create: .env file"
    echo "  4. Run: python serve.py"
    echo ""
    exit 0
else
    echo -e "${RED}❌ Some checks failed. Please review the errors above.${NC}"
    exit 1
fi
