# Deployment-Runbook: Hetzner Cloud VPS

Ziel: Die App läuft öffentlich unter `https://DEINE-DOMAIN` — App + PostgreSQL +
Caddy als Docker-Compose-Verbund, HTTPS automatisch via Let's Encrypt.

Hinweis zu UI-Beschreibungen: Die Hetzner-Konsole ändert sich gelegentlich —
Menünamen können leicht abweichen (Glaube ich: Stand der Beschreibung kann
veralten, das Grundprinzip bleibt).

---

## 0. Voraussetzungen

- Hetzner-Cloud-Konto (console.hetzner.cloud)
- Eine Domain bzw. Subdomain, deren DNS du verwalten kannst
- Ein SSH-Schlüsselpaar auf deinem Rechner. Falls noch keins existiert:
  ```bash
  ssh-keygen -t ed25519 -C "lernscript-deploy"
  ```
  Den **öffentlichen** Schlüssel (`~/.ssh/id_ed25519.pub`) brauchst du gleich.

## 1. Server anlegen

1. Hetzner-Konsole → Projekt → **Server hinzufügen**
2. Standort: Nürnberg oder Falkenstein (Deutschland, DSGVO)
3. Image: **Ubuntu 24.04**
4. Typ: kleinster/zweitkleinster Shared-vCPU-Server reicht für den Start
   (2 vCPU / 4 GB empfohlen — Preise beim Bestellen prüfen)
5. **SSH-Key**: deinen öffentlichen Schlüssel einfügen (NICHT Passwort-Login wählen)
6. Erstellen → notiere die **öffentliche IPv4-Adresse**

## 2. Hetzner-Firewall (vor dem ersten Login!)

Konsole → Firewalls → neue Firewall, dem Server zuweisen. Eingehende Regeln:

| Port | Protokoll | Zweck |
|---|---|---|
| 22 | TCP | SSH |
| 80 | TCP | HTTP (Let's-Encrypt-Challenge + Redirect) |
| 443 | TCP + UDP | HTTPS (UDP für HTTP/3) |

Alles andere eingehend: blockiert (Default).

## 3. DNS setzen

Beim Domain-Anbieter einen **A-Record** anlegen:
`lernscript.deine-domain.de → <Server-IPv4>`
(Optional AAAA-Record für die IPv6 des Servers.)
DNS-Propagation kann einige Minuten dauern — ohne korrekten Record kann
Caddy kein Zertifikat holen.

## 4. Erster Login + Grundhärtung

```bash
ssh root@<SERVER-IP>

# System aktuell
apt update && apt upgrade -y

# SSH härten: Passwort-Login abschalten (Key liegt ja schon drauf)
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh
```

WICHTIG: Bevor du das Terminal schließt, in einem ZWEITEN Terminal testen,
dass der Key-Login noch funktioniert.

## 5. Docker installieren

```bash
# Offizielles Convenience-Skript von Docker
curl -fsSL https://get.docker.com | sh
docker --version && docker compose version
```

## 6. Projekt auf den Server holen

```bash
mkdir -p /opt && cd /opt
git clone https://github.com/<DEIN-NUTZER>/<DEIN-REPO>.git lernscript
cd lernscript
```

## 7. Konfiguration (.env)

```bash
cp .env.production.example .env
nano .env
```

Ausfüllen:
- `DOMAIN` — deine (Sub-)Domain aus Schritt 3
- `ANTHROPIC_API_KEY` — Key aus der Anthropic-Konsole
- `SECRET_KEY` — erzeugen: `openssl rand -hex 32`
- `INVITE_CODE` — selbst festlegen
- `POSTGRES_PASSWORD` — erzeugen: `openssl rand -hex 24`

## 8. Starten

```bash
docker compose up -d --build
docker compose ps          # alle drei Services "running"/"healthy"?
docker compose logs -f app # Startlog ansehen (Strg+C zum Verlassen)
```

Dann im Browser: `https://DEINE-DOMAIN` → Login-Seite sollte erscheinen,
Zertifikat gültig (Schloss-Symbol). Erstes Konto über /register mit deinem
INVITE_CODE anlegen.

## 9. Backups aktivieren

```bash
crontab -e
# Zeile ergänzen:
0 3 * * * /opt/lernscript/scripts/backup.sh >> /var/log/lernscript-backup.log 2>&1
```

Test von Hand: `/opt/lernscript/scripts/backup.sh` — danach liegt unter
`/opt/lernscript/backups/` eine `.sql.gz`.

Wiederherstellen (falls je nötig):
```bash
gunzip -c backups/lernscript_DATUM.sql.gz | docker compose exec -T db psql -U lernscript lernscript
```

## 10. Updates einspielen (Standard-Ablauf)

```bash
cd /opt/lernscript
git pull
docker compose up -d --build
```

## Fehlersuche

| Symptom | Prüfen |
|---|---|
| Kein Zertifikat / Browser-Warnung | DNS-A-Record korrekt? Port 80+443 offen? `docker compose logs caddy` |
| App startet nicht | `docker compose logs app` — häufig: leere Pflicht-Variable in `.env` |
| 502 Bad Gateway | App-Container läuft nicht (`docker compose ps`), DB healthy? |
| Login klappt, Session verloren | `SECRET_KEY` gesetzt und unverändert? |

## Bewusste MVP-Grenzen (spätere Ausbaustufen)

- Backups liegen auf demselben Server (kein Off-Site) — nächste Stufe:
  zusätzlich in Hetzner Object Storage o. Ä. kopieren
- Kein Monitoring/Alerting — nächste Stufe: z. B. Uptime-Check auf /health
- Deploy manuell — nächste Stufe: GitHub-Actions-Auto-Deploy
