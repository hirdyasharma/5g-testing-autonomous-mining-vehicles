#!/bin/bash
# ============================================================
# COMP6016 — Complete Fresh Ubuntu Setup Script
# 5G Security Testing for Autonomous Mining Vehicles
# Hirdya Sharma (21749180)
#
# Run this on a brand new Ubuntu system:
#   chmod +x setup.sh
#   sudo bash setup.sh
#
# This script:
#   1. Installs Docker + Docker Compose
#   2. Fixes all permissions and network settings
#   3. Pulls all Docker images
#   4. Starts the full stack
#   5. Verifies everything is running
# ============================================================

set -e  # Exit on any error

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${GREEN}[OK]${NC} $1"; }
info() { echo -e "${BLUE}[..] $1${NC}"; }
warn() { echo -e "${YELLOW}[!!] $1${NC}"; }
err()  { echo -e "${RED}[ERROR] $1${NC}"; exit 1; }

echo ""
echo "============================================================"
echo " COMP6016 — Fresh Ubuntu Setup"
echo " 5G Security Testing for Autonomous Mining Vehicles"
echo " Hirdya Sharma (21749180)"
echo "============================================================"
echo ""

# ── Must run as root ──────────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
  err "Please run as root: sudo bash setup.sh"
fi

# Get the actual user (not root)
ACTUAL_USER="${SUDO_USER:-$(logname 2>/dev/null || echo $USER)}"
HOME_DIR=$(eval echo "~$ACTUAL_USER")
log "Running as root, will configure for user: $ACTUAL_USER"

# ── STEP 1: System update ─────────────────────────────────────
info "Step 1/7 — Updating system packages..."
apt-get update -qq
apt-get install -y -qq \
  curl wget git unzip ca-certificates \
  gnupg lsb-release apt-transport-https \
  python3 python3-pip net-tools \
  > /dev/null 2>&1
log "System packages installed"

# ── STEP 2: Install Docker ────────────────────────────────────
info "Step 2/7 — Installing Docker..."

if command -v docker &> /dev/null; then
  warn "Docker already installed: $(docker --version)"
else
  # Add Docker GPG key
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg

  # Add Docker repository
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null

  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin > /dev/null 2>&1
  log "Docker installed: $(docker --version)"
fi

# ── STEP 3: Docker permissions ────────────────────────────────
info "Step 3/7 — Setting up Docker permissions..."

# Add user to docker group
usermod -aG docker "$ACTUAL_USER"
log "Added $ACTUAL_USER to docker group"

# Start and enable Docker
systemctl start docker
systemctl enable docker > /dev/null 2>&1
log "Docker service started and enabled"

# ── STEP 4: Network and kernel settings ──────────────────────
info "Step 4/7 — Configuring network and kernel settings..."

# Enable IP forwarding (needed for UPF and Docker networking)
echo 'net.ipv4.ip_forward=1' > /etc/sysctl.d/99-5g-mining.conf
echo 'net.ipv6.conf.all.forwarding=1' >> /etc/sysctl.d/99-5g-mining.conf

# Increase inotify watches for Docker
echo 'fs.inotify.max_user_watches=524288' >> /etc/sysctl.d/99-5g-mining.conf
echo 'fs.inotify.max_user_instances=512' >> /etc/sysctl.d/99-5g-mining.conf

sysctl --system > /dev/null 2>&1
log "IP forwarding enabled"

# Load tun module (needed for UPF)
modprobe tun 2>/dev/null || true
echo 'tun' >> /etc/modules-load.d/5g-mining.conf
log "TUN module loaded"

# ── STEP 5: Locate project folder ────────────────────────────
info "Step 5/7 — Locating project folder..."

# Try common locations
PROJECT_DIR=""
for loc in \
  "$HOME_DIR/Downloads/mining5g" \
  "$HOME_DIR/Desktop/mining5g" \
  "$HOME_DIR/mining5g" \
  "/opt/mining5g" \
  "$(find $HOME_DIR -name 'docker-compose.yml' -path '*/mining5g/*' 2>/dev/null | head -1 | xargs dirname 2>/dev/null)"; do
  if [ -f "$loc/docker-compose.yml" ]; then
    PROJECT_DIR="$loc"
    break
  fi
done

if [ -z "$PROJECT_DIR" ]; then
  warn "Could not find project folder automatically."
  echo ""
  echo "Where is your mining5g folder? Enter full path:"
  read -p "Path: " PROJECT_DIR
  if [ ! -f "$PROJECT_DIR/docker-compose.yml" ]; then
    err "docker-compose.yml not found at $PROJECT_DIR"
  fi
fi

log "Project folder found: $PROJECT_DIR"
cd "$PROJECT_DIR"

# Fix ownership
chown -R "$ACTUAL_USER:$ACTUAL_USER" "$PROJECT_DIR"

# Fix permissions on scripts
chmod +x "$PROJECT_DIR"/*.sh 2>/dev/null || true

# ── STEP 6: Pull all Docker images ───────────────────────────
info "Step 6/7 — Pulling Docker images (this takes 5-10 minutes on first run)..."
echo "   Images to pull: mongo, open5gs, ueransim, python, prometheus, grafana, alertmanager, node-exporter"
echo ""

docker compose pull
log "All images pulled"

# ── STEP 7: Start the stack ───────────────────────────────────
info "Step 7/7 — Starting the full stack..."

# Stop any existing stack first
docker compose down 2>/dev/null || true

# Start everything
docker compose up -d
log "Stack started"

# Wait for MongoDB to be ready
echo ""
info "Waiting 45 seconds for services to initialise..."
sleep 45

# Check status
echo ""
echo "============================================================"
echo " Container Status"
echo "============================================================"
docker compose ps

echo ""
echo "============================================================"
echo " Verifying key services"
echo "============================================================"

# Check MEC API
if curl -s http://localhost:5000/health > /dev/null 2>&1; then
  log "MEC Edge API: http://localhost:5000/health - UP"
else
  warn "MEC Edge API not responding yet - may need another 30 seconds"
fi

# Check Prometheus
if curl -s http://localhost:9190/api/v1/targets > /dev/null 2>&1; then
  log "Prometheus: http://localhost:9190 - UP"
else
  warn "Prometheus not responding yet"
fi

# Check Grafana
if curl -s http://localhost:3000 > /dev/null 2>&1; then
  log "Grafana: http://localhost:3000 - UP"
else
  warn "Grafana not responding yet"
fi

# Check telemetry
if curl -s http://localhost:8000/metrics > /dev/null 2>&1; then
  log "Physics Simulator: http://localhost:8000/metrics - UP"
else
  warn "Physics Simulator not responding yet"
fi

echo ""
echo "============================================================"
echo " SETUP COMPLETE"
echo "============================================================"
echo ""
echo "  Grafana Dashboard:  http://localhost:3000"
echo "  Login:              admin / mining5g@secure"
echo ""
echo "  MEC Edge API:       http://localhost:5000/health"
echo "  Prometheus:         http://localhost:9190"
echo "  Physics Metrics:    http://localhost:8000/metrics"
echo ""
echo "  NOTE: Run the following WITHOUT sudo for Docker commands:"
echo "    docker compose ps"
echo "    docker logs telemetry-simulator --tail=20"
echo ""
echo "  If containers are still starting, wait 60 more seconds"
echo "  then run: docker compose ps"
echo ""
echo "  IMPORTANT: Log out and back in for Docker group to take"
echo "  effect (so you can run docker without sudo)"
echo "============================================================"
