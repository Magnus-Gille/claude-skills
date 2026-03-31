---
name: deploy
description: Deploy Grimnir services to Pi hosts. Supports deploying all services, a subset, or a single service by name.
---

# /deploy - Deploy Grimnir Services

Deploy services to Pi hosts via the centralized deploy script in the grimnir repo.

## Usage

- `/deploy` — deploy all services
- `/deploy munin-memory` — deploy a single service
- `/deploy munin-memory hugin heimdall` — deploy several services

## Service Registry

| Service | Host | Path | Type |
|---|---|---|---|
| munin-memory | huginmunin.local (Pi 1) | ~/repos/munin-memory | service |
| hugin | huginmunin.local (Pi 1) | ~/repos/hugin | service |
| heimdall | huginmunin.local (Pi 1) | ~/repos/heimdall | service |
| ratatoskr | huginmunin.local (Pi 1) | ~/repos/ratatoskr | service |
| skuld | huginmunin.local (Pi 1) | ~/repos/skuld | timer |
| mimir | nas.local (Pi 2) | ~/repos/mimir | service |

## Workflow

### Step 1: Validate requested services

If the user specified service names, check they match the registry above. If a name doesn't match, tell the user and list the valid names.

### Step 2: Run deploy script

The deploy script lives at `~/repos/grimnir/scripts/deploy.sh`. Run it from the grimnir repo:

```bash
# All services
/Users/magnus/repos/grimnir/scripts/deploy.sh

# Specific services
/Users/magnus/repos/grimnir/scripts/deploy.sh munin-memory hugin
```

The script handles: git stash + pull, npm ci, build (for mimir), systemd restart (for services), and reports pass/fail per service.

### Step 3: Report results

Show the summary table from the script output. If any service failed:
- Check `ssh magnus@<host> "journalctl -u <service> -n 20 --no-pager"` for logs
- Report the error to the user

### Step 4: Health check (if all passed)

For each deployed service, verify the health endpoint responds:

```bash
# Pi 1 services
ssh magnus@huginmunin.local "curl -sf localhost:3030/health && echo; curl -sf localhost:3032/health && echo; curl -sf localhost:3033/health && echo; curl -sf localhost:3034/health && echo"

# Pi 2
ssh magnus@nas.local "curl -sf localhost:3031/health"
```

Port mapping: munin-memory=3030, mimir=3031, hugin=3032, heimdall=3033, ratatoskr=3034, skuld=3040 (no health endpoint — timer only).

Only check health for the services that were actually deployed, not all of them.
