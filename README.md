# Jabfy Deploy

Central deployment configuration for the Jabfy services published to GitHub
Container Registry. This repository never builds application source code; it
deploys immutable image digests produced by the service repositories.

## Setup

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
