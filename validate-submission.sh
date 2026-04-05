#!/usr/bin/env bash
#
# validate-submission.sh — OpenEnv Submission Validator
#
set -uo pipefail

# Visuals
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

PING_URL="${1:-}"
REPO_DIR="${2:-.}"

if [ -z "$PING_URL" ]; then
    printf "${RED}Usage:${NC} sh %s <ping_url> [repo_dir]\n" "$0"
    exit 1
fi

printf "\n${BOLD}Starting Validation...${NC}\n"

# Step 1: Ping Check
printf "[1/3] Pinging: $PING_URL/reset... "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{}' "$PING_URL/reset" --max-time 10 || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    printf "${GREEN}PASSED${NC}\n"
else
    printf "${RED}FAILED${NC} (HTTP $HTTP_CODE)\n"
    exit 1
fi

# Step 2: Docker Check
printf "[2/3] Checking Docker Build... "
if docker build -t validation-test "$REPO_DIR" > /dev/null 2>&1; then
    printf "${GREEN}PASSED${NC}\n"
else
    printf "${RED}FAILED${NC} (Docker build error)\n"
    exit 1
fi

# Step 3: OpenEnv Spec Check
printf "[3/3] Checking OpenEnv Spec... "
SCHEMA=$(curl -s http://localhost:7860/schema)
if echo "$SCHEMA" | python3 -c "
import sys, json
s = json.load(sys.stdin)
assert 'action' in s
assert 'observation' in s
assert 'charge_rate_kw' in s['action']['properties']
assert s['action']['properties']['charge_rate_kw']['minimum'] == -15.0
assert s['action']['properties']['charge_rate_kw']['maximum'] == 50.0
print('[OK]')
" 2>&1 | grep -q "\[OK\]"; then
    printf "${GREEN}PASSED${NC}\n"
else
    printf "${RED}FAILED${NC} (Schema mismatch)\n"
    exit 1
fi

printf "\n${GREEN}${BOLD}ALL CHECKS PASSED! Ready for submission.${NC}\n"