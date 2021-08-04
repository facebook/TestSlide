# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

set -o errexit
set -o nounset
set -o pipefail


homedir=$(dirname "${BASH_SOURCE}")/..
validatorDir="${homedir}/tests/copyright_check"
validator="${validatorDir}/copyright_validator.py"

defective_files=($(${validator} --rootdir=${homedir}))

if [[ ${#defective_files[@]} -gt 0 ]]; then
  for file in "${defective_files[@]}"; do
    echo "Copyright structure missing or incorrect for: ${file##*../}"
  done

  exit 1
fi
