# Dépannage

Solutions aux problèmes courants.

## Installation

### "python3-venv not found"

```bash
sudo apt install python3-venv
```

### Version Python trop ancienne

```bash
# Vérifier la version
python3 --version

# Si < 3.11, installer pyenv
curl https://pyenv.run | bash
pyenv install 3.11.0
pyenv global 3.11.0
```

### Erreur mémoire lors de pip install

```bash
# Augmenter le swap
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Installer sans cache
pip install -e . --no-cache-dir
```

---

## Dashboard

### Le dashboard ne démarre pas

```bash
# Vérifier le port
sudo netstat -tlnp | grep 8501

# Si occupé, tuer le processus
sudo kill $(sudo lsof -t -i:8501)

# Relancer
sentinelpi-dashboard
```

### Page blanche ou erreur 502

```bash
# Vérifier les logs
journalctl -u sentinelpi-dashboard -f

# Ou directement
streamlit run src/dashboard/app.py 2>&1 | tee dashboard.log
```

### "ModuleNotFoundError"

```bash
# S'assurer que l'environnement est activé
source venv/bin/activate

# Réinstaller
pip install -e .
```

---

## Collecte

### Aucun item collecté

1. **Vérifier que les sources sont activées**
   - Dashboard > Sources > Vérifier "Activée"

2. **Tester une source manuellement**
   - Dashboard > Sources > Cliquer "Tester"

3. **Vérifier les logs**
   ```bash
   tail -f logs/sentinelpi.log
   ```

### Erreur 403/429 sur une source

Le site bloque les requêtes automatisées.

```yaml
# Dans config/settings.yaml, ajuster les headers HTTP
http:
  user_agent: "Mozilla/5.0 ..."
  rate_limit: 5.0  # Augmenter le délai entre requêtes
```

### Source en erreur permanente

```bash
# Réinitialiser le compteur d'erreurs
# Via le dashboard : Sources > Modifier > Sauvegarder
```

---

## Alertes

### Telegram ne fonctionne pas

1. **Vérifier le token et chat_id**
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getMe"
   curl "https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<ID>&text=test"
   ```

2. **Vérifier le fichier .env**
   ```bash
   cat .env | grep TELEGRAM
   ```

3. **Vérifier la configuration**
   ```yaml
   # config/alerts.yaml
   channels:
     telegram:
       enabled: true
       min_severity: notice
   ```

### Emails non reçus

1. **Vérifier les paramètres SMTP**
2. **Pour Gmail, utiliser un mot de passe d'application**
3. **Vérifier les spams**

### Trop d'alertes

```yaml
# config/alerts.yaml
alerting:
  aggregation:
    enabled: true
    window_minutes: 30
    max_alerts_per_window: 5
```

---

## Base de données

### Base corrompue

```bash
# Sauvegarder
cp data/sentinelpi.db data/sentinelpi.db.bak

# Vérifier l'intégrité
sqlite3 data/sentinelpi.db "PRAGMA integrity_check;"

# Si corrompue, exporter/réimporter
sqlite3 data/sentinelpi.db ".dump" > dump.sql
rm data/sentinelpi.db
sqlite3 data/sentinelpi.db < dump.sql
```

### Base trop volumineuse

```bash
# Vérifier la taille
du -h data/sentinelpi.db

# Nettoyer les anciens items (via settings.yaml)
maintenance:
  retention_days: 30  # Réduire

# Compacter manuellement
sqlite3 data/sentinelpi.db "VACUUM;"
```

### Erreur "database is locked"

```bash
# Arrêter tous les processus SentinelPi
sudo systemctl stop sentinelpi sentinelpi-dashboard

# Vérifier les processus
ps aux | grep sentinel

# Relancer
sudo systemctl start sentinelpi sentinelpi-dashboard
```

---

## Performance

### Collecte lente

```yaml
# config/settings.yaml
collection:
  max_concurrent_collectors: 5  # Augmenter (attention RAM)
  collector_timeout: 60         # Réduire le timeout
```

### Dashboard lent avec beaucoup d'items

1. **Réduire la période de date par défaut**
2. **Utiliser les filtres de statut/catégorie**
3. **Augmenter la rétention des items**

### Mémoire saturée

```bash
# Vérifier l'utilisation
free -h
htop

# Réduire les workers
collection:
  max_concurrent_collectors: 2
```

---

## Services systemd

### Service ne démarre pas

```bash
# Vérifier le statut
sudo systemctl status sentinelpi

# Voir les logs détaillés
journalctl -u sentinelpi -n 50 --no-pager

# Vérifier le fichier service
sudo cat /etc/systemd/system/sentinelpi.service
```

### Erreur de permissions

```bash
# Vérifier l'utilisateur dans le service
User=pi

# Vérifier les permissions du dossier
ls -la /home/pi/sentinelpi
chown -R pi:pi /home/pi/sentinelpi
```

### Service qui redémarre en boucle

```bash
# Voir les crashs
journalctl -u sentinelpi -f

# Désactiver le restart automatique temporairement
sudo systemctl stop sentinelpi
# Lancer manuellement pour debug
/home/pi/sentinelpi/venv/bin/sentinelpi
```

---

## Logs

### Activer le mode debug

```yaml
# config/settings.yaml
logging:
  level: DEBUG
```

### Localiser les erreurs

```bash
# Logs récents
tail -100 logs/sentinelpi.log

# Rechercher les erreurs
grep -i error logs/sentinelpi.log | tail -20

# Suivre en temps réel
tail -f logs/sentinelpi.log
```

---

## Réinitialisation complète

Si rien ne fonctionne :

```bash
# 1. Arrêter les services
sudo systemctl stop sentinelpi sentinelpi-dashboard

# 2. Sauvegarder la config
cp -r config config.bak

# 3. Supprimer les données
rm -rf data/* logs/*

# 4. Réinstaller
pip install -e . --force-reinstall

# 5. Relancer
sentinelpi
```

---

## Obtenir de l'aide

1. **Consulter les logs** : `logs/sentinelpi.log`
2. **Mode debug** : `logging.level: DEBUG`
3. **Issues GitHub** : https://github.com/sentinelpi/sentinelpi/issues
