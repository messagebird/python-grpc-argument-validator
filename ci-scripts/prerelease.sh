#!/bin/bash

set -e

export CURRENT_VERSION=$(git describe --tags --abbrev=0 --match="*dev*+${CI_COMMIT_BRANCH//-/.}*")

echo "Current tag ${CURRENT_VERSION}"

if [[ "${CURRENT_VERSION}" =~ ^([0-9]+\.[0-9]+\.[0-9]+)\.dev([0-9]+) ]]
then
  export NEW_VERSION=${BASH_REMATCH[1]}.dev$((BASH_REMATCH[2] + 1))+${CI_COMMIT_BRANCH//-/.}
else
  export NEW_VERSION=$(git describe --tags --abbrev=0).dev1+${CI_COMMIT_BRANCH//-/.}
fi

echo "Creating new tag ${NEW_VERSION}"

git tag ${NEW_VERSION}

poetry version ${NEW_VERSION}

poetry publish --build -r messagebird-python-packages -u "gitlab-ci-token" -p "${CI_JOB_TOKEN}"

git push --tags -o ci.skip
