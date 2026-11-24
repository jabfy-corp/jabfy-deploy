# Jabfy Deploy

Point d'entrée unique pour assembler, démarrer et arrêter Jabfy. Les dépôts
applicatifs fournissent leurs images et bibliothèques ; Deploy possède la topologie,
les connexions, les volumes et les contrôles de santé.

Documentation du composant : [docs/README.md](docs/README.md). Ces pages sont la
source destinée à la section Composants de `jabfy-docs`, après fusion sur `main`.

## Deploy V1 — lancer la maison virtuelle

Depuis ce dépôt, avec Docker Compose v2, Git et Python 3.9 ou ultérieur :

```bash
python3 scripts/deploy.py up
python3 scripts/deploy.py model
python3 scripts/deploy.py status
```

Ouvrir [la maison virtuelle](http://127.0.0.1:8080). La commande `model` installe
le modèle local pour l'onglet IA. Pour arrêter les services et conserver maison,
audit et modèle, utiliser `python3 scripts/deploy.py down`.

V1 désigne ici l'orchestrateur. Il assemble les versions disponibles de Core,
Simulation, Bus et Guard. Le périmètre applicatif reste la maison virtuelle V0.0.1.
Voir le [guide V1 et les tests reproductibles](docs/deploy-v1.md).

## V0.0.1 — lancement historique depuis les copies de travail

Placer `jabfy-deploy`, `jabfy-core`, `jabfy-bus`, `jabfy-guard` et `jabfy-simulation`
côte à côte avec les changements V0.0.1. Ouvrir Docker Desktop, puis, depuis ce dépôt :

```bash
python3 scripts/start.py --check  # vérifie la configuration, sans démarrer
python3 scripts/start.py          # construit, démarre et télécharge le modèle
```

Ouvrir **http://127.0.0.1:8080**. `--no-ai` évite le téléchargement du modèle ; les
contrôles manuels restent disponibles. Python 3 est nécessaire pour le lanceur.

```bash
docker compose -f compose.local.yml ps
docker compose -f compose.local.yml logs --tail=100
docker compose -f compose.local.yml down # conserve les données, ne pas ajouter -v
```

Sans lanceur : `docker compose -f compose.local.yml up --build -d --wait`, puis
`docker compose -f compose.local.yml exec ollama ollama pull qwen2.5:1.5b` pour l'IA.

Cette configuration construit les sources locales tant que les images intégrées
ne sont pas publiées. Elle lance Simulation, Core, Ollama et MQTT. **Guard est une
bibliothèque et Bus reste embarqué dans le runtime Simulation** : pas de faux
services indépendants. Seuls les appareils virtuels sont pilotés.

Le nom technique du projet Compose reste `jabfy-simulation` pour conserver les
conteneurs/volumes existants. Le plan et l'audit restent dans `../jabfy-simulation/data`.
Ne pas lancer l'ancienne stack en parallèle. Plus de détails : [guide V0.0.1](docs/v0.0.1.md).

Tests de l'orchestration : `python3 -m pytest -q tests` (installer `pytest` et `PyYAML`).

## Déploiement par images publiées — configuration historique

Le fichier `docker-compose.yml` conserve la configuration GHCR historique, séparée
de `compose.local.yml`. Ses digests dans `deployment.env` sont encore des placeholders :
ce n'est pas le lancement de la V0.0.1 et il ne faut pas démarrer les deux stacks ensemble.
Le chemin par images immuables reste prévu pour la distribution, sans build local.

### Setup

1. Replace every placeholder in the versioned `deployment.env` lock file with
   the digest shown by a successful source
   repository publishing workflow.
2. Authenticate the target machine to GHCR if the images remain private.
3. Start the stack:

```bash
docker compose --env-file deployment.env up -d
```

The voice service is optional and disabled by default. Start it only when its
runtime dependencies are suitable for the target host:

```bash
docker compose --env-file deployment.env --profile voice up -d
```

## Image updates

Producer workflows can send an `image-published` repository-dispatch event. The
`update-image-digest` workflow validates the SHA-256 digest and opens a pull
request that updates `deployment.env`. Configure these repository secrets before
enabling cross-repository updates:

- `JABFY_DEPLOY_DISPATCH_TOKEN` in each producer repository: a fine-grained
  token or GitHub App token with access to dispatch events in `jabfy-deploy`.
- `JABFY_DEPLOY_PR_TOKEN` in this repository when `GITHUB_TOKEN` cannot create
  pull requests under the organisation's branch policies.

Review each generated pull request before merging it. The merged file is the
auditable record of the exact images deployed.
