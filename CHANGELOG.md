# Changelog

## 0.0.3 — 2026-07-18

- nouveau menu Sondes avec découverte forcée et suivi quasi-direct des tâches ;
- remontée des réseaux IPv4 visibles depuis les agents distribués ;
- inventaire des équipements observés par sonde et accès à leur fiche ;
- déploiement de sonde en réseau hôte pour les scans LAN ;
- migration de routes de sonde réentrante après une interruption ;
- harmonisation des versions backend, API et frontend.
- correction des profils Nmap standard/profond sur les sondes non-root : la détection de services reste active et l'empreinte OS est désactivée proprement.
- sonde LAN exécutée avec l'eUID root isolé pour restaurer la capture ARP, les MAC/OUI et l'empreinte OS.

## 0.0.2 — 2026-07-12

- migrations Alembic compatibles avec les installations neuves et existantes ;
- gestion des utilisateurs, rôles et sessions révocables ;
- scans et rapports SMTP planifiés depuis l’interface ;
- diagnostic interactif SNMP/OID et reconnaissance par enterprise OID ;
- VRF, hiérarchie IPAM, plages et réservations DHCP ;
- rapports PDF et sauvegardes versionnées de configuration ;
- base OUI hors ligne, reverse proxy Caddy HTTPS et documentation associée ;
- tests Playwright, CI GitHub Actions et correction du chemin d’import pytest.

## 0.0.1 — 2026-07-11

Première version publique de NetScope.

- inventaire réseau manuel et découvert ;
- scans ICMP, ARP, Nmap, DNS, SNMPv3 et SNMPv2c ;
- IPAM, sites, VLAN, Datacenter, services et capacité IP ;
- collecte ARP/MAC, interfaces, LLDP/CDP et relations manuelles ;
- reconnaissance des constructeurs, Android, Google Pixel et Apple iOS ;
- MFA, rôles, chiffrement des secrets et limitation de connexion ;
- rapports CSV et envoi SMTP ;
- journaux structurés et simulation fonctionnelle complète ;
- correction de Swagger UI sous CSP ;
- correction des cibles SNMP pour interroger les hôtes découverts plutôt qu’un CIDR.
- mise à niveau des dépendances Python vulnérables et verrouillage des dépendances frontend.
