# Prompt pour Claude Code : Déploiement sur RedHat 9.4

## Contexte

Tu dois installer et configurer l'application **spaCy Layout - Fine-Tuning Automatisé** sur un serveur RedHat 9.4. Cette application est un système de fine-tuning automatisé pour la pseudonymisation de documents scolaires français.

## Spécifications Serveur

- **OS** : RedHat Enterprise Linux 9.4
- **Architecture** : x86_64
- **Accès** : Root ou sudo
- **Ports requis** : 8000 (application web)

## Objectifs

1. Installer toutes les dépendances système et Python
2. Configurer l'environnement Python avec virtualenv
3. Cloner et installer l'application spacy-layout
4. Configurer les variables d'environnement
5. Créer un service systemd pour le démarrage automatique
6. Configurer le pare-feu
7. (Optionnel) Configurer Nginx comme reverse proxy
8. Tester le déploiement

---

## Étape 1 : Préparation du Système

### 1.1 Mise à jour du système

```bash
sudo dnf update -y
sudo dnf install -y dnf-plugins-core
```

### 1.2 Installation des dépendances système

```bash
# Outils de développement
sudo dnf groupinstall -y "Development Tools"

# Bibliothèques requises pour Python et ses packages
sudo dnf install -y \
    python3.11 \
    python3.11-devel \
    python3.11-pip \
    git \
    wget \
    curl \
    gcc \
    gcc-c++ \
    make \
    openssl-devel \
    bzip2-devel \
    libffi-devel \
    zlib-devel \
    sqlite-devel \
    readline-devel
```

### 1.3 Vérification de Python

```bash
python3.11 --version
# Doit afficher : Python 3.11.x
```

---

## Étape 2 : Configuration de l'Utilisateur et des Répertoires

### 2.1 Créer un utilisateur dédié

```bash
sudo useradd -m -s /bin/bash spacylayout
sudo usermod -aG wheel spacylayout  # Optionnel : accès sudo
```

### 2.2 Créer la structure de répertoires

```bash
sudo mkdir -p /opt/spacy-layout
sudo mkdir -p /var/log/spacy-layout
sudo mkdir -p /etc/spacy-layout

sudo chown -R spacylayout:spacylayout /opt/spacy-layout
sudo chown -R spacylayout:spacylayout /var/log/spacy-layout
sudo chown -R spacylayout:spacylayout /etc/spacy-layout
```

### 2.3 Passer à l'utilisateur spacylayout

```bash
sudo su - spacylayout
cd /opt/spacy-layout
```

---

## Étape 3 : Installation de l'Application

### 3.1 Cloner le repository

```bash
git clone https://github.com/jedeth/spacy-layout.git .
# Ou si branche spécifique :
# git clone -b claude/analyze-repository-011DB8fawnqrMwycxo2N3w1b https://github.com/jedeth/spacy-layout.git .
```

### 3.2 Créer l'environnement virtuel Python

```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 3.3 Installer les dépendances Python

```bash
pip install --upgrade pip setuptools wheel

# Installation des dépendances
pip install -r requirements.txt

# Installation du modèle spaCy français
python -m spacy download fr_core_news_lg
```

### 3.4 Vérifier l'installation

```bash
# Test d'import
python -c "import spacy; import fastapi; import docling; print('✓ Imports OK')"

# Test du CLI
python cli.py --help
```

---

## Étape 4 : Configuration de l'Application

### 4.1 Créer le fichier .env

```bash
cat > /etc/spacy-layout/.env <<'EOF'
# API Aristote Dispatcher
ARISTOTE_API_KEY=drasi-idf-1-84e20c68-c43f-4a71-b655-a5af1426ebXX

# Configuration application
DATA_DIR=/opt/spacy-layout/data
OUTPUT_DIR=/opt/spacy-layout/output
LOGS_DIR=/var/log/spacy-layout

# Configuration serveur web
HOST=0.0.0.0
PORT=8000
EOF

# Sécuriser le fichier
chmod 600 /etc/spacy-layout/.env
```

**IMPORTANT** : Remplacez les `XX` par les 2 caractères manquants de votre clé API Aristote.

### 4.2 Créer un lien symbolique vers .env

```bash
ln -s /etc/spacy-layout/.env /opt/spacy-layout/.env
```

### 4.3 Créer la structure de données

```bash
mkdir -p data/entities/{students,schools,programs}
mkdir -p data/documents/{train,test}
mkdir -p data/annotations
mkdir -p output
```

---

## Étape 5 : Configuration du Service Systemd

### 5.1 Créer le fichier service (en tant que root)

```bash
exit  # Sortir de l'utilisateur spacylayout

sudo cat > /etc/systemd/system/spacy-layout.service <<'EOF'
[Unit]
Description=spaCy Layout - Fine-Tuning Automatisé
After=network.target

[Service]
Type=simple
User=spacylayout
Group=spacylayout
WorkingDirectory=/opt/spacy-layout
Environment="PATH=/opt/spacy-layout/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/etc/spacy-layout/.env

ExecStart=/opt/spacy-layout/venv/bin/python /opt/spacy-layout/server.py --host 0.0.0.0 --port 8000

Restart=always
RestartSec=10

StandardOutput=append:/var/log/spacy-layout/access.log
StandardError=append:/var/log/spacy-layout/error.log

[Install]
WantedBy=multi-user.target
EOF
```

### 5.2 Activer et démarrer le service

```bash
sudo systemctl daemon-reload
sudo systemctl enable spacy-layout
sudo systemctl start spacy-layout
```

### 5.3 Vérifier le statut

```bash
sudo systemctl status spacy-layout
```

### 5.4 Consulter les logs

```bash
# Logs en temps réel
sudo journalctl -u spacy-layout -f

# Logs de l'application
sudo tail -f /var/log/spacy-layout/access.log
sudo tail -f /var/log/spacy-layout/error.log
```

---

## Étape 6 : Configuration du Pare-feu

### 6.1 Ouvrir le port 8000

```bash
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

### 6.2 Vérifier les règles

```bash
sudo firewall-cmd --list-all
```

---

## Étape 7 : (Optionnel) Configuration Nginx comme Reverse Proxy

### 7.1 Installer Nginx

```bash
sudo dnf install -y nginx
sudo systemctl enable nginx
```

### 7.2 Créer la configuration Nginx

```bash
sudo cat > /etc/nginx/conf.d/spacy-layout.conf <<'EOF'
upstream spacy_layout {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name votre-domaine.fr;  # Remplacer par votre domaine

    client_max_body_size 100M;  # Pour les uploads de documents

    location / {
        proxy_pass http://spacy_layout;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://spacy_layout;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }

    access_log /var/log/nginx/spacy-layout-access.log;
    error_log /var/log/nginx/spacy-layout-error.log;
}
EOF
```

### 7.3 Tester et redémarrer Nginx

```bash
sudo nginx -t
sudo systemctl restart nginx
```

### 7.4 Ouvrir les ports HTTP/HTTPS

```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 7.5 (Optionnel) Configurer SSL avec Let's Encrypt

```bash
sudo dnf install -y certbot python3-certbot-nginx
sudo certbot --nginx -d votre-domaine.fr
```

---

## Étape 8 : SELinux (Si activé)

### 8.1 Vérifier le statut SELinux

```bash
getenforce
# Si "Enforcing", configurer les permissions
```

### 8.2 Autoriser les connexions réseau

```bash
sudo setsebool -P httpd_can_network_connect 1
```

### 8.3 Configurer les contextes de fichiers

```bash
sudo semanage fcontext -a -t httpd_sys_rw_content_t "/opt/spacy-layout(/.*)?"
sudo semanage fcontext -a -t httpd_sys_rw_content_t "/var/log/spacy-layout(/.*)?"
sudo restorecon -Rv /opt/spacy-layout
sudo restorecon -Rv /var/log/spacy-layout
```

---

## Étape 9 : Tests de Déploiement

### 9.1 Test local (sur le serveur)

```bash
curl http://localhost:8000
# Doit retourner la page HTML
```

### 9.2 Test API

```bash
curl http://localhost:8000/api/status
# Doit retourner : {"is_running":false,"current_run":null}
```

### 9.3 Test CLI (en tant que spacylayout)

```bash
sudo su - spacylayout
cd /opt/spacy-layout
source venv/bin/activate

# Test des données
python cli.py data-stats

# Test LLM (si clé API configurée)
python cli.py test-llm
```

### 9.4 Test depuis un navigateur

Ouvrez dans votre navigateur :
- Sans Nginx : `http://IP_SERVEUR:8000`
- Avec Nginx : `http://votre-domaine.fr`

---

## Étape 10 : Chargement des Données Initiales

### 10.1 Upload de fichiers via l'interface web

1. Accéder à l'interface web
2. Section "Données Chargées"
3. Utiliser l'API d'upload ou placer manuellement les fichiers

### 10.2 Ou copie manuelle (en tant que spacylayout)

```bash
sudo su - spacylayout
cd /opt/spacy-layout

# Exemple : copier des listes d'entités
echo -e "Dupont\nMartin\nBernard" > data/entities/students/noms.txt
echo -e "Lycée Victor Hugo\nLycée Henri IV" > data/entities/schools/lycees.txt

# Définir les permissions
chmod 644 data/entities/students/*.txt
chmod 644 data/entities/schools/*.txt
```

---

## Étape 11 : Maintenance et Monitoring

### 11.1 Logs à surveiller

```bash
# Logs système
sudo journalctl -u spacy-layout -f

# Logs application
sudo tail -f /var/log/spacy-layout/access.log
sudo tail -f /var/log/spacy-layout/error.log

# Logs de training (générés pendant l'utilisation)
sudo tail -f /var/log/spacy-layout/run_*/summary.json
```

### 11.2 Rotation des logs

```bash
sudo cat > /etc/logrotate.d/spacy-layout <<'EOF'
/var/log/spacy-layout/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 spacylayout spacylayout
    sharedscripts
    postrotate
        systemctl reload spacy-layout > /dev/null 2>&1 || true
    endscript
}
EOF
```

### 11.3 Mise à jour de l'application

```bash
sudo su - spacylayout
cd /opt/spacy-layout

# Pull des modifications
git pull origin main

# Mise à jour des dépendances
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Redémarrage
exit
sudo systemctl restart spacy-layout
```

### 11.4 Sauvegarde

```bash
# Script de sauvegarde
sudo cat > /usr/local/bin/backup-spacy-layout.sh <<'EOF'
#!/bin/bash
BACKUP_DIR="/backup/spacy-layout"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p ${BACKUP_DIR}

# Sauvegarde des données
tar -czf ${BACKUP_DIR}/data_${DATE}.tar.gz /opt/spacy-layout/data/

# Sauvegarde des modèles entraînés
tar -czf ${BACKUP_DIR}/output_${DATE}.tar.gz /opt/spacy-layout/output/

# Sauvegarde des logs
tar -czf ${BACKUP_DIR}/logs_${DATE}.tar.gz /var/log/spacy-layout/

# Sauvegarde de la config
cp /etc/spacy-layout/.env ${BACKUP_DIR}/.env_${DATE}

# Nettoyage (garde 7 jours)
find ${BACKUP_DIR} -name "*.tar.gz" -mtime +7 -delete

echo "Sauvegarde terminée : ${BACKUP_DIR}"
EOF

sudo chmod +x /usr/local/bin/backup-spacy-layout.sh

# Ajouter au cron (tous les jours à 2h du matin)
sudo crontab -e
# Ajouter : 0 2 * * * /usr/local/bin/backup-spacy-layout.sh
```

---

## Étape 12 : Sécurité

### 12.1 Pare-feu applicatif (fail2ban)

```bash
sudo dnf install -y fail2ban

sudo cat > /etc/fail2ban/jail.d/spacy-layout.conf <<'EOF'
[spacy-layout]
enabled = true
port = 8000
filter = spacy-layout
logpath = /var/log/spacy-layout/access.log
maxretry = 5
bantime = 3600
findtime = 600
EOF

sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 12.2 Limiter l'accès par IP (optionnel)

```bash
# Autoriser uniquement certaines IPs
sudo firewall-cmd --permanent --zone=public --add-rich-rule='
  rule family="ipv4"
  source address="192.168.1.0/24"
  port protocol="tcp" port="8000" accept'

sudo firewall-cmd --reload
```

---

## Vérification Finale

### Checklist de déploiement

- [ ] Python 3.11+ installé
- [ ] Environnement virtuel créé et activé
- [ ] Dépendances Python installées
- [ ] Modèle spaCy fr_core_news_lg téléchargé
- [ ] Fichier .env configuré avec la clé API
- [ ] Service systemd créé et en cours d'exécution
- [ ] Pare-feu configuré (port 8000 ouvert)
- [ ] Nginx configuré (si utilisé)
- [ ] SELinux configuré (si activé)
- [ ] Interface web accessible depuis navigateur
- [ ] Logs fonctionnels
- [ ] Sauvegarde configurée

### Tests finaux

```bash
# 1. Service actif
sudo systemctl is-active spacy-layout
# Doit retourner : active

# 2. Port ouvert
sudo ss -tlnp | grep 8000
# Doit afficher le processus Python

# 3. Interface web
curl -I http://localhost:8000
# Doit retourner : HTTP/1.1 200 OK

# 4. Logs sans erreur
sudo journalctl -u spacy-layout --since "5 minutes ago" | grep -i error
# Aucune erreur critique

# 5. Test complet de l'API
curl http://localhost:8000/api/data/stats
# Doit retourner un JSON avec les statistiques
```

---

## Dépannage

### Problème : Service ne démarre pas

```bash
# Vérifier les logs
sudo journalctl -u spacy-layout -n 50

# Vérifier les permissions
sudo ls -la /opt/spacy-layout/
sudo ls -la /etc/spacy-layout/.env

# Tester manuellement
sudo su - spacylayout
cd /opt/spacy-layout
source venv/bin/activate
python server.py
```

### Problème : Port 8000 déjà utilisé

```bash
# Trouver le processus
sudo lsof -i :8000
sudo netstat -tulpn | grep 8000

# Changer le port dans le service
sudo nano /etc/systemd/system/spacy-layout.service
# Modifier : --port 8001

sudo systemctl daemon-reload
sudo systemctl restart spacy-layout
```

### Problème : Imports Python échouent

```bash
# Réinstaller les dépendances
sudo su - spacylayout
cd /opt/spacy-layout
source venv/bin/activate
pip install --force-reinstall -r requirements.txt
```

### Problème : SELinux bloque l'accès

```bash
# Vérifier les alertes SELinux
sudo ausearch -m avc -ts recent

# Mode permissif temporaire (debug uniquement)
sudo setenforce 0

# Après identification du problème, revenir en enforcing
sudo setenforce 1
```

---

## URLs et Commandes Utiles

### Accès

- Interface web : `http://IP_SERVEUR:8000` ou `http://votre-domaine.fr`
- Documentation API : `http://IP_SERVEUR:8000/docs`
- Monitoring : `http://IP_SERVEUR:8000/api/status`

### Commandes fréquentes

```bash
# Redémarrer le service
sudo systemctl restart spacy-layout

# Voir les logs en temps réel
sudo journalctl -u spacy-layout -f

# Statut du service
sudo systemctl status spacy-layout

# Arrêter le service
sudo systemctl stop spacy-layout

# Démarrer le service
sudo systemctl start spacy-layout
```

---

## Support et Documentation

- **README principal** : `/opt/spacy-layout/README.md`
- **Documentation training** : `/opt/spacy-layout/TRAINING_README.md`
- **Guide des données** : `/opt/spacy-layout/data/README.md`
- **Exemple d'utilisation** : `/opt/spacy-layout/examples/training/basic_usage.py`

---

## Résumé pour Claude Code

**Objectif** : Déployer spacy-layout sur RedHat 9.4

**Actions principales** :
1. Installer Python 3.11 et dépendances
2. Créer utilisateur `spacylayout` et répertoires `/opt/spacy-layout`
3. Cloner le repo et installer dans un venv
4. Configurer `/etc/spacy-layout/.env` avec la clé API
5. Créer service systemd `/etc/systemd/system/spacy-layout.service`
6. Configurer firewall (port 8000)
7. (Optionnel) Nginx reverse proxy
8. Tester l'accès web

**Résultat attendu** : Interface web accessible sur `http://IP:8000` avec le service démarré automatiquement.
