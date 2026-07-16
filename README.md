# NetScope

Version actuelle : **0.0.2** — voir le [changelog](CHANGELOG.md) et la [feuille de route](docs/ROADMAP.md).

NetScope est une application web auto-hébergée pour découvrir, inventorier et documenter un réseau. Elle réunit l’inventaire des équipements, les scans, l’IPAM, les VLAN, les sites Datacenter, les services, SNMPv3 et les relations LLDP/CDP.

![Tableau de bord NetScope](netscope.png)

Ce guide est prévu pour une première installation, même sans expérience de Docker.

## 1. Ce qu’il faut avant de commencer

Il vous faut une machine Linux avec :

- Docker Engine 24 ou plus récent ;
- Docker Compose v2 (`docker compose`) ;
- au moins 2 Go de mémoire vive et 10 Go d’espace libre ;
- un compte autorisé à exécuter Docker.

Vérifiez l’installation :

```bash
docker --version
docker compose version
```

Si ces commandes ne fonctionnent pas, installez Docker en suivant la documentation de votre distribution. NetScope n’a pas besoin d’installer Python, Node.js ou PostgreSQL sur la machine : Docker les fournit dans les conteneurs.

## 2. Préparer la configuration

Placez-vous dans le dossier du projet :

```bash
cd /chemin/vers/soc
cp .env.example .env
chmod 600 .env
```

Ouvrez ensuite `.env` avec un éditeur :

```bash
nano .env
```

Exemple de configuration :

```dotenv
POSTGRES_PASSWORD=remplacez-par-un-mot-de-passe-long
SECRET_KEY=remplacez-par-une-cle-aleatoire-de-32-caracteres-minimum
MASTER_ENCRYPTION_KEY=remplacez-par-une-autre-cle-aleatoire-longue
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=remplacez-par-un-mot-de-passe-administrateur
HTTP_PORT=8080
```

Générez facilement des secrets aléatoires :

```bash
openssl rand -hex 32
```

Utilisez une valeur différente pour `POSTGRES_PASSWORD`, `SECRET_KEY`, `MASTER_ENCRYPTION_KEY` et `ADMIN_PASSWORD`. Conservez `MASTER_ENCRYPTION_KEY` : la perdre rendrait les identifiants SNMP enregistrés illisibles.

Ne transmettez jamais le fichier `.env` et ne le placez pas dans Git.

## 3. Installer et démarrer NetScope

Depuis le dossier du projet :

```bash
docker compose up -d --build
```

Le premier lancement peut prendre plusieurs minutes. Docker télécharge les images, construit l’application puis initialise PostgreSQL.

Contrôlez l’état des services :

```bash
docker compose ps
```

`backend-api` et `frontend` doivent être indiqués comme `healthy`. Les services attendus sont :

- `frontend` : interface web et proxy HTTP ;
- `backend-api` : API et authentification ;
- `scanner` : Nmap, ARP, DNS et SNMP ;
- `worker` et `scheduler` : tâches asynchrones ;
- `postgres` : base de données ;
- `redis` : file de tâches et protection de connexion.

Ouvrez ensuite :

- interface : <http://localhost:8080> ;
- documentation API : <http://localhost:8080/api/docs>.

Depuis un autre ordinateur, remplacez `localhost` par l’adresse IP du serveur, par exemple `http://192.168.1.20:8080`.

Connectez-vous avec `ADMIN_EMAIL` et `ADMIN_PASSWORD` définis dans `.env`. Lors de la mise à jour d'une installation existante, le compte `ADMIN_USERNAME` est automatiquement renommé avec cet email sans modifier son mot de passe ni son MFA. Après la première connexion, ouvrez **Paramètres** pour activer le MFA et, si nécessaire, changer le mot de passe.

## 4. Première configuration recommandée

### Ajouter un réseau et configurer le DNS

1. Ouvrez **Infrastructure Lab → Réseaux**.
2. Ajoutez le réseau au format CIDR, par exemple `192.168.1.0/24`.
3. Ouvrez **IPAM** et vérifiez que le préfixe est présent.
4. Dans **Paramètres → Résolution DNS**, saisissez le serveur DNS interne.
5. Entrez une IP connue et utilisez **Tester le PTR**.

Un serveur DNS interne permet de retrouver les noms d’hôtes. La box Internet, Active Directory, Pi-hole ou le serveur DNS de l’entreprise peut fournir cette résolution.

### Lancer un premier scan

1. Ouvrez **Scans**.
2. Sélectionnez le profil **Inventaire rapide**.
3. Choisissez un réseau privé enregistré.
4. Lancez le scan et attendez l’état `completed`.
5. Consultez **Équipements** pour ouvrir les fiches découvertes.

Commencez par un petit réseau `/24`. Les scans de réseaux très larges sont volontairement protégés.

### Configurer un Datacenter

Le menu **Datacenter** permet de construire une source de vérité manuelle :

1. créez un site ou un lieu ;
2. enregistrez d’abord son réseau dans **Réseaux/IPAM** ;
3. créez un VLAN et associez-le à ce préfixe ;
4. ajoutez les équipements avec leur IP, description, système et services ;
5. contrôlez les IP prises, disponibles et le taux d’occupation du VLAN.

NetScope refuse une IP hors du préfixe du VLAN ou déjà utilisée.

### Configurer SNMPv3

SNMPv3 sert à collecter les interfaces, VLAN, tables ARP/MAC et voisins LLDP/CDP des commutateurs, routeurs et pare-feu.

1. Ouvrez <http://localhost:8080/api/docs>.
2. Authentifiez-vous avec le bouton **Authorize** et un jeton obtenu par `/api/v1/auth/login`, ou utilisez l’interface lorsque l’option est proposée.
3. Appelez `POST /api/v1/credentials/snmpv3`.
4. Saisissez le nom, l’utilisateur SNMP, les protocoles et les mots de passe.
5. Lancez un scan avec le profil **Infrastructure SNMPv3** et cet identifiant.

Les secrets SNMP sont chiffrés avec `MASTER_ENCRYPTION_KEY` et ne sont jamais retournés par l’API. Préférez `authPriv`, SHA et AES. N’utilisez pas SNMPv1/v2c sur un réseau sensible.

#### Identifiant SNMP par défaut dans `.env`

La méthode recommandée consiste à créer les identifiants chiffrés dans l’API, ce qui permet d’utiliser des accès différents par site. Pour un petit réseau, un identifiant par défaut facultatif peut être défini dans `.env` :

```dotenv
SNMP_DEFAULT_VERSION=3
SNMPV3_USERNAME=netscope
SNMPV3_SECURITY_LEVEL=authPriv
SNMPV3_AUTH_PROTOCOL=SHA
SNMPV3_AUTH_PASSWORD=mot-de-passe-authentification
SNMPV3_PRIVACY_PROTOCOL=AES
SNMPV3_PRIVACY_PASSWORD=mot-de-passe-chiffrement
```

Laissez `SNMP_DEFAULT_VERSION` vide pour obliger l’utilisateur à sélectionner un identifiant chiffré à chaque scan.

#### Compatibilité SNMPv2c

NetScope prend aussi en charge SNMPv2c. Vous pouvez créer une communauté chiffrée au repos avec `POST /api/v1/credentials/snmpv2c`, ou configurer un défaut :

```dotenv
SNMP_DEFAULT_VERSION=2c
SNMPV2_COMMUNITY=changez-cette-communaute
```

SNMPv2c ne chiffre ni la communauté ni les données sur le réseau. Limitez-le à un VLAN d’administration isolé et filtré par pare-feu. SNMPv1 n’est pas pris en charge.

## 5. Guide des menus

Les menus visibles dépendent du rôle connecté :

- **Lecteur** : consulte les inventaires, alertes, cartes, rapports et archives ;
- **Opérateur** : dispose aussi des actions d’exploitation, notamment les scans,
  l’IPAM, les paramètres et les sauvegardes de configurations ;
- **Administrateur** : gère en plus les utilisateurs, connecteurs, sondes,
  identifiants sensibles et restaurations réseau.

### Vue principale

#### Tableau de bord

Cette page résume l’état du réseau : nombre d’équipements, disponibilité,
alertes, constructeurs, systèmes détectés et activité récente. Utilisez-la pour
repérer rapidement une hausse des équipements hors ligne ou des alertes
critiques. Cliquez sur une carte ou un graphique pour rejoindre la vue détaillée
correspondante. Les indicateurs reposent sur les dernières observations ; un
inventaire ancien doit être actualisé par un scan ou un connecteur passif.

#### Alertes

La liste centralise notamment les nouveaux équipements, conflits IP/MAC,
équipements hors ligne, échecs de scan, sondes indisponibles, interfaces
saturées, sécurité Wi-Fi faible et erreurs de sauvegarde/restauration.

- filtrez par état ou sévérité pour traiter d’abord les alertes critiques ;
- ouvrez l’équipement associé pour examiner ses preuves et son historique ;
- acquittez une alerte prise en charge et résolvez-la lorsque la cause est
  corrigée ;
- évitez de résoudre manuellement une panne encore active : les évaluations
  automatiques peuvent la rouvrir.

#### Scans

Cette page lance et planifie la découverte active. Saisissez une adresse ou un
préfixe CIDR, choisissez la VRF, un profil, éventuellement une sonde distante et
un identifiant SNMP. L’historique indique le module actif, la progression, le
nombre de résultats et les erreurs. Le diagnostic SNMP/OID permet de tester un
équipement avant un inventaire complet.

Commencez par **Inventaire rapide** sur un petit réseau privé. Réservez les
profils TCP/UDP approfondis aux plages autorisées. Une sonde distante doit être
en ligne, appartenir à la même VRF et annoncer toutes les capacités du profil.
Les secrets SNMP restent sur le scanner central et ne sont jamais transmis aux
sondes.

### Infrastructure Lab

#### Vue d’ensemble

La vue Infrastructure Lab présente les équipements réseau gérés, leurs ports,
VLAN, états administratifs/opérationnels et dernières métriques. Elle sert au
suivi quotidien des commutateurs et routeurs collectés par SNMP. Deux collectes
sont nécessaires avant de calculer un débit ; ouvrez une interface pour examiner
son historique d’utilisation et d’erreurs.

#### Datacenter

Cette page construit la documentation manuelle des sites : lieux, VLAN,
équipements, services et occupation des adresses. Créez d’abord le réseau dans
**Réseaux** ou **IPAM**, associez-le au VLAN, puis ajoutez les équipements.
NetScope refuse une adresse hors préfixe ou déjà utilisée. Utilisez cette vue
comme source de vérité pour les éléments qui ne peuvent pas être découverts.

#### Équipements

L’inventaire regroupe les actifs manuels et découverts. Recherchez ou filtrez un
équipement, puis ouvrez sa fiche pour consulter :

- adresses IPv4/IPv6, identifiants et services ;
- constructeur, modèle, système et niveau de confiance ;
- preuves brutes, métadonnées et historique d’identité IP/MAC ;
- état, rôle, site et modifications manuelles.

Archivez plutôt que supprimer un équipement qui doit rester traçable. En cas de
conflit IP/MAC, examinez l’historique avant de fusionner ou corriger les données.

#### IPAM

L’IPAM gère les préfixes IPv4/IPv6, VRF, passerelles, DNS, plages, réservations
et adresses. Créez la VRF avant ses préfixes et sélectionnez toujours la bonne
VRF lors d’un scan. La capacité, le nombre d’adresses utilisées et le taux
d’occupation sont calculés automatiquement. Avant de supprimer un préfixe,
contrôlez ses adresses, VLAN et réseaux dépendants.

#### Réseaux

Cette vue déclare les réseaux autorisés et leur état. Elle sert de garde-fou aux
scans et relie la documentation réseau à l’IPAM. Utilisez un CIDR canonique
(`192.168.10.0/24`, par exemple), un nom explicite et l’état adapté. La
suppression d’un réseau ne doit entraîner la purge de son préfixe IPAM qu’après
vérification des dépendances affichées.

#### Relations

La topologie rassemble les liens manuels et ceux inférés par LLDP/CDP ou par les
données réseau. Actualisez la topologie après une collecte SNMP, filtrez les
nœuds trop nombreux et ouvrez un lien pour vérifier ses ports source/destination.
Les liens manuels permettent de compléter une infrastructure non compatible avec
LLDP/CDP ; indiquez leur nature afin de les distinguer des relations découvertes.

### Intelligence

#### Constructeurs

Cette page agrège les actifs par constructeur et type d’équipement. Elle aide à
mesurer l’hétérogénéité du parc et à repérer les matériels non identifiés. Un
constructeur absent signifie généralement qu’aucune adresse MAC exploitable ou
preuve SNMP fiable n’a été collectée. Consultez alors la fiche de l’actif et ses
preuves d’identification.

#### Routage et Wi-Fi

La partie routage affiche les routes IPv4/IPv6, protocoles, next-hops et
interfaces collectés. La partie Wi-Fi présente contrôleurs, radios, bandes,
canaux, BSSID, VLAN, sécurité et clients. Vérifiez en priorité les réseaux OPEN,
WEP ou WPA signalés comme critiques et les radios durablement saturées. Les
observations Wi-Fi automatisées nécessitent un connecteur de type Wi-Fi créé
dans **Connecteurs**.

### Administration

#### Rapports

Générez ou envoyez des rapports d’inventaire, IPAM, scans, constructeurs et
sécurité aux formats proposés. L’envoi nécessite une configuration SMTP valide
et un expéditeur présent dans `SMTP_SENDERS`. Testez d’abord l’état SMTP, puis
créez une planification avec une fréquence raisonnable et des destinataires
autorisés. Vérifiez les journaux du worker si un envoi reste en échec.

#### Archives

Les équipements archivés sont conservés hors de l’inventaire actif avec leur
traçabilité. Utilisez la restauration pour remettre un actif dans l’inventaire.
La suppression définitive doit rester exceptionnelle, notamment si l’historique
est utile à un audit ou à l’analyse d’une ancienne attribution IP.

#### Paramètres

Cette page regroupe les réglages d’exploitation : DNS/PTR, sécurité du compte,
MFA, options de plateforme et supervision. Le panneau de supervision actualisé
toutes les quinze secondes affiche les conteneurs, leurs healthchecks,
redémarrages et l’espace disque disponible. Vert signifie opérationnel ; rouge
impose de consulter `docker compose logs nom-du-service`. Conservez les codes de
récupération MFA dans un emplacement sûr avant de fermer la page d’activation.

#### Configurations

Le coffre conserve les accès SSH chiffrés et les versions de configuration des
équipements Cisco IOS, Arista EOS, Junos et FortiOS. Enregistrez la clé publique
hôte OpenSSH complète afin d’empêcher une interception, puis sélectionnez
l’équipement, l’identifiant et la plateforme pour lancer une sauvegarde.

Le téléchargement et la restauration sont réservés aux administrateurs. Avant
toute restauration, NetScope vérifie l’empreinte de la version et crée une
sauvegarde de secours. Saisissez exactement `RESTORE nom` ou `RESTORE adresse`.
FortiOS est volontairement limité à la sauvegarde. Effectuez les restaurations
pendant une fenêtre de maintenance avec un accès de secours à l’équipement.

#### Connecteurs

Les connecteurs ingèrent des observations passives DHCP, ARP, DNS, génériques ou
Wi-Fi. À la création ou au renouvellement, copiez immédiatement le jeton : il
n’est affiché qu’une fois. Configurez la source pour appeler l’endpoint indiqué
avec `X-Connector-Token`, surveillez sa dernière activité et son dernier message
d’erreur, puis désactivez ou renouvelez tout jeton suspect. Les identifiants
d’événement empêchent les doublons lors d’un renvoi.

#### Sondes

Les sondes exécutent ICMP, ARP, Nmap et DNS depuis des sites ou VRF distants sans
port entrant. Créez la sonde, copiez son jeton à affichage unique, associez le bon
site et la bonne VRF, puis déployez `probe-agent`. L’état passe en ligne après le
premier heartbeat. Si elle reste hors ligne, vérifiez l’URL HTTPS, le jeton,
l’horloge du système et les logs de l’agent. Renouveler le jeton révoque
immédiatement l’ancien.

#### Utilisateurs

Les administrateurs créent les comptes, attribuent les rôles et activent ou
désactivent les accès. Utilisez une adresse email comme identifiant, accordez le
plus petit rôle nécessaire et préférez la désactivation à la suppression pour
conserver l’audit. Chaque utilisateur doit remplacer son mot de passe initial et
activer le MFA. Ne partagez jamais un compte administrateur entre plusieurs
personnes.

### Déconnexion

Le bouton situé à droite de l’utilisateur ferme la session côté serveur et
efface les données d’authentification du navigateur. Utilisez-le sur tout poste
partagé ; fermer uniquement l’onglet ne garantit pas la révocation immédiate de
la session.

## 6. Commandes utiles

### Configurer l’envoi SMTP des rapports

Renseignez `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` et `SMTP_SENDERS` dans `.env`, puis redémarrez l’API. `SMTP_SENDERS` accepte plusieurs expéditeurs séparés par des virgules. Utilisez le port 587 avec `SMTP_USE_TLS=true`, ou le port 465 avec `SMTP_USE_SSL=true` et `SMTP_USE_TLS=false`. Le menu **Administration → Rapports** permet ensuite de choisir le rapport, l’expéditeur autorisé et les destinataires.

Afficher l’état :

```bash
docker compose ps
```

Suivre les journaux :

```bash
docker compose logs -f
```

Redémarrer :

```bash
docker compose restart
```

Rebuild après une mise à jour :

```bash
docker compose up -d --build
```

Arrêter sans supprimer les données :

```bash
docker compose down
```

Ne lancez pas `docker compose down -v` sauf si vous voulez effacer définitivement la base PostgreSQL et les volumes.

## 7. Vérifier l’installation

Lancer la simulation des menus et API en remplaçant le mot de passe :

```bash
python3 scripts/smoke_all.py --password 'votre-mot-de-passe-admin'
```

Avec un vrai scan réseau :

```bash
python3 scripts/smoke_all.py --password 'votre-mot-de-passe-admin' --scan
```

Les rapports sont enregistrés dans `logs/reports/`. Les journaux détaillés se trouvent dans :

```text
logs/api/
logs/frontend/
logs/scanner/
logs/worker/
logs/scheduler/
```

## 8. Sauvegarder et restaurer

### Sauvegarde automatique

Le service `backup` crée automatiquement une sauvegarde PostgreSQL au format
`custom` dans `backups/`. Par défaut, il s'exécute toutes les 24 heures et
conserve 14 jours d'historique. Ces valeurs se configurent dans `.env` :

```dotenv
BACKUP_INTERVAL_HOURS=24
BACKUP_RETENTION_DAYS=14
```

Vérifiez son état et son dernier journal :

```bash
docker compose ps backup
docker compose logs --tail=20 backup
ls -lh backups/
```

Les fichiers sont écrits d'abord avec l'extension `.tmp`, puis renommés
uniquement après la réussite de `pg_dump`. Une sauvegarde doit toujours être
copiée sur un autre hôte ou stockage objet pour protéger aussi la panne du
serveur.

### Sauvegarde manuelle

Créer une sauvegarde PostgreSQL :

```bash
docker compose exec -T postgres pg_dump -U netscope -d netscope -Fc > netscope-backup.dump
```

Conservez également une copie sécurisée du `.env`, séparément de la sauvegarde.

Restaurer dans une base vide :

```bash
docker compose exec -T postgres pg_restore -U netscope -d netscope --clean --if-exists < netscope-backup.dump
```

Testez toujours une restauration avant de considérer une sauvegarde comme valide.

### Coffre SSH et configurations des équipements

La page **Administration → Configurations** permet de conserver des identifiants
SSH chiffrés, de versionner les configurations Cisco IOS, Arista EOS, Junos et
FortiOS, puis de télécharger une version. La restauration automatique est
réservée aux administrateurs et disponible pour Cisco IOS, EOS et Junos.

Chaque identifiant doit contenir la clé publique hôte OpenSSH attendue : NetScope
refuse une connexion si l'équipement présente une autre clé. Avant une
restauration, NetScope contrôle l'empreinte SHA-256 de la version sélectionnée et
capture automatiquement la configuration courante comme sauvegarde de secours.
Une confirmation `RESTORE nom-équipement` ou `RESTORE adresse-ip` est exigée.

En production, utilisez un compte SSH dédié avec les droits minimaux nécessaires,
limitez son accès par ACL et renouvelez régulièrement son mot de passe ou sa clé.
FortiOS reste volontairement en sauvegarde seule : sa restauration automatique
n'est pas déclenchée par cette version.

## 9. Supervision et alertes facultatives

NetScope fournit un profil de supervision avec Prometheus, Grafana,
Alertmanager, Blackbox Exporter et des exporters PostgreSQL, Redis et
sauvegardes. Il contrôle l'interface, l'API prête, PostgreSQL, Redis et l'âge de
la dernière sauvegarde.

Avant l'activation, remplacez au minimum `GRAFANA_ADMIN_PASSWORD` dans `.env`,
puis lancez :

```bash
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml \
  --profile monitoring up -d
```

Les interfaces restent accessibles seulement depuis le serveur par défaut :

- Grafana : `http://127.0.0.1:3000` ;
- Prometheus : `http://127.0.0.1:9090` ;
- Alertmanager : `http://127.0.0.1:9093` ;
- notifications ntfy : `http://127.0.0.1:8081/netscope-alerts`.

Pour recevoir les alertes, ouvrez le sujet `netscope-alerts` dans l'application
ntfy ou dans son interface web. Alertmanager envoie une notification quand
NetScope ne répond plus pendant deux minutes, quand un exporter PostgreSQL ou
Redis tombe, ou quand aucune sauvegarde valide n'a été produite depuis 36
heures. Pour un accès distant, publiez ces interfaces derrière HTTPS avec une
authentification ; ne remplacez pas `MONITORING_BIND=127.0.0.1` par `0.0.0.0`
sur un serveur exposé.

## 10. Dépannage simple

Lancez d'abord le diagnostic automatique :

```bash
make diagnose
```

Il contrôle la configuration Compose, les conteneurs, les healthchecks, l'accès HTTP et recherche les erreurs critiques dans les journaux des dix dernières minutes. Utilisez `LOG_SINCE=1h make diagnose` pour élargir la période.

Il vérifie également l'espace disque et signale tout journal dépassant 100 Mio. Les logs internes du moteur Docker sont limités à trois fichiers de 10 Mio par conteneur. `WORKER_CONCURRENCY` et `SCANNER_CONCURRENCY` valent 2 par défaut afin d'éviter une consommation mémoire excessive ; augmentez-les progressivement sur les serveurs disposant de davantage de mémoire.

Les administrateurs disposent aussi d'un panneau **Paramètres → Supervision de la plateforme**. Il affiche toutes les quinze secondes l'état de chaque conteneur, son healthcheck, ses redémarrages et l'espace disque disponible. La lecture du socket Docker est isolée dans `docker-monitor` ; l'API principale n'y accède jamais directement.

Le menu **Alertes** conserve les nouveaux équipements, les équipements hors ligne et les scans en échec. Un actif réellement observé passe hors ligne après `ASSET_OFFLINE_MINUTES` (60 minutes par défaut) sans nouvelle observation ; les actifs créés uniquement à la main sont exclus de cette règle. Une nouvelle observation remet automatiquement l'actif en ligne et résout son alerte. Les alertes résolues sont conservées pendant `ALERT_RETENTION_DAYS` (90 jours par défaut).

L'IPAM accepte les mêmes préfixes et adresses dans plusieurs VRF. Sélectionnez la VRF lors de la création du préfixe et lors du lancement ou de la planification d'un scan. La fiche d'un actif conserve l'historique des couples IP/MAC observés. Si une IP et une MAC pointent vers deux actifs différents, NetScope donne priorité à la MAC, ne déplace aucune association silencieusement et crée une alerte critique à examiner.

Les profils **Audit approfondi TCP** et **Services UDP essentiels** complètent l'inventaire standard. Le profil UDP est volontairement limité aux 100 ports les plus courants et à 50 paquets/s. L'historique affiche le module actif, la progression et le nombre de résultats corrélés.

La page **Connecteurs** permet à un administrateur de créer des sources passives DHCP, ARP, DNS ou génériques. Chaque source reçoit un jeton affiché une seule fois, révocable et renouvelable. Elle transmet jusqu'à 500 événements par requête à `POST /api/v1/passive-ingest` avec l'en-tête `X-Connector-Token`. Les identifiants d'événements rendent les renvois idempotents et les observations alimentent le même moteur de corrélation IP/MAC que les scans actifs.

```json
{"events":[{"event_id":"dhcp-2026-000123","ip_address":"192.168.1.42","mac_address":"00:11:22:33:44:55","hostname":"poste-42","observed_at":"2026-07-16T10:00:00Z"}]}
```

Une source est limitée à 120 requêtes par minute. Les reçus d'anti-rejeu sont conservés 30 jours et les événements datés de plus de 7 jours ou de plus de 5 minutes dans le futur sont refusés.

### Sondes distribuées

Une sonde distante initie elle-même toutes les connexions HTTPS vers NetScope : aucun port entrant n'est nécessaire sur le site distant. Créez-la dans **Sondes**, copiez son jeton, puis déployez-la :

```bash
cd probe-agent
NETSCOPE_URL=https://netscope.example.com PROBE_TOKEN='jeton-affiché-une-fois' docker compose up -d --build
```

La sonde publie un heartbeat, récupère une tâche à la fois et renvoie uniquement les observations appartenant au préfixe demandé. Les tâches abandonnées sont remises en file après 15 minutes. Les résultats sont limités à 5 Mo. ICMP, ARP, Nmap et DNS sont pris en charge ; les profils SNMP et leurs secrets restent exécutés par le scanner central.

Les collectes SNMP enregistrent également les compteurs 64 bits, erreurs, vitesse et utilisation de chaque interface. Deux collectes sont nécessaires pour calculer les débits entrants/sortants ; les dernières valeurs apparaissent dans **Infrastructure Lab** et l'historique sur 90 jours est disponible par l'API `/switch-ports/{id}/metrics`. Une utilisation supérieure à 90 % sur deux collectes ouvre une alerte, résolue sous 80 %. Les voisins LLDP/CDP sont associés à leurs vrais index et noms de ports locaux/distants.

La vue **Routage et Wi-Fi** rassemble les routes IPv4/IPv6 collectées par SNMP, les next-hops, protocoles et interfaces. Le voisinage moderne `ipNetToPhysical` ajoute les associations IPv6/MAC. Les observations de contrôleurs Wi-Fi enregistrent radios, bandes 2,4/5/6 GHz, canaux jusqu'à 320 MHz, BSSID, VLAN, sécurité et clients ; OPEN, WEP et WPA déclenchent une alerte critique. Une radio à au moins 80 % sur deux observations ouvre une alerte, résolue sous 60 %. Pour automatiser l'envoi, créez un connecteur de type Wi-Fi et appelez `POST /api/v1/wireless-ingest` avec son `X-Connector-Token` (120 requêtes/minute maximum).

### La page ne s’ouvre pas

```bash
docker compose ps
docker compose logs --tail=100 frontend backend-api
```

Vérifiez aussi que le port configuré dans `HTTP_PORT` est autorisé par le pare-feu et n’est pas déjà utilisé.

### Un conteneur redémarre continuellement

```bash
docker compose logs --tail=200 nom-du-service
```

Les causes fréquentes sont un secret incorrect, PostgreSQL indisponible, des permissions insuffisantes sur `logs/` ou une erreur dans `.env`.

### Le scan ne trouve aucun appareil

- vérifiez que la cible est le bon réseau CIDR ;
- commencez par un `/24` privé ;
- vérifiez les pare-feu des équipements ;
- pour ARP, le scanner doit généralement être sur le même réseau local ;
- pour SNMPv3, vérifiez utilisateur, niveau de sécurité, SHA/AES et filtrage de l’équipement.

### Les noms d’ordinateurs sont absents

Ajoutez le serveur DNS interne dans **Paramètres**, vérifiez qu’un enregistrement PTR existe, puis relancez un scan. Les adresses MAC aléatoires des téléphones peuvent empêcher l’identification fiable du constructeur.

### Erreur `429` à la connexion

Après cinq mots de passe incorrects, NetScope bloque les essais pendant cinq minutes pour protéger le compte. Attendez avant de réessayer.

## 11. Sécurité avant exposition

Un exemple Caddy complet est fourni dans [docs/REVERSE_PROXY.md](docs/REVERSE_PROXY.md). Il active HTTPS, HSTS, le renouvellement automatique du certificat et les journaux JSON. Lorsque Caddy tourne sur le même hôte, définissez `HTTP_BIND=127.0.0.1`.

- changez tous les secrets de `.env` ;
- activez le MFA ;
- n’exposez pas directement le port 8080 sur Internet ;
- placez NetScope derrière un reverse proxy HTTPS avec un certificat valide ;
- limitez l’accès par pare-feu ou VPN ;
- sauvegardez PostgreSQL et `.env` ;
- installez régulièrement les mises à jour du système et reconstruisez les images.

Le scanner dispose de capacités réseau élevées nécessaires à Nmap. N’ajoutez pas d’autres volumes ou accès hôte au conteneur scanner.

## 12. Fonctionnalités principales

- inventaire manuel et découvert, édition, archivage et restauration ;
- IPAM IPv4/IPv6, DNS, préfixes, adresses et utilisation ;
- sites, Datacenter, VLAN, équipements et services ;
- scans ICMP, ARP, Nmap, DNS et SNMPv3 ;
- interfaces, ARP/MAC, LLDP/CDP et corrélation aux ports ;
- topologie manuelle et inférée ;
- constructeurs normalisés, systèmes et preuves d’identification ;
- MFA, rôles, audit, limitation de connexion et chiffrement des secrets ;
- export CSV, API REST et journaux structurés.

## Limites actuelles

- les MIB propriétaires peuvent nécessiter une adaptation par constructeur ;
- NetScope est un outil d’inventaire et ne remplace pas un scanner de vulnérabilités ou un SIEM.

## Licence

NetScope est distribué sous licence [MIT](LICENSE). Vous pouvez l’utiliser, le copier, le modifier, le redistribuer et l’intégrer à des projets personnels ou commerciaux, sous réserve de conserver la notice de copyright et la licence.

Le logiciel est fourni sans garantie. Les contributions et améliorations sont les bienvenues.
