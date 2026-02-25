#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Autixx/WGD_AWG_fix_multihop.git}"
GIT_REF="${GIT_REF:-main}"
INSTALL_DIR="${INSTALL_DIR:-/opt/wgd-awg-multihop}"
CONFIG_DIR="${CONFIG_DIR:-/etc/wgdashboard}"
SERVICE_NAME="${SERVICE_NAME:-wg-dashboard}"

usage() {
  cat <<'EOF'
Usage: sudo bash scripts/install_ubuntu.sh [options]

Options:
  --repo-url <url>        Git repository URL
  --ref <branch|tag|sha>  Git ref to checkout (default: main)
  --install-dir <path>    Project install directory (default: /opt/wgd-awg-multihop)
  --config-dir <path>     Runtime config dir (default: /etc/wgdashboard)
  --service-name <name>   systemd unit name without suffix (default: wg-dashboard)
  -h, --help              Show help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-url)
      REPO_URL="$2"
      shift 2
      ;;
    --ref)
      GIT_REF="$2"
      shift 2
      ;;
    --install-dir)
      INSTALL_DIR="$2"
      shift 2
      ;;
    --config-dir)
      CONFIG_DIR="$2"
      shift 2
      ;;
    --service-name)
      SERVICE_NAME="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0"
  exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This installer supports Ubuntu/Debian apt-based systems only."
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

echo "[1/7] Installing OS dependencies..."
apt-get update
apt-get install -y \
  ca-certificates \
  curl \
  git \
  iproute2 \
  iptables \
  net-tools \
  python3 \
  python3-dev \
  python3-pip \
  python3-venv \
  build-essential \
  libffi-dev \
  libssl-dev

if ! command -v wg >/dev/null 2>&1 || ! command -v wg-quick >/dev/null 2>&1; then
  apt-get install -y wireguard wireguard-tools || apt-get install -y wireguard-tools
fi

mkdir -p /etc/wireguard

if ! command -v awg >/dev/null 2>&1 || ! command -v awg-quick >/dev/null 2>&1; then
  echo "[WARN] awg/awg-quick not found. AWG configs will stay unavailable until AWG is installed."
fi

echo "[2/7] Fetching project source..."
if [[ -d "${INSTALL_DIR}/.git" ]]; then
  git -C "${INSTALL_DIR}" fetch --all --tags
else
  mkdir -p "$(dirname "${INSTALL_DIR}")"
  git clone "${REPO_URL}" "${INSTALL_DIR}"
fi

if git -C "${INSTALL_DIR}" rev-parse --verify --quiet "origin/${GIT_REF}" >/dev/null; then
  git -C "${INSTALL_DIR}" checkout -B "${GIT_REF}" "origin/${GIT_REF}"
else
  git -C "${INSTALL_DIR}" checkout "${GIT_REF}"
fi

SRC_DIR="${INSTALL_DIR}/src"
if [[ ! -f "${SRC_DIR}/dashboard.py" ]]; then
  echo "Invalid source layout: ${SRC_DIR}/dashboard.py not found."
  exit 1
fi

echo "[3/7] Preparing runtime directories..."
mkdir -p "${SRC_DIR}/log" "${SRC_DIR}/download"
mkdir -p "${CONFIG_DIR}/db" "${CONFIG_DIR}/letsencrypt/work-dir" "${CONFIG_DIR}/letsencrypt/config-dir"

if [[ ! -f "${SRC_DIR}/ssl-tls.ini" ]]; then
  cat > "${SRC_DIR}/ssl-tls.ini" <<'EOF'
[SSL/TLS]
certificate_path =
private_key_path =
EOF
fi

echo "[4/7] Creating Python virtualenv..."
python3 -m venv "${SRC_DIR}/venv"

echo "[5/7] Installing Python dependencies..."
"${SRC_DIR}/venv/bin/python3" -m pip install --upgrade pip wheel setuptools
"${SRC_DIR}/venv/bin/python3" -m pip install -r "${SRC_DIR}/requirements.txt"

chmod +x "${SRC_DIR}/wgd.sh"

echo "[6/7] Installing systemd service..."
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=WGDashboard (AWG Multi-hop Fork)
After=network-online.target
Wants=network-online.target
ConditionPathIsDirectory=/etc/wireguard

[Service]
Type=forking
Environment=CONFIGURATION_PATH=${CONFIG_DIR}
WorkingDirectory=${SRC_DIR}
PIDFile=${SRC_DIR}/gunicorn.pid
ExecStart=${SRC_DIR}/wgd.sh start
ExecStop=${SRC_DIR}/wgd.sh stop
ExecReload=${SRC_DIR}/wgd.sh restart
TimeoutSec=120
Restart=always
RestartSec=5
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
EOF

echo "[7/7] Enabling and starting service..."
systemctl daemon-reload
systemctl enable --now "${SERVICE_NAME}.service"

echo
echo "Installation complete."
echo "Service: ${SERVICE_NAME}.service"
echo "Status:  systemctl status ${SERVICE_NAME}.service --no-pager"
echo "Logs:    journalctl -u ${SERVICE_NAME}.service -f"
echo "Config:  ${CONFIG_DIR}/wg-dashboard.ini"
echo "URL:     http://<server-ip>:10086"
