# artwork
Project Artwork and Lore

## Publishing GNOME wallpapers

The publishing workflow builds and pushes with Podman, then keyless-signs the
multi-arch image and publishes provenance. Registry authentication uses the
built-in `GITHUB_TOKEN`; signing uses GitHub OIDC, not a private-key secret.
Before signing, `podman login --compat-auth-file` writes credentials to
`~/.docker/config.json` for cosign and attestation tooling. This compatibility
file does not require Docker.
