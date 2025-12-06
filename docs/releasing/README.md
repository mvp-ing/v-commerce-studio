# Releasing v-commerce

This document walks through the process of creating a new release of v-commerce.

## Prerequisites for tagging a release

1. Choose the logical next release tag, using [semantic versioning](https://semver.org/): `vX.Y.Z`.

   If this release includes significant feature changes, update the minor version (`Y`). Otherwise, for bug-fix releases or standard quarterly release, update the patch version `Z`).

2. Ensure that the following commands are in your `PATH`:

   - `gsed` (found in the `gnu-sed` Brew package for macOS, or by symlinking `sed` for Linux)
   - `helm`
   - `docker`

3. Make sure you are authenticated to your container registry:

   ```sh
   docker login <your-registry>
   ```

## Create and tag the new release

Run the `make-release.sh` script found inside the `docs/releasing/` directory:

```sh
# assuming you are inside the root path of the v-commerce repository
export TAG=vX.Y.Z # This is the new version (e.g. `v0.3.5`)
export REPO_PREFIX=<your-registry>/v-commerce # This is the Docker repository for tagged images
./docs/releasing/make-release.sh
```

This script does the following:

1. Uses `make-docker-images.sh` to build and push a Docker image for each microservice to the previously specified repository.
2. Uses `make-release-artifacts.sh` to regenerates (and update the image $TAGS) YAML file at `./release/kubernetes-manifests.yaml` and `./kustomize/base/`.
3. Runs `git tag` and pushes a new branch (e.g., `release/v0.3.5`) with the changes to `./release/kubernetes-manifests.yaml`.

You can then browse your container registry to make sure a Docker image was created for each microservice (with the new version tag).

## Create the PR

Now that the release branch has been created, you can find it in the list of branches and create a pull request targeting `main` (the default branch).

This process is going to trigger multiple CI checks as well as stage the release onto a temporary cluster. Once the PR has been approved and all checks are successfully passing, you can then merge the branch. Make sure to include the release draft (see next section) in the pull-request description for reviewers to see.

Once reviewed and you're ready to merge, make sure to not delete the release branch or the tags during that process.

## Add notes to the release

Once the PR has been fully merged, you are ready to create a new release for the newly created tag.

- Click the breadcrumbs on the row of the latest tag that was created in the tags page
- Select the `Create release` option

The release notes should contain a brief description of the changes since the previous release (like bug fixed and new features).

> **_Note:_** No assets need to be uploaded. They are picked up automatically from the tagged revision

## Deploy on a production environment

Once the release notes are published, you should then replace the version of the production environment to the newly published version.

1. Connect to your Kubernetes cluster:

   ```sh
   kubectl config use-context <your-cluster-context>
   ```

2. Deploy `release/kubernetes-manifests.yaml` to it:

   ```sh
   kubectl apply -f ./release/kubernetes-manifests.yaml
   ```

3. Verify the deployment:

   ```sh
   kubectl get pods
   kubectl get services
   ```

## Update major tags

1. Update the relevant major tag (for example, `v1`):

```sh
export MAJOR_TAG=v0 # Edit this as needed (to v1/v2/v3/etc)
git checkout release/${TAG}
git pull
git push --delete origin ${MAJOR_TAG} # Delete the remote tag (if it exists)
git tag --delete ${MAJOR_TAG} # Delete the local tag (if it exists)
git tag -a ${MAJOR_TAG} -m "Updating ${MAJOR_TAG} to its most recent release: ${TAG}"
git push origin ${MAJOR_TAG} # Push the new tag to origin
```

## Announce the new release

Once the new release is out, you can announce it via your preferred communication channels.
