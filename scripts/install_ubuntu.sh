#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Autixx/WGD_AWG_fix_multihop.git}"
GIT_REF="${GIT_REF:-main}"
INSTALL_DIR="${INSTALL_DIR:-/opt/wgd-awg-multihop}"
CONFIG_DIR="${CONFIG_DIR:-/etc/wgdashboard}"
SERVICE_NAME="${SERVICE_NAME:-wg-dashboard}"
BOOTSTRAP_INBOUND="${BOOTSTRAP_INBOUND:-}"
BOOTSTRAP_PROTOCOL="${BOOTSTRAP_PROTOCOL:-wg}"
BOOTSTRAP_ADDRESS="${BOOTSTRAP_ADDRESS:-10.66.66.1/24}"
BOOTSTRAP_LISTEN_PORT="${BOOTSTRAP_LISTEN_PORT:-51820}"
BOOTSTRAP_OUT_IF="${BOOTSTRAP_OUT_IF:-}"
BOOTSTRAP_DNS="${BOOTSTRAP_DNS:-1.1.1.1,1.0.0.1}"
BOOTSTRAP_FORCE="${BOOTSTRAP_FORCE:-false}"
BOOTSTRAP_START="${BOOTSTRAP_START:-true}"
AWG_JC="${AWG_JC:-0}"
AWG_JMIN="${AWG_JMIN:-0}"
AWG_JMAX="${AWG_JMAX:-0}"
AWG_S1="${AWG_S1:-0}"
AWG_S2="${AWG_S2:-0}"
AWG_S3="${AWG_S3:-0}"
AWG_S4="${AWG_S4:-0}"
AWG_H1="${AWG_H1:-1}"
AWG_H2="${AWG_H2:-2}"
AWG_H3="${AWG_H3:-3}"
AWG_H4="${AWG_H4:-4}"

usage() {
  cat <<'EOF'
Usage: sudo bash scripts/install_ubuntu.sh [options]

Options:
  --repo-url <url>        Git repository URL
  --ref <branch|tag|sha>  Git ref to checkout (default: main)
  --install-dir <path>    Project install directory (default: /opt/wgd-awg-multihop)
  --config-dir <path>     Runtime config dir (default: /etc/wgdashboard)
  --service-name <name>   systemd unit name without suffix (default: wg-dashboard)
  --bootstrap-inbound <name>
                           Create inbound interface config (example: wg0 / awg0)
  --bootstrap-protocol <wg|awg>
                           Protocol for bootstrap inbound (default: wg)
  --bootstrap-address <cidr>
                           Interface address/CIDR (default: 10.66.66.1/24)
  --bootstrap-listen-port <port>
                           Listen port for inbound (default: 51820)
  --bootstrap-out-if <iface>
                           Outbound NIC for NAT; auto-detected by default route
  --bootstrap-dns <dns1,dns2>
                           DNS pushed to peers by default template
  --bootstrap-force        Overwrite existing inbound config if it already exists
  --no-bootstrap-start     Create config but do not bring interface up
  --awg-jc <num>           AWG2.0 Jc value (default: 0)
  --awg-jmin <num>         AWG2.0 Jmin value (default: 0)
  --awg-jmax <num>         AWG2.0 Jmax value (default: 0)
  --awg-s1 <num>           AWG2.0 S1 value (default: 0)
  --awg-s2 <num>           AWG2.0 S2 value (default: 0)
  --awg-s3 <num>           AWG2.0 S3 value (default: 0)
  --awg-s4 <num>           AWG2.0 S4 value (default: 0)
  --awg-h1 <num>           AWG2.0 H1 value (default: 1)
  --awg-h2 <num>           AWG2.0 H2 value (default: 2)
  --awg-h3 <num>           AWG2.0 H3 value (default: 3)
  --awg-h4 <num>           AWG2.0 H4 value (default: 4)
  -h, --help              Show help
EOF
}

fail() {
  echo "$*" >&2
  exit 1
}

validate_port() {
  local value="$1"
  [[ "${value}" =~ ^[0-9]{1,5}$ ]] || return 1
  ((value >= 1 && value <= 65535))
}

validate_int() {
  local value="$1"
  [[ "${value}" =~ ^-?[0-9]+$ ]]
}

create_bootstrap_inbound() {
  local interface_name="$1"
  local protocol="$2"
  local address_cidr="$3"
  local listen_port="$4"
  local out_if="$5"
  local dns_value="$6"
  local force="$7"
  local should_start="$8"
  local conf_dir conf_path quick_bin nat_subnet private_key public_key service_unit
  local awg_jc="$9"
  local awg_jmin="${10}"
  local awg_jmax="${11}"
  local awg_s1="${12}"
  local awg_s2="${13}"
  local awg_s3="${14}"
  local awg_s4="${15}"
  local awg_h1="${16}"
  local awg_h2="${17}"
  local awg_h3="${18}"
  local awg_h4="${19}"

  [[ "${interface_name}" =~ ^[a-zA-Z0-9_.-]{1,15}$ ]] || fail "[bootstrap] Invalid interface name: ${interface_name}"
  [[ "${protocol}" == "wg" || "${protocol}" == "awg" ]] || fail "[bootstrap] Protocol must be wg or awg."
  validate_port "${listen_port}" || fail "[bootstrap] Invalid port: ${listen_port}"
  for numeric in "${awg_jc}" "${awg_jmin}" "${awg_jmax}" "${awg_s1}" "${awg_s2}" "${awg_s3}" "${awg_s4}" "${awg_h1}" "${awg_h2}" "${awg_h3}" "${awg_h4}"; do
    validate_int "${numeric}" || fail "[bootstrap] AWG parameters must be integer values."
  done

  quick_bin="${protocol}-quick"
  command -v "${quick_bin}" >/dev/null 2>&1 || fail "[bootstrap] ${quick_bin} is not installed."
  command -v wg >/dev/null 2>&1 || fail "[bootstrap] wg binary is required for key generation."

  if [[ "${protocol}" == "wg" ]]; then
    conf_dir="/etc/wireguard"
  else
    conf_dir="/etc/amnezia/amneziawg"
  fi
  mkdir -p "${conf_dir}"
  conf_path="${conf_dir}/${interface_name}.conf"

  if [[ -z "${out_if}" ]]; then
    out_if="$(ip -o -4 route show to default | awk '{print $5}' | head -n 1)"
  fi
  [[ -n "${out_if}" ]] || fail "[bootstrap] Failed to detect outbound NIC. Use --bootstrap-out-if."

  nat_subnet="$(python3 - <<PY
import ipaddress
print(ipaddress.ip_interface("${address_cidr}").network)
PY
)"

  private_key="$(wg genkey)"
  public_key="$(printf '%s' "${private_key}" | wg pubkey)"

  if [[ -f "${conf_path}" && "${force}" != "true" ]]; then
    fail "[bootstrap] ${conf_path} already exists. Use --bootstrap-force to overwrite."
  fi

  umask 077
  cat > "${conf_path}" <<EOF
[Interface]
PrivateKey = ${private_key}
Address = ${address_cidr}
ListenPort = ${listen_port}
DNS = ${dns_value}
PostUp = iptables -t nat -A POSTROUTING -s ${nat_subnet} -o ${out_if} -j MASQUERADE; iptables -A FORWARD -i ${interface_name} -j ACCEPT; iptables -A FORWARD -o ${interface_name} -j ACCEPT
PreDown = iptables -t nat -D POSTROUTING -s ${nat_subnet} -o ${out_if} -j MASQUERADE; iptables -D FORWARD -i ${interface_name} -j ACCEPT; iptables -D FORWARD -o ${interface_name} -j ACCEPT
SaveConfig = false
EOF
  if [[ "${protocol}" == "awg" ]]; then
    cat >> "${conf_path}" <<EOF
Jc = ${awg_jc}
Jmin = ${awg_jmin}
Jmax = ${awg_jmax}
S1 = ${awg_s1}
S2 = ${awg_s2}
S3 = ${awg_s3}
S4 = ${awg_s4}
H1 = ${awg_h1}
H2 = ${awg_h2}
H3 = ${awg_h3}
H4 = ${awg_h4}
EOF
  fi
  chmod 600 "${conf_path}"

  cat > /etc/sysctl.d/99-wgd-forward.conf <<'EOF'
net.ipv4.ip_forward=1
net.ipv6.conf.all.forwarding=1
EOF
  sysctl -p /etc/sysctl.d/99-wgd-forward.conf >/dev/null

  if [[ "${should_start}" == "true" ]]; then
    "${quick_bin}" down "${conf_path}" >/dev/null 2>&1 || true
    "${quick_bin}" up "${conf_path}"
    service_unit="${quick_bin}@${interface_name}.service"
    if systemctl list-unit-files --type=service | awk '{print $1}' | grep -qx "${service_unit}"; then
      systemctl enable "${service_unit}" >/dev/null 2>&1 || true
    fi
  fi

  echo
  echo "[bootstrap] Inbound interface created:"
  echo "  Name:       ${interface_name}"
  echo "  Protocol:   ${protocol}"
  echo "  Config:     ${conf_path}"
  echo "  ListenPort: ${listen_port}"
  echo "  Address:    ${address_cidr}"
  echo "  NAT via:    ${out_if}"
  echo "  PublicKey:  ${public_key}"
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
    --bootstrap-inbound)
      BOOTSTRAP_INBOUND="$2"
      shift 2
      ;;
    --bootstrap-protocol)
      BOOTSTRAP_PROTOCOL="$2"
      shift 2
      ;;
    --bootstrap-address)
      BOOTSTRAP_ADDRESS="$2"
      shift 2
      ;;
    --bootstrap-listen-port)
      BOOTSTRAP_LISTEN_PORT="$2"
      shift 2
      ;;
    --bootstrap-out-if)
      BOOTSTRAP_OUT_IF="$2"
      shift 2
      ;;
    --bootstrap-dns)
      BOOTSTRAP_DNS="$2"
      shift 2
      ;;
    --bootstrap-force)
      BOOTSTRAP_FORCE="true"
      shift 1
      ;;
    --no-bootstrap-start)
      BOOTSTRAP_START="false"
      shift 1
      ;;
    --awg-jc)
      AWG_JC="$2"
      shift 2
      ;;
    --awg-jmin)
      AWG_JMIN="$2"
      shift 2
      ;;
    --awg-jmax)
      AWG_JMAX="$2"
      shift 2
      ;;
    --awg-s1)
      AWG_S1="$2"
      shift 2
      ;;
    --awg-s2)
      AWG_S2="$2"
      shift 2
      ;;
    --awg-s3)
      AWG_S3="$2"
      shift 2
      ;;
    --awg-s4)
      AWG_S4="$2"
      shift 2
      ;;
    --awg-h1)
      AWG_H1="$2"
      shift 2
      ;;
    --awg-h2)
      AWG_H2="$2"
      shift 2
      ;;
    --awg-h3)
      AWG_H3="$2"
      shift 2
      ;;
    --awg-h4)
      AWG_H4="$2"
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

echo "[1/8] Installing OS dependencies..."
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

echo "[2/8] Fetching project source..."
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

echo "[3/8] Preparing runtime directories..."
mkdir -p "${SRC_DIR}/log" "${SRC_DIR}/download"
mkdir -p "${CONFIG_DIR}/db" "${CONFIG_DIR}/letsencrypt/work-dir" "${CONFIG_DIR}/letsencrypt/config-dir"

if [[ ! -f "${SRC_DIR}/ssl-tls.ini" ]]; then
  cat > "${SRC_DIR}/ssl-tls.ini" <<'EOF'
[SSL/TLS]
certificate_path =
private_key_path =
EOF
fi

echo "[4/8] Creating Python virtualenv..."
python3 -m venv "${SRC_DIR}/venv"

echo "[5/8] Installing Python dependencies..."
"${SRC_DIR}/venv/bin/python3" -m pip install --upgrade pip wheel setuptools
"${SRC_DIR}/venv/bin/python3" -m pip install -r "${SRC_DIR}/requirements.txt"

chmod +x "${SRC_DIR}/wgd.sh"

echo "[6/8] Installing systemd service..."
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

echo "[7/8] Enabling and starting service..."
systemctl daemon-reload
systemctl enable --now "${SERVICE_NAME}.service"

echo "[8/8] Optional inbound bootstrap..."
if [[ -n "${BOOTSTRAP_INBOUND}" ]]; then
  create_bootstrap_inbound \
    "${BOOTSTRAP_INBOUND}" \
    "${BOOTSTRAP_PROTOCOL}" \
    "${BOOTSTRAP_ADDRESS}" \
    "${BOOTSTRAP_LISTEN_PORT}" \
    "${BOOTSTRAP_OUT_IF}" \
    "${BOOTSTRAP_DNS}" \
    "${BOOTSTRAP_FORCE}" \
    "${BOOTSTRAP_START}" \
    "${AWG_JC}" \
    "${AWG_JMIN}" \
    "${AWG_JMAX}" \
    "${AWG_S1}" \
    "${AWG_S2}" \
    "${AWG_S3}" \
    "${AWG_S4}" \
    "${AWG_H1}" \
    "${AWG_H2}" \
    "${AWG_H3}" \
    "${AWG_H4}"
else
  echo "[bootstrap] skipped (use --bootstrap-inbound <name> to enable)"
fi

echo
echo "Installation complete."
echo "Service: ${SERVICE_NAME}.service"
echo "Status:  systemctl status ${SERVICE_NAME}.service --no-pager"
echo "Logs:    journalctl -u ${SERVICE_NAME}.service -f"
echo "Config:  ${CONFIG_DIR}/wg-dashboard.ini"
echo "URL:     http://<server-ip>:10086"
