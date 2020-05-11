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
git add testslide/version
git commit -m "v$release_version"
git push

git tag $release_version
git push origin $release_version
