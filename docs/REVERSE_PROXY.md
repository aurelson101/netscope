# Reverse proxy HTTPS prêt à l’emploi

NetScope doit rester lié à une interface privée et être publié par un reverse proxy. L’exemple [Caddyfile](reverse-proxy/Caddyfile) obtient et renouvelle automatiquement un certificat TLS public.

1. Faites pointer `netscope.example.com` vers le serveur et remplacez ce nom dans le fichier.
2. Limitez le port NetScope à la boucle locale dans `.env` avec `HTTP_BIND=127.0.0.1`.
3. Dans `docker-compose.yml`, la publication du frontend utilise `${HTTP_BIND:-0.0.0.0}:${HTTP_PORT:-8080}:80`.
4. Installez Caddy, copiez le fichier vers `/etc/caddy/Caddyfile`, puis exécutez `sudo systemctl reload caddy`.
5. Autorisez uniquement TCP/80 et TCP/443 depuis les clients attendus. Ne publiez ni PostgreSQL, ni Redis, ni le backend.

Pour un certificat interne, remplacez la première ligne par un nom DNS interne et ajoutez `tls internal`; distribuez ensuite l’autorité racine Caddy aux postes clients. Vérifiez enfin `https://netscope.example.com/health` et la présence de l’en-tête HSTS.
