#!/bin/bash
# =============================================================================
# SAKSHI - Kali Linux Full Deployment Script
# Run this on your Kali VM:
#   bash <(curl -fsSL https://raw.githubusercontent.com/Anshuman-VR/Sakshi/main/scripts/setup_kali.sh)
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()    { echo -e "${BLUE}[SAKSHI]${NC} $1"; }
success(){ echo -e "${GREEN}[OK]${NC} $1"; }
warn()   { echo -e "${YELLOW}[WARN]${NC} $1"; }

echo ""
echo "  ███████╗ █████╗ ██╗  ██╗███████╗██╗  ██╗██╗"
echo "  ██╔════╝██╔══██╗██║ ██╔╝██╔════╝██║  ██║██║"
echo "  ███████╗███████║█████╔╝ ███████╗███████║██║"
echo "  ╚════██║██╔══██║██╔═██╗ ╚════██║██╔══██║██║"
echo "  ███████║██║  ██║██║  ██╗███████║██║  ██║██║"
echo "  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝"
echo "  ZK-ML Contract Conformance for Digital Lending"
echo "  ─────────────────────────────────────────────"
echo ""

# Step 0: Remove any broken Docker repo from get.docker.com
log "Cleaning up any broken Docker repo entries..."
sudo rm -f /etc/apt/sources.list.d/docker.list
sudo apt-get update -qq
success "APT sources cleaned."

# Step 1: Install Docker from Kali own repository
log "Installing Docker (docker.io from kali-rolling)..."
sudo apt-get install -y docker.io docker-compose-plugin
sudo systemctl start docker
sudo systemctl enable docker
success "Docker installed: $(docker --version)"
success "Docker Compose installed: $(docker compose version)"

# Step 2: Add current user to docker group
log "Adding $USER to docker group..."
sudo usermod -aG docker "$USER"
success "User $USER added to docker group."

# Step 3: Install Python 3 + pip + httpx
log "Installing Python 3 + pip + httpx..."
sudo apt-get install -y python3 python3-pip
pip3 install --quiet httpx
success "Python $(python3 --version) ready."

# Step 4: Install ngrok
log "Installing ngrok..."
if ! command -v ngrok &>/dev/null; then
  curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
    | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
  echo "deb https://ngrok-agent.s3.amazonaws.com buster main" \
    | sudo tee /etc/apt/sources.list.d/ngrok.list >/dev/null
  sudo apt-get update -qq
  sudo apt-get install -y ngrok
  success "ngrok installed: $(ngrok --version)"
else
  success "ngrok already installed: $(ngrok --version)"
fi

# Step 5: Clone or update the Sakshi repo
REPO_URL="https://github.com/Anshuman-VR/Sakshi.git"
REPO_DIR="$HOME/Sakshi"

if [ -d "$REPO_DIR/.git" ]; then
  log "Repo already exists at $REPO_DIR pulling latest..."
  git -C "$REPO_DIR" pull origin main
else
  log "Cloning Sakshi repository..."
  git clone "$REPO_URL" "$REPO_DIR"
fi
success "Repo ready at $REPO_DIR"

# Step 6: Build and start the 2 Docker containers
log "Building and starting containers (this may take 3-5 minutes on first run)..."
cd "$REPO_DIR"
sg docker -c "docker compose -f deploy/docker-compose.yml up -d --build"
success "Containers started."

# Step 7: Wait for health checks
log "Waiting for containers to become healthy (up to 90s)..."
for i in $(seq 1 18); do
  LENDER_STATUS=$(sg docker -c "docker inspect --format={{.State.Health.Status}} sakshi-lender" 2>/dev/null || echo "starting")
  if [ "$LENDER_STATUS" = "healthy" ]; then
    success "sakshi-lender is healthy!"
    break
  fi
  echo "  ... ($i/18) current: $LENDER_STATUS"
  sleep 5
done

# Step 8: Seed the database
log "Seeding database with demo data..."
python3 "$REPO_DIR/scripts/reset_demo.py" || warn "Seed failed - run manually: python3 ~/Sakshi/scripts/reset_demo.py"

# Done
echo ""
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  SAKSHI IS LIVE!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo ""
echo "  Intranet Access (anyone on college LAN):"
echo "     http://172.20.88.119:8000             Lender Dashboard"
echo "     http://172.20.88.119:8000/borrower    Borrower Portal"
echo "     http://172.20.88.119:8000/demo         Demo Lab"
echo "     http://172.20.88.119:8000/ledger       Audit Ledger"
echo "     http://172.20.88.119:8000/docs         API Swagger"
echo ""
echo "  To expose on the public internet (run in a new terminal):"
echo "     1. ngrok config add-authtoken <YOUR_TOKEN>"
echo "        (token from: https://dashboard.ngrok.com/get-started/your-authtoken)"
echo "     2. ngrok http 8000"
echo "     3. Copy the https://xxxxx.ngrok-free.app URL"
echo ""
echo "  Useful commands:"
echo "     docker compose -f ~/Sakshi/deploy/docker-compose.yml logs -f"
echo "     docker compose -f ~/Sakshi/deploy/docker-compose.yml ps"
echo "     docker compose -f ~/Sakshi/deploy/docker-compose.yml down"
echo ""