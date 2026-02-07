#!/bin/bash
# SentinelPi Backup Script
# Creates backups of database and configuration

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
INSTALL_DIR="${SENTINELPI_HOME:-$HOME/sentinelpi}"
BACKUP_DIR="${BACKUP_DIR:-$INSTALL_DIR/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="sentinelpi_backup_${TIMESTAMP}"

echo -e "${BLUE}SentinelPi Backup${NC}"
echo "================="
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create temp directory for this backup
TEMP_BACKUP_DIR=$(mktemp -d)
BACKUP_SUBDIR="$TEMP_BACKUP_DIR/$BACKUP_NAME"
mkdir -p "$BACKUP_SUBDIR"

echo -e "${BLUE}[1/4] Sauvegarde de la base de données...${NC}"
if [ -f "$INSTALL_DIR/data/sentinelpi.db" ]; then
    # Use SQLite backup command for consistency
    sqlite3 "$INSTALL_DIR/data/sentinelpi.db" ".backup '$BACKUP_SUBDIR/sentinelpi.db'"
    echo -e "${GREEN}  ✓ Base de données sauvegardée${NC}"
else
    echo -e "${YELLOW}  ⚠ Base de données non trouvée${NC}"
fi

echo -e "${BLUE}[2/4] Sauvegarde de la configuration...${NC}"
if [ -d "$INSTALL_DIR/config" ]; then
    cp -r "$INSTALL_DIR/config" "$BACKUP_SUBDIR/"
    echo -e "${GREEN}  ✓ Configuration sauvegardée${NC}"
fi

# Backup .env (contains tokens)
if [ -f "$INSTALL_DIR/.env" ]; then
    cp "$INSTALL_DIR/.env" "$BACKUP_SUBDIR/"
    echo -e "${GREEN}  ✓ Fichier .env sauvegardé${NC}"
fi

echo -e "${BLUE}[3/4] Création de l'archive...${NC}"
ARCHIVE_PATH="$BACKUP_DIR/${BACKUP_NAME}.tar.gz"
cd "$TEMP_BACKUP_DIR"
tar -czf "$ARCHIVE_PATH" "$BACKUP_NAME"
echo -e "${GREEN}  ✓ Archive créée: $ARCHIVE_PATH${NC}"

# Calculate size
ARCHIVE_SIZE=$(du -h "$ARCHIVE_PATH" | cut -f1)
echo "    Taille: $ARCHIVE_SIZE"

# Cleanup temp
rm -rf "$TEMP_BACKUP_DIR"

echo -e "${BLUE}[4/4] Nettoyage des anciennes sauvegardes...${NC}"
# Remove backups older than retention period
DELETED_COUNT=$(find "$BACKUP_DIR" -name "sentinelpi_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
if [ "$DELETED_COUNT" -gt 0 ]; then
    echo -e "${GREEN}  ✓ $DELETED_COUNT ancienne(s) sauvegarde(s) supprimée(s)${NC}"
else
    echo "  Aucune ancienne sauvegarde à supprimer"
fi

# List backups
echo ""
echo -e "${BLUE}Sauvegardes disponibles:${NC}"
ls -lh "$BACKUP_DIR"/*.tar.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'

echo ""
echo -e "${GREEN}Backup terminé !${NC}"
echo ""
echo "Pour restaurer:"
echo "  tar -xzf $ARCHIVE_PATH -C /tmp"
echo "  cp /tmp/$BACKUP_NAME/sentinelpi.db $INSTALL_DIR/data/"
echo "  cp -r /tmp/$BACKUP_NAME/config/* $INSTALL_DIR/config/"
