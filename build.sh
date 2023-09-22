#!/usr/bin/env bash

# ./build.sh [component] [tag] [-r registry] [-u username] [-p password]
# leave registry empty if default registry [docker.io] used

set -e

# Initialize default values
REGISTRY=""
LOGIN=""
PASSWORD=""
COMPONENT=""
INPUT_TAG=""

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -r) REGISTRY="$2"; shift ;;
        -u) LOGIN="$2"; shift ;;
        -p) PASSWORD="$2"; shift ;;
        *)
            # Check if COMPONENT is empty
            if [[ -z "$COMPONENT" ]]; then
                COMPONENT="$1"
            else
                # If COMPONENT is already set, then set BUILD_TAG
                INPUT_TAG="$1"
            fi
            ;;
    esac
    shift
done


BUILD_TAG=${INPUT_TAG:-'build'}
FIND_CMD="find . -mindepth 2 -maxdepth 3 -print | grep Dockerfile | grep -vE '(test|.j2)'"
FIND_CMD="${FIND_CMD} | grep $COMPONENT/"

if [[ -n "${LOGIN}" && -n "${PASSWORD}" ]]; then
  echo "docker login"
  docker login ${REGISTRY} -u "${LOGIN}" -p "${PASSWORD}"
fi

push_image () {
   echo "Pushing $2"
    if [ -z $1]; then
      docker tag "$2:$3" "hystax/$2:$3"
      docker push "hystax/$2:$3"
    else
      docker tag "$2:$3" "$1/$2:$3"
      docker push "$1/$2:$3"
    fi
}

for DOCKERFILE in $(eval ${FIND_CMD} | xargs)
do
    COMPONENT=$(echo "${DOCKERFILE}" | awk -F '/' '{print $(NF-1)}')
    echo "Building image for ${COMPONENT}, build tag: ${BUILD_TAG}"
    docker build -t ${COMPONENT}:${BUILD_TAG} -f ${DOCKERFILE} .
    if [[ -n "${LOGIN}" && -n "${PASSWORD}" ]]; then
      push_image $REGISTRY $COMPONENT $BUILD_TAG
    fi
done
