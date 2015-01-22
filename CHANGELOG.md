# Changelog

## v0.0.3
- Log level to debug #20
- Docker registry config options #20
- Failed/errored builds are cleaned, even when versioned #20
- Versioned images are pushed to registry #20
- Forms are validated for model integrity #21
- Added auto scroll button to build pages #22
- Auto scroll off by default #22

## v0.0.2
- Streaming console #16
- HipChat notifications #9
- Correctly tag images #13
- Any git tags acceptable, not just semver (though semver is special) #12
- Tagged builds not cleaned up #4
- Tagged builds will remove built image before replacing #12
- Version tags can not be built twice #12
- Version tag builds will never use cache #3
- Service provisioning #10
- Ability to use some Docker env vars as config #8

## v0.0.1
- YAML model
- Web UI to add jobs, builds, global config
- Auto-detect if running in Docker, guess Docker host
- Web UI to view builds
- Git clone, checkout
- Check for git version tag, save to build
- Build the Docker image
- Run the Docker image with the `ci` command
- Success/failed/errored/running/queued statuses
- Build output archive/download
- GitHub push hook
- Builds save committer/auther info
