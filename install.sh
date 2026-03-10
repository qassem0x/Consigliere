#!/usr/bin/env bash
# =============================================================================
#  Consigliere — Interactive Setup Script
#  Run once before starting the application for the first time.
# =============================================================================

set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

# ── Helpers ───────────────────────────────────────────────────────────────────
info()    { echo -e "${CYAN}${BOLD}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}${BOLD}[ OK ]${NC}  $*"; }
warn()    { echo -e "${YELLOW}${BOLD}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}${BOLD}[ERR ]${NC}  $*" >&2; }
section() { echo -e "\n${BOLD}${BLUE}━━━  $*  ━━━${NC}\n"; }

prompt_required() {
    # prompt_required VAR "Prompt text" [default]
    local var="$1" msg="$2" default="${3:-}"
    local val=""
    while [[ -z "$val" ]]; do
        if [[ -n "$default" ]]; then
            read -rp "  ${msg} [${default}]: " val
            val="${val:-$default}"
        else
            read -rp "  ${msg}: " val
        fi
        [[ -z "$val" ]] && warn "This field is required."
    done
    printf -v "$var" '%s' "$val"
}

prompt_secret() {
    # prompt_secret VAR "Prompt text"
    local var="$1" msg="$2" val=""
    while [[ -z "$val" ]]; do
        read -rsp "  ${msg}: " val
        echo
        [[ -z "$val" ]] && warn "This field is required."
    done
    printf -v "$var" '%s' "$val"
}

prompt_optional() {
    # prompt_optional VAR "Prompt text"
    local var="$1" msg="$2" val=""
    read -rp "  ${msg} (leave blank to skip): " val
    printf -v "$var" '%s' "$val"
}

generate_secret_key() {
    python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null \
        || openssl rand -hex 32 2>/dev/null \
        || head -c 32 /dev/urandom | xxd -p | tr -d '\n'
}

generate_fernet_key() {
    python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null \
        || python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
}

# ── Banner ────────────────────────────────────────────────────────────────────
clear
echo -e "${BOLD}${BLUE}"
cat << 'BANNER'
   ____                _       _리에
  / ___|___  _ __  ___(_) __ _| (_) ___ _ __ ___
 | |   / _ \| '_ \/ __| |/ _` | | |/ _ \ '__/ _ \
 | |__| (_) | | | \__ \ | (_| | | |  __/ | |  __/
  \____\___/|_| |_|___/_|\__, |_|_|\___|_|  \___|
                          |___/
BANNER
echo -e "${NC}"
echo -e "  ${BOLD}Self-Hosted AI Data Analysis Platform — Setup Wizard${NC}"
echo -e "  ─────────────────────────────────────────────────────"

# ── Check prerequisites ───────────────────────────────────────────────────────
section "Checking Prerequisites"

MISSING=()
command -v docker   &>/dev/null && success "Docker found"       || MISSING+=("docker")
command -v python3  &>/dev/null && success "Python 3 found"     || MISSING+=("python3")

if ! docker compose version &>/dev/null 2>&1; then
    MISSING+=("docker-compose-plugin")
fi
[[ ${#MISSING[@]} -eq 0 ]] && success "Docker Compose found" || true

if [[ ${#MISSING[@]} -gt 0 ]]; then
    error "Missing required tools: ${MISSING[*]}"
    error "Install them and re-run this script."
    exit 1
fi

if [[ ! -f ".env.example" ]]; then
    error "Run this script from the Consigliere project root."
    exit 1
fi

if [[ -f ".env" ]]; then
    warn ".env already exists."
    read -rp "  Overwrite it? [y/N]: " OVERWRITE
    [[ "${OVERWRITE,,}" != "y" ]] && { info "Keeping existing .env. Exiting."; exit 0; }
fi

# ── LLM Provider & Model ─────────────────────────────────────────────────────
section "LLM Provider & Model Selection"

echo -e "  Select your model (powered by LiteLLM):\n"
echo -e "  ${BOLD}OpenAI Models:${NC}"
echo -e "   ${BOLD}1)${NC} gpt-4o           (recommended - balanced)"
echo -e "   ${BOLD}2)${NC} gpt-4o-mini      (fast, cost-effective)"
echo -e "\n  ${BOLD}Anthropic Models:${NC}"
echo -e "   ${BOLD}3)${NC} claude-sonnet-4-5   (strong reasoning)"
echo -e "   ${BOLD}4)${NC} claude-haiku-4-5    (fast, lightweight)"
echo -e "\n  ${BOLD}Google Models:${NC}"
echo -e "   ${BOLD}5)${NC} gemini-2.0-flash-001    (fast, multimodal)"
echo -e "   ${BOLD}6)${NC} gemini-1.5-pro           (long context)"
echo -e "\n  ${BOLD}Other Providers:${NC}"
echo -e "   ${BOLD}7)${NC} meta-llama/llama-3.3-70b-instruct  (open-source)"
echo -e "   ${BOLD}8)${NC} deepseek/deepseek-chat            (reasoning)"
echo -e "   ${BOLD}9)${NC} mistral/mistral-large             (general purpose)"
echo -e "  ${BOLD}10)${NC} xai/grok-3                        (fast reasoning)"
echo -e "  ${BOLD}11)${NC} Custom model (enter name manually)"
echo -e "\n  ${CYAN}Full model list: https://models.litellm.ai/${NC}\n"

MODEL_CHOICE=""
while [[ ! "$MODEL_CHOICE" =~ ^[0-9]+$ ]] || [[ "$MODEL_CHOICE" -lt 1 ]] || [[ "$MODEL_CHOICE" -gt 11 ]]; do
    read -rp "  Choice [1-11]: " MODEL_CHOICE
    MODEL_CHOICE="${MODEL_CHOICE:-1}"
done

OPENAI_API_KEY="" ANTHROPIC_API_KEY="" GEMINI_API_KEY="" DEEPSEEK_API_KEY="" MISTRAL_API_KEY="" XAI_API_KEY=""

case "$MODEL_CHOICE" in
    1) MODEL_NAME="openai/gpt-4o" ;;
    2) MODEL_NAME="openai/gpt-4o-mini" ;;
    3) MODEL_NAME="anthropic/claude-sonnet-4-5" ;;
    4) MODEL_NAME="anthropic/claude-haiku-4-5" ;;
    5) MODEL_NAME="google/gemini-2.0-flash-001" ;;
    6) MODEL_NAME="google/gemini-1.5-pro" ;;
    7) MODEL_NAME="meta-llama/llama-3.3-70b-instruct" ;;
    8) MODEL_NAME="deepseek/deepseek-chat" ;;
    9) MODEL_NAME="mistral/mistral-large" ;;
    10) MODEL_NAME="xai/grok-3" ;;
    11) prompt_required MODEL_NAME "Full model name (e.g. openai/gpt-4o)" ;;
esac

PROVIDER="${MODEL_NAME%%/*}"

case "$PROVIDER" in
    openai)
        echo -e "\n  Get your API key at ${CYAN}https://platform.openai.com/api-keys${NC}"
        prompt_secret OPENAI_API_KEY "OpenAI API Key"
        ;;
    anthropic)
        echo -e "\n  Get your API key at ${CYAN}https://console.anthropic.com/settings/keys${NC}"
        prompt_secret ANTHROPIC_API_KEY "Anthropic API Key"
        ;;
    google)
        echo -e "\n  Get your API key at ${CYAN}https://aistudio.google.com/app/apikey${NC}"
        prompt_secret GEMINI_API_KEY "Gemini API Key"
        ;;
    deepseek)
        echo -e "\n  Get your API key at ${CYAN}https://platform.deepseek.com/${NC}"
        prompt_secret DEEPSEEK_API_KEY "DeepSeek API Key"
        ;;
    mistral)
        echo -e "\n  Get your API key at ${CYAN}https://console.mistral.ai/${NC}"
        prompt_secret MISTRAL_API_KEY "Mistral API Key"
        ;;
    xai)
        echo -e "\n  Get your API key at ${CYAN}https://console.x.ai/${NC}"
        prompt_secret XAI_API_KEY "xAI API Key"
        ;;
    meta-llama)
        echo -e "\n  ${YELLOW}Note: Meta Llama via API requires a provider like Together.ai or Cerebras${NC}"
        echo -e "  Get your API key at ${CYAN}https://together.ai/${NC}"
        prompt_secret OPENAI_API_KEY "Together.ai API Key"
        MODEL_NAME="together_ai/meta-llama/Llama-3.3-70B-Instruct"
        ;;
    *)
        echo -e "\n  ${YELLOW}Please provide the required API keys.${NC}\n"
        prompt_optional OPENAI_API_KEY      "OpenAI API Key     "
        prompt_optional ANTHROPIC_API_KEY   "Anthropic API Key  "
        prompt_optional GEMINI_API_KEY      "Gemini API Key     "
        prompt_optional DEEPSEEK_API_KEY    "DeepSeek API Key   "
        prompt_optional MISTRAL_API_KEY     "Mistral API Key    "
        prompt_optional XAI_API_KEY         "xAI API Key        "
        ;;
esac

success "Model configured: ${BOLD}${MODEL_NAME}${NC}"

# ── Database credentials ──────────────────────────────────────────────────────
section "Database Configuration"

echo -e "  PostgreSQL credentials (used internally by Docker).\n"
prompt_required DB_USER     "DB username" "consigliere"
prompt_secret   DB_PASSWORD "DB password"
prompt_required DB_NAME     "DB name" "consigliere"

DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}"
success "Database URL set."

# ── pgAdmin (optional) ────────────────────────────────────────────────────────
section "pgAdmin Configuration (Optional)"
echo -e "  pgAdmin is a web UI for browsing your database at ${CYAN}http://localhost:5050${NC}.\n"
read -rp "  Configure pgAdmin? [Y/n]: " PGA_CHOICE; PGA_CHOICE="${PGA_CHOICE:-Y}"

if [[ "${PGA_CHOICE,,}" == "y" ]]; then
    prompt_required PGA_EMAIL    "pgAdmin email"    "admin@admin.com"
    prompt_secret   PGA_PASSWORD "pgAdmin password"
else
    PGA_EMAIL="admin@admin.com"
    PGA_PASSWORD="admin"
    info "Using default pgAdmin credentials (admin@admin.com / admin)."
fi

# ── Generate crypto secrets ───────────────────────────────────────────────────
section "Generating Cryptographic Keys"

info "Generating SECRET_KEY..."
SECRET_KEY="$(generate_secret_key)"
success "SECRET_KEY generated."

info "Generating ENCRYPTION_KEY (Fernet)..."
ENCRYPTION_KEY="$(generate_fernet_key)"
success "ENCRYPTION_KEY generated."

# ── Write .env ────────────────────────────────────────────────────────────────
section "Writing .env"

cat > .env << EOF
# Consigliere — generated by install.sh on $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Do NOT commit this file to version control.

# ── App secrets ───────────────────────────────────────────────────────────────
SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# ── LLM ──────────────────────────────────────────────────────────────────────
MODEL_NAME=${MODEL_NAME}
OPENAI_API_KEY=${OPENAI_API_KEY}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
GEMINI_API_KEY=${GEMINI_API_KEY}
DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
MISTRAL_API_KEY=${MISTRAL_API_KEY}
XAI_API_KEY=${XAI_API_KEY}

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL=${DATABASE_URL}
POSTGRES_USER=${DB_USER}
POSTGRES_PASSWORD=${DB_PASSWORD}
POSTGRES_DB=${DB_NAME}

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ORIGINS=http://localhost

# ── pgAdmin ───────────────────────────────────────────────────────────────────
PGADMIN_EMAIL=${PGA_EMAIL}
PGADMIN_PASSWORD=${PGA_PASSWORD}
EOF

success ".env written successfully."

# ── Summary ───────────────────────────────────────────────────────────────────
section "Setup Complete"

echo -e "  ${BOLD}Configuration Summary${NC}"
echo -e "  ─────────────────────────────────────────"
echo -e "  Model:         ${CYAN}${MODEL_NAME}${NC}"
echo -e "  Database:      ${CYAN}postgresql://${DB_USER}:***@db:5432/${DB_NAME}${NC}"
echo -e "  pgAdmin:       ${CYAN}http://localhost:5050${NC}  (${PGA_EMAIL})"
echo -e "  App URL:       ${CYAN}http://localhost${NC}"
echo -e "  ─────────────────────────────────────────\n"

# ── Launch ────────────────────────────────────────────────────────────────────
read -rp "  Launch Consigliere now with Docker Compose? [Y/n]: " LAUNCH
LAUNCH="${LAUNCH:-Y}"

if [[ "${LAUNCH,,}" == "y" ]]; then
    echo ""
    info "Building and starting all services (this may take a few minutes)..."
    echo ""
    docker compose up --build -d
    echo ""
    success "Consigliere is running!"
    echo ""
    echo -e "  ${BOLD}Access:${NC}"
    echo -e "    🌐 App    → ${CYAN}http://localhost${NC}"
    echo -e "    🗄️  pgAdmin → ${CYAN}http://localhost:5050${NC}"
    echo ""
    echo -e "  To view logs:  ${BOLD}docker compose logs -f${NC}"
    echo -e "  To stop:       ${BOLD}docker compose down${NC}"
else
    echo ""
    info "To start later, run:"
    echo -e "    ${BOLD}docker compose up --build -d${NC}"
fi

echo ""
