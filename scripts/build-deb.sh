#!/bin/bash
# Script de création du paquet Debian SentinelPi
#
# Usage: ./scripts/build-deb.sh [version]
# Exemple: ./scripts/build-deb.sh 1.0.1

set -e

# Configuration
PACKAGE_NAME="sentinelpi"
VERSION="${1:-1.0.1}"
ARCH="all"
BUILD_DIR="build/deb"
INSTALL_DIR="opt/sentinelpi"

echo "=== Construction du paquet $PACKAGE_NAME v$VERSION ==="

# Vérifier qu'on est dans le bon répertoire
if [ ! -f "pyproject.toml" ]; then
    echo "Erreur: Exécutez ce script depuis la racine du projet"
    exit 1
fi

# Nettoyer
echo "[1/6] Nettoyage..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Créer la structure du paquet
echo "[2/6] Création de la structure..."
PKG_DIR="$BUILD_DIR/${PACKAGE_NAME}_${VERSION}_${ARCH}"
mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/$INSTALL_DIR"
mkdir -p "$PKG_DIR/etc/systemd/system"

# Copier le code source
echo "[3/6] Copie des fichiers..."
cp -r src "$PKG_DIR/$INSTALL_DIR/"
cp -r config "$PKG_DIR/$INSTALL_DIR/"
cp -r scripts "$PKG_DIR/$INSTALL_DIR/"
cp -r docs "$PKG_DIR/$INSTALL_DIR/" 2>/dev/null || true
cp pyproject.toml "$PKG_DIR/$INSTALL_DIR/"
cp README.md "$PKG_DIR/$INSTALL_DIR/"
cp .env.example "$PKG_DIR/$INSTALL_DIR/"

# Copier les fichiers Debian
cp debian/control "$PKG_DIR/DEBIAN/"
cp debian/postinst "$PKG_DIR/DEBIAN/"
cp debian/prerm "$PKG_DIR/DEBIAN/"
cp debian/postrm "$PKG_DIR/DEBIAN/"

# Mettre à jour la version dans control
sed -i "s/Version:.*/Version: $VERSION/" "$PKG_DIR/DEBIAN/control"

# Permissions des scripts
chmod 755 "$PKG_DIR/DEBIAN/postinst"
chmod 755 "$PKG_DIR/DEBIAN/prerm"
chmod 755 "$PKG_DIR/DEBIAN/postrm"

# Copier les services systemd
cp debian/sentinelpi.service "$PKG_DIR/etc/systemd/system/"
cp debian/sentinelpi-dashboard.service "$PKG_DIR/etc/systemd/system/"

# Note: conffiles n'est pas utilisé car les fichiers de config
# sont créés par postinst depuis les templates dans /opt/sentinelpi/config/
echo "[4/6] Configuration des fichiers..."

# Calculer la taille installée
echo "[5/6] Calcul de la taille..."
INSTALLED_SIZE=$(du -sk "$PKG_DIR" | cut -f1)
echo "Installed-Size: $INSTALLED_SIZE" >> "$PKG_DIR/DEBIAN/control"

# Construire le paquet
echo "[6/6] Construction du paquet..."
dpkg-deb --build --root-owner-group "$PKG_DIR"

# Résultat
DEB_FILE="$BUILD_DIR/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
echo ""
echo "=== Paquet créé avec succès ==="
echo "Fichier: $DEB_FILE"
echo "Taille:  $(du -h "$DEB_FILE" | cut -f1)"
echo ""
echo "Installation:"
echo "  sudo dpkg -i $DEB_FILE"
echo ""
echo "Ou avec les dépendances:"
echo "  sudo apt install ./$DEB_FILE"
