#!/bin/bash

# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

set -euxo pipefail

release_version=${1?"Usage: $0 <release_version>"}

git checkout master
git pull

echo $release_version > testslide/version
sed -i -e "s/Version .*/Version $release_version/" \
    util/testslide-snippets/README.md \
    util/testslide-snippets/CHANGELOG.md
sed -i -e "s/\"version\":.*/\"version\": \"$release_version\",/" util/testslide-snippets/package.json
git add testslide/version util/testslide-snippets
git commit -m "v$release_version"
git push

git tag $release_version
git push origin $release_version
