# 🚀 Guide de Déploiement sur Serveur

Ce repository contient un guide complet de déploiement pour installer l'application **spaCy Layout - Fine-Tuning Automatisé** sur un serveur RedHat 9.4.

## 📋 Fichiers de Déploiement

- **`DEPLOYMENT_PROMPT.md`** - Prompt détaillé pour Claude Code (déploiement automatisé)
- **`DEPLOYMENT_README.md`** - Ce fichier (instructions d'utilisation)

---

## 🤖 Option 1 : Déploiement avec Claude Code (Recommandé)

### Prérequis

- Serveur RedHat 9.4 avec accès SSH
- Accès root ou sudo
- Claude Code installé sur votre machine locale

### Étapes

1. **Connexion SSH au serveur**

```bash
ssh votre-utilisateur@IP_SERVEUR
```

2. **Lancer Claude Code**

Dans votre terminal local, démarrez Claude Code et copiez-collez le contenu de `DEPLOYMENT_PROMPT.md` :

```bash
claude-code
```

Puis dans Claude Code, collez :

```
Voici le prompt de déploiement pour l'application spacy-layout sur RedHat 9.4.
Tu dois suivre exactement les instructions du fichier DEPLOYMENT_PROMPT.md pour installer
et configurer l'application sur ce serveur.

[Coller ici le contenu complet de DEPLOYMENT_PROMPT.md]

IMPORTANT :
- Vérifie chaque commande avant de l'exécuter
- Demande confirmation pour les étapes critiques
- Adapte les noms de domaine et IPs selon ma configuration
- Note tous les mots de passe et clés générés
```

3. **Claude Code exécutera automatiquement**

Claude Code va :
- ✅ Installer Python 3.11 et les dépendances
- ✅ Créer l'utilisateur et les répertoires
- ✅ Cloner le repository
- ✅ Configurer l'environnement virtuel
- ✅ Créer le service systemd
- ✅ Configurer le pare-feu
- ✅ Tester le déploiement

4. **Finalisation**

Une fois le déploiement terminé, Claude Code vous fournira :
- L'URL d'accès à l'interface web
- Les commandes de vérification
- Les logs de déploiement

---

## 🛠️ Option 2 : Déploiement Manuel

Si vous préférez un déploiement manuel, suivez le guide `DEPLOYMENT_PROMPT.md` étape par étape.

### Étapes Principales

```bash
# 1. Mise à jour système
sudo dnf update -y

# 2. Installation Python 3.11
sudo dnf install -y python3.11 python3.11-devel python3.11-pip

# 3. Création de l'utilisateur
sudo useradd -m -s /bin/bash spacylayout
sudo mkdir -p /opt/spacy-layout /var/log/spacy-layout /etc/spacy-layout
sudo chown -R spacylayout:spacylayout /opt/spacy-layout /var/log/spacy-layout /etc/spacy-layout

# 4. Installation de l'application
sudo su - spacylayout
cd /opt/spacy-layout
git clone https://github.com/jedeth/spacy-layout.git .
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m spacy download fr_core_news_lg

# 5. Configuration
cat > /etc/spacy-layout/.env <<EOF
ARISTOTE_API_KEY=votre_clé_api
DATA_DIR=/opt/spacy-layout/data
OUTPUT_DIR=/opt/spacy-layout/output
LOGS_DIR=/var/log/spacy-layout
EOF

# 6. Service systemd (voir DEPLOYMENT_PROMPT.md pour le fichier complet)
exit
sudo systemctl enable spacy-layout
sudo systemctl start spacy-layout

# 7. Pare-feu
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload

# 8. Vérification
curl http://localhost:8000
```

Consultez `DEPLOYMENT_PROMPT.md` pour les détails complets de chaque étape.

---

## 🔧 Configuration Post-Déploiement

### 1. Configurer la Clé API Aristote

```bash
sudo nano /etc/spacy-layout/.env
# Modifier : ARISTOTE_API_KEY=votre_clé_complète
sudo systemctl restart spacy-layout
```

### 2. Uploader les Données Initiales

Deux options :

**A. Via l'interface web**
- Accéder à `http://IP_SERVEUR:8000`
- Utiliser la section "Upload de fichiers"

**B. Via SSH/SCP**

```bash
# Depuis votre machine locale
scp -r mes_donnees/* spacylayout@IP_SERVEUR:/opt/spacy-layout/data/

# Ou créer des données de test
ssh spacylayout@IP_SERVEUR
cd /opt/spacy-layout
echo -e "Dupont\nMartin\nBernard" > data/entities/students/noms.txt
echo -e "Lycée Victor Hugo" > data/entities/schools/lycees.txt
```

### 3. Tester le Fine-Tuning

```bash
# Se connecter au serveur
ssh spacylayout@IP_SERVEUR

# Activer l'environnement
cd /opt/spacy-layout
source venv/bin/activate

# Test CLI
python cli.py data-stats
python cli.py test-llm
```

Ou via l'interface web : `http://IP_SERVEUR:8000`

---

## 🌐 Configuration du Domaine (Optionnel)

Si vous souhaitez utiliser un nom de domaine (ex: `spacy.votre-domaine.fr`) :

### 1. Configurer le DNS

Ajouter un enregistrement A dans votre DNS :
```
spacy.votre-domaine.fr.  IN  A  IP_SERVEUR
```

### 2. Installer et Configurer Nginx

Voir la section "Étape 7" dans `DEPLOYMENT_PROMPT.md`

```bash
sudo dnf install -y nginx
# Suivre les instructions du DEPLOYMENT_PROMPT.md
```

### 3. Activer SSL avec Let's Encrypt

```bash
sudo dnf install -y certbot python3-certbot-nginx
sudo certbot --nginx -d spacy.votre-domaine.fr
```

L'application sera accessible via : `https://spacy.votre-domaine.fr`

---

## 📊 Vérification du Déploiement

### Checklist

- [ ] Service systemd actif : `sudo systemctl status spacy-layout`
- [ ] Port 8000 ouvert : `sudo ss -tlnp | grep 8000`
- [ ] Interface web accessible : `curl http://localhost:8000`
- [ ] API fonctionnelle : `curl http://localhost:8000/api/status`
- [ ] Logs sans erreur : `sudo journalctl -u spacy-layout -n 50`
- [ ] Clé API configurée : `cat /etc/spacy-layout/.env | grep ARISTOTE`
- [ ] Modèle spaCy installé : `python -c "import spacy; spacy.load('fr_core_news_lg')"`

### Commandes de Diagnostic

```bash
# Statut du service
sudo systemctl status spacy-layout

# Logs en temps réel
sudo journalctl -u spacy-layout -f

# Logs de l'application
sudo tail -f /var/log/spacy-layout/access.log

# Test de connexion
curl -I http://localhost:8000

# Vérifier les processus
ps aux | grep python

# Vérifier les ports
sudo netstat -tulpn | grep 8000
```

---

## 🔒 Sécurité

### Recommandations

1. **Changer les mots de passe par défaut**

```bash
# Mot de passe utilisateur spacylayout
sudo passwd spacylayout
```

2. **Configurer fail2ban** (voir DEPLOYMENT_PROMPT.md)

3. **Limiter l'accès par IP** (si réseau privé)

```bash
sudo firewall-cmd --permanent --zone=public --add-rich-rule='
  rule family="ipv4"
  source address="192.168.1.0/24"
  port protocol="tcp" port="8000" accept'
sudo firewall-cmd --reload
```

4. **Activer HTTPS** (avec Let's Encrypt)

5. **Rotation des logs** (voir DEPLOYMENT_PROMPT.md)

---

## 🔄 Mise à Jour de l'Application

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

---

## 💾 Sauvegarde

### Script de Sauvegarde Automatique

Voir la section "Étape 11.4" dans `DEPLOYMENT_PROMPT.md` pour le script complet.

```bash
# Exécuter une sauvegarde manuelle
sudo /usr/local/bin/backup-spacy-layout.sh

# Vérifier les sauvegardes
ls -lh /backup/spacy-layout/
```

---

## 🆘 Dépannage

### Problème : Service ne démarre pas

```bash
sudo journalctl -u spacy-layout -n 100
sudo ls -la /opt/spacy-layout/
sudo ls -la /etc/spacy-layout/.env
```

### Problème : Erreur d'import Python

```bash
sudo su - spacylayout
cd /opt/spacy-layout
source venv/bin/activate
pip install --force-reinstall -r requirements.txt
python -m spacy download fr_core_news_lg
```

### Problème : Interface web inaccessible

```bash
# Vérifier le service
sudo systemctl status spacy-layout

# Vérifier le pare-feu
sudo firewall-cmd --list-all

# Vérifier les ports
sudo ss -tlnp | grep 8000

# Test local
curl http://localhost:8000
```

### Problème : SELinux bloque l'accès

```bash
# Vérifier les alertes
sudo ausearch -m avc -ts recent

# Mode permissif temporaire (debug)
sudo setenforce 0

# Après résolution, remettre en enforcing
sudo setenforce 1
```

---

## 📞 Support

Pour plus d'informations :
- **Documentation complète** : `TRAINING_README.md`
- **Guide de déploiement détaillé** : `DEPLOYMENT_PROMPT.md`
- **Guide des données** : `data/README.md`

---

## ✅ Résumé

**Déploiement en 3 étapes** :

1. **Préparer le serveur** : RedHat 9.4 avec accès root
2. **Exécuter le prompt** : Copier `DEPLOYMENT_PROMPT.md` dans Claude Code
3. **Accéder à l'application** : `http://IP_SERVEUR:8000`

**Temps estimé** : 15-30 minutes avec Claude Code, 45-60 minutes en manuel.

**Résultat** : Application web opérationnelle avec service systemd, pare-feu configuré, et logs actifs.
