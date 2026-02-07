#!/bin/bash
# SentinelPi Installation Script
# For Raspberry Pi OS (Debian-based)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="${INSTALL_DIR:-$HOME/sentinelpi}"
PYTHON_VERSION="3.11"
VENV_DIR="$INSTALL_DIR/.venv"
WITH_SYSTEMD=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --with-systemd)
            WITH_SYSTEMD=true
            shift
            ;;
    esac
done

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════╗"
echo "║         SentinelPi Installation Script         ║"
echo "║     Station de veille pour Raspberry Pi        ║"
echo "╚════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running on Raspberry Pi OS
check_system() {
    echo -e "${BLUE}[1/7] Vérification du système...${NC}"

    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "  OS: $PRETTY_NAME"
    fi

    # Check architecture
    ARCH=$(uname -m)
    echo "  Architecture: $ARCH"

    # Check memory
    MEM_TOTAL=$(free -m | awk '/^Mem:/{print $2}')
    echo "  Mémoire: ${MEM_TOTAL}MB"

    if [ "$MEM_TOTAL" -lt 1024 ]; then
        echo -e "${YELLOW}  ⚠️  Moins de 1GB de RAM détecté. Performance réduite possible.${NC}"
    fi

    echo -e "${GREEN}  ✓ Système compatible${NC}"
}

# Install system dependencies
install_dependencies() {
    echo -e "${BLUE}[2/7] Installation des dépendances système...${NC}"

    sudo apt-get update

    # Python and build tools
    sudo apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        build-essential \
        libffi-dev \
        libssl-dev \
        libxml2-dev \
        libxslt1-dev \
        libjpeg-dev \
        zlib1g-dev \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf2.0-0 \
        libcairo2 \
        libgirepository1.0-dev \
        gir1.2-pango-1.0 \
        git \
        curl

    echo -e "${GREEN}  ✓ Dépendances installées${NC}"
}

# Create virtual environment
setup_virtualenv() {
    echo -e "${BLUE}[3/7] Création de l'environnement virtuel...${NC}"

    if [ -d "$VENV_DIR" ]; then
        echo "  Environnement existant détecté, mise à jour..."
    else
        python3 -m venv "$VENV_DIR"
    fi

    # Activate venv
    source "$VENV_DIR/bin/activate"

    # Upgrade pip
    pip install --upgrade pip wheel setuptools

    echo -e "${GREEN}  ✓ Environnement virtuel créé: $VENV_DIR${NC}"
}

# Install Python dependencies
install_python_deps() {
    echo -e "${BLUE}[4/7] Installation des dépendances Python...${NC}"

    source "$VENV_DIR/bin/activate"

    # Install from pyproject.toml
    cd "$INSTALL_DIR"
    pip install -e .

    echo -e "${GREEN}  ✓ Dépendances Python installées${NC}"
}

# Setup configuration
setup_config() {
    echo -e "${BLUE}[5/7] Configuration...${NC}"

    # Create directories
    mkdir -p "$INSTALL_DIR/data/cache"
    mkdir -p "$INSTALL_DIR/data/exports"
    mkdir -p "$INSTALL_DIR/logs"

    # Copy .env if not exists
    if [ ! -f "$INSTALL_DIR/.env" ]; then
        if [ -f "$INSTALL_DIR/.env.example" ]; then
            cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
            echo "  Fichier .env créé depuis .env.example"
            echo -e "${YELLOW}  ⚠️  Pensez à configurer vos tokens dans .env${NC}"
        fi
    else
        echo "  Fichier .env existant conservé"
    fi

    echo -e "${GREEN}  ✓ Configuration initiale terminée${NC}"
}

# Initialize database
init_database() {
    echo -e "${BLUE}[6/7] Initialisation de la base de données...${NC}"

    source "$VENV_DIR/bin/activate"
    cd "$INSTALL_DIR"

    # Run Python to initialize DB
    python3 -c "
import asyncio
from src.storage.database import init_database
asyncio.run(init_database())
print('Base de données initialisée')
"

    echo -e "${GREEN}  ✓ Base de données initialisée${NC}"
}

# Install systemd services
setup_systemd() {
    if [ "$WITH_SYSTEMD" = true ]; then
        echo -e "${BLUE}[7/8] Installation des services systemd...${NC}"

        if [ "$(id -u)" != "0" ]; then
            echo -e "${YELLOW}  ⚠️  L'option --with-systemd nécessite les droits root${NC}"
            echo "  Relancez avec: sudo ./scripts/install.sh --with-systemd"
            return
        fi

        # Get current user
        CURRENT_USER="${SUDO_USER:-$USER}"

        # Create service files
        cat > /etc/systemd/system/sentinelpi.service << EOF
[Unit]
Description=SentinelPi - Station de veille multi-sources
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$VENV_DIR/bin/python -m src.main
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

        cat > /etc/systemd/system/sentinelpi-dashboard.service << EOF
[Unit]
Description=SentinelPi Dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$VENV_DIR/bin/streamlit run src/dashboard/app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

        # Install sentinelctl
        cp "$INSTALL_DIR/scripts/sentinelctl" /usr/local/bin/sentinelctl
        chmod +x /usr/local/bin/sentinelctl

        systemctl daemon-reload

        echo -e "${GREEN}  ✓ Services systemd installés${NC}"
        echo ""
        echo "  Pour activer les services:"
        echo -e "    ${BLUE}sudo systemctl enable --now sentinelpi${NC}"
        echo -e "    ${BLUE}sudo systemctl enable --now sentinelpi-dashboard${NC}"
        echo ""
        echo "  Pour gérer SentinelPi:"
        echo -e "    ${BLUE}sentinelctl status${NC}"
    else
        echo -e "${BLUE}[7/8] Services systemd non installés (utilisez --with-systemd)${NC}"
    fi
}

# Create shell aliases
setup_aliases() {
    echo -e "${BLUE}[8/8] Configuration des raccourcis...${NC}"

    # Create activation script
    cat > "$INSTALL_DIR/activate.sh" << EOF
#!/bin/bash
# Activate SentinelPi environment
source "$VENV_DIR/bin/activate"
cd "$INSTALL_DIR"
export SENTINELPI_HOME="$INSTALL_DIR"
echo "SentinelPi environment activated"
EOF
    chmod +x "$INSTALL_DIR/activate.sh"

    # Add to .bashrc if not already present
    ALIAS_LINE="alias sentinelpi-env='source $INSTALL_DIR/activate.sh'"
    if ! grep -q "sentinelpi-env" ~/.bashrc 2>/dev/null; then
        echo "" >> ~/.bashrc
        echo "# SentinelPi" >> ~/.bashrc
        echo "$ALIAS_LINE" >> ~/.bashrc
        echo "alias sentinelpi='source $INSTALL_DIR/activate.sh && sentinelpi'" >> ~/.bashrc
        echo "alias sentinelpi-dashboard='source $INSTALL_DIR/activate.sh && streamlit run $INSTALL_DIR/src/dashboard/app.py'" >> ~/.bashrc
    fi

    echo -e "${GREEN}  ✓ Raccourcis configurés${NC}"
}

# Print completion message
print_completion() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════╗"
    echo "║         Installation terminée ! 🎉              ║"
    echo "╚════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "📁 Répertoire: ${BLUE}$INSTALL_DIR${NC}"
    echo ""
    echo -e "${YELLOW}Prochaines étapes:${NC}"
    echo ""
    echo "1. Configurer les tokens dans .env:"
    echo -e "   ${BLUE}nano $INSTALL_DIR/.env${NC}"
    echo ""
    echo "2. Configurer vos sources:"
    echo -e "   ${BLUE}nano $INSTALL_DIR/config/sources.yaml${NC}"
    echo ""
    echo "3. Démarrer SentinelPi:"
    echo -e "   ${BLUE}source $INSTALL_DIR/activate.sh${NC}"
    echo -e "   ${BLUE}sentinelpi${NC}"
    echo ""
    echo "4. Ou lancer le dashboard:"
    echo -e "   ${BLUE}sentinelpi-dashboard${NC}"
    echo ""
    if [ "$WITH_SYSTEMD" = true ]; then
        echo "5. Gérer avec systemd:"
        echo -e "   ${BLUE}sentinelctl status${NC}"
        echo -e "   ${BLUE}sentinelctl start${NC}"
        echo -e "   ${BLUE}sentinelctl logs${NC}"
    else
        echo "5. (Optionnel) Installer comme service systemd:"
        echo -e "   ${BLUE}sudo ./scripts/install.sh --with-systemd${NC}"
    fi
    echo ""
}

# Main installation
main() {
    # Check we're in the right directory
    if [ ! -f "$INSTALL_DIR/pyproject.toml" ]; then
        echo -e "${RED}Erreur: pyproject.toml non trouvé dans $INSTALL_DIR${NC}"
        echo "Assurez-vous d'exécuter ce script depuis le répertoire sentinelpi"
        exit 1
    fi

    check_system
    install_dependencies
    setup_virtualenv
    install_python_deps
    setup_config
    init_database
    setup_systemd
    setup_aliases
    print_completion
}

# Run
main "$@"
