#!/bin/bash
set -euxo pipefail

USAGE="No release version specified. Please try again like this: $0 <release_version>"

release_version=${1?$USAGE}

git checkout master
git pull

echo $release_version > testslide/version
git add testslide/version
git commit -m "v$release_version"
git push

git tag $release_version
git push origin $release_version
