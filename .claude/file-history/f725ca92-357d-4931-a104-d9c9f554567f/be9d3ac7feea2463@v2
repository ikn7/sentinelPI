#!/bin/bash
# SentinelPi - Systemd Service Setup Script
# Must be run with sudo

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
INSTALL_DIR="${SENTINELPI_HOME:-$HOME/sentinelpi}"
SERVICE_USER="${SUDO_USER:-$USER}"
SERVICE_NAME="sentinelpi"
DASHBOARD_SERVICE_NAME="sentinelpi-dashboard"

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════╗"
echo "║      SentinelPi Service Configuration          ║"
echo "╚════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Ce script doit être exécuté avec sudo${NC}"
    echo "Usage: sudo $0"
    exit 1
fi

# Find actual home directory
if [ -n "$SUDO_USER" ]; then
    USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    INSTALL_DIR="$USER_HOME/sentinelpi"
fi

echo "Utilisateur: $SERVICE_USER"
echo "Répertoire: $INSTALL_DIR"
echo ""

# Check installation
if [ ! -f "$INSTALL_DIR/pyproject.toml" ]; then
    echo -e "${RED}SentinelPi n'est pas installé dans $INSTALL_DIR${NC}"
    echo "Exécutez d'abord scripts/install.sh"
    exit 1
fi

# Create main service
create_main_service() {
    echo -e "${BLUE}Création du service principal...${NC}"

    cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=SentinelPi - Station de veille automatisée
Documentation=https://github.com/sentinelpi/sentinelpi
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${INSTALL_DIR}
Environment="PATH=${INSTALL_DIR}/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=${INSTALL_DIR}"
Environment="SENTINELPI_HOME=${INSTALL_DIR}"
ExecStart=${INSTALL_DIR}/.venv/bin/python -m src.main
Restart=always
RestartSec=10

# Hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=${INSTALL_DIR}/data ${INSTALL_DIR}/logs

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${SERVICE_NAME}

[Install]
WantedBy=multi-user.target
EOF

    echo -e "${GREEN}  ✓ Service ${SERVICE_NAME} créé${NC}"
}

# Create dashboard service
create_dashboard_service() {
    echo -e "${BLUE}Création du service dashboard...${NC}"

    cat > /etc/systemd/system/${DASHBOARD_SERVICE_NAME}.service << EOF
[Unit]
Description=SentinelPi Dashboard - Interface web
Documentation=https://github.com/sentinelpi/sentinelpi
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${INSTALL_DIR}
Environment="PATH=${INSTALL_DIR}/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=${INSTALL_DIR}"
Environment="SENTINELPI_HOME=${INSTALL_DIR}"
ExecStart=${INSTALL_DIR}/.venv/bin/streamlit run ${INSTALL_DIR}/src/dashboard/app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true
Restart=always
RestartSec=10

# Hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=${INSTALL_DIR}/data ${INSTALL_DIR}/logs

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${DASHBOARD_SERVICE_NAME}

[Install]
WantedBy=multi-user.target
EOF

    echo -e "${GREEN}  ✓ Service ${DASHBOARD_SERVICE_NAME} créé${NC}"
}

# Create timer for periodic tasks (alternative to internal scheduler)
create_timer() {
    echo -e "${BLUE}Création du timer de collecte...${NC}"

    # Timer unit
    cat > /etc/systemd/system/${SERVICE_NAME}-collect.timer << EOF
[Unit]
Description=SentinelPi Collection Timer
Documentation=https://github.com/sentinelpi/sentinelpi

[Timer]
OnBootSec=2min
OnUnitActiveSec=15min
Unit=${SERVICE_NAME}-collect.service

[Install]
WantedBy=timers.target
EOF

    # Service unit for timer
    cat > /etc/systemd/system/${SERVICE_NAME}-collect.service << EOF
[Unit]
Description=SentinelPi Collection Run
Documentation=https://github.com/sentinelpi/sentinelpi

[Service]
Type=oneshot
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${INSTALL_DIR}
Environment="PATH=${INSTALL_DIR}/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=${INSTALL_DIR}"
ExecStart=${INSTALL_DIR}/.venv/bin/python -c "import asyncio; from src.scheduler import get_scheduler; asyncio.run(get_scheduler().run_now())"

# Hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=${INSTALL_DIR}/data ${INSTALL_DIR}/logs
EOF

    echo -e "${GREEN}  ✓ Timer de collecte créé${NC}"
}

# Enable and start services
enable_services() {
    echo -e "${BLUE}Activation des services...${NC}"

    # Reload systemd
    systemctl daemon-reload

    # Enable services
    systemctl enable ${SERVICE_NAME}.service
    systemctl enable ${DASHBOARD_SERVICE_NAME}.service

    echo -e "${GREEN}  ✓ Services activés${NC}"
}

# Start services
start_services() {
    echo -e "${BLUE}Démarrage des services...${NC}"

    systemctl start ${SERVICE_NAME}.service
    systemctl start ${DASHBOARD_SERVICE_NAME}.service

    # Wait a moment for services to start
    sleep 3

    # Check status
    if systemctl is-active --quiet ${SERVICE_NAME}.service; then
        echo -e "${GREEN}  ✓ ${SERVICE_NAME} démarré${NC}"
    else
        echo -e "${YELLOW}  ⚠ ${SERVICE_NAME} n'a pas démarré correctement${NC}"
        echo "    Consultez: journalctl -u ${SERVICE_NAME} -f"
    fi

    if systemctl is-active --quiet ${DASHBOARD_SERVICE_NAME}.service; then
        echo -e "${GREEN}  ✓ ${DASHBOARD_SERVICE_NAME} démarré${NC}"
    else
        echo -e "${YELLOW}  ⚠ ${DASHBOARD_SERVICE_NAME} n'a pas démarré correctement${NC}"
        echo "    Consultez: journalctl -u ${DASHBOARD_SERVICE_NAME} -f"
    fi
}

# Print summary
print_summary() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════╗"
    echo "║        Configuration terminée ! 🎉             ║"
    echo "╚════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Services créés:${NC}"
    echo "  • ${SERVICE_NAME}.service     - Collecteur principal"
    echo "  • ${DASHBOARD_SERVICE_NAME}.service - Interface web"
    echo ""
    echo -e "${BLUE}Commandes utiles:${NC}"
    echo ""
    echo "  Voir le statut:"
    echo "    sudo systemctl status ${SERVICE_NAME}"
    echo "    sudo systemctl status ${DASHBOARD_SERVICE_NAME}"
    echo ""
    echo "  Voir les logs:"
    echo "    journalctl -u ${SERVICE_NAME} -f"
    echo "    journalctl -u ${DASHBOARD_SERVICE_NAME} -f"
    echo ""
    echo "  Redémarrer:"
    echo "    sudo systemctl restart ${SERVICE_NAME}"
    echo ""
    echo "  Arrêter:"
    echo "    sudo systemctl stop ${SERVICE_NAME}"
    echo ""
    echo -e "${BLUE}Dashboard accessible sur:${NC}"

    # Get IP address
    IP_ADDR=$(hostname -I | awk '{print $1}')
    echo "    http://${IP_ADDR}:8501"
    echo "    http://localhost:8501"
    echo ""
}

# Uninstall function
uninstall() {
    echo -e "${YELLOW}Désinstallation des services...${NC}"

    systemctl stop ${SERVICE_NAME}.service 2>/dev/null || true
    systemctl stop ${DASHBOARD_SERVICE_NAME}.service 2>/dev/null || true
    systemctl disable ${SERVICE_NAME}.service 2>/dev/null || true
    systemctl disable ${DASHBOARD_SERVICE_NAME}.service 2>/dev/null || true

    rm -f /etc/systemd/system/${SERVICE_NAME}.service
    rm -f /etc/systemd/system/${DASHBOARD_SERVICE_NAME}.service
    rm -f /etc/systemd/system/${SERVICE_NAME}-collect.timer
    rm -f /etc/systemd/system/${SERVICE_NAME}-collect.service

    systemctl daemon-reload

    echo -e "${GREEN}Services désinstallés${NC}"
}

# Main
main() {
    case "${1:-install}" in
        install)
            create_main_service
            create_dashboard_service
            create_timer
            enable_services
            start_services
            print_summary
            ;;
        uninstall)
            uninstall
            ;;
        *)
            echo "Usage: $0 [install|uninstall]"
            exit 1
            ;;
    esac
}

main "$@"
