
#!/usr/bin/env bash

set -u

usage() {
  cat >&2 <<'EOF'
Usage:
  check-multiarch.sh docker  linux/amd64 linux/arm64
  check-multiarch.sh podman  linux/amd64 linux/arm64

Behavior:
  - If the first argument is "docker":
      * exits 0 if Docker + buildx are installed and all requested platforms are supported
      * otherwise prints instructions and exits 14
  - If the first argument is "podman":
      * exits 0 if Podman is installed and all requested platforms are supported
      * otherwise prints instructions and exits 1
EOF
}

docker_instructions() {
  cat >&2 <<'EOF'
Docker multi-arch support is missing or incomplete.

Install / configure the following:

1. Install Docker Engine
   Fedora / RHEL example:
     sudo dnf -y install dnf-plugins-core
     sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
     sudo dnf install -y docker-ce docker-ce-cli containerd.io
     sudo systemctl enable --now docker

2. Verify buildx is available
     docker buildx version

3. Install & register QEMU binfmt handlers
     docker run --rm --privileged tonistiigi/binfmt --install all

4. Create or select a buildx builder
     docker buildx create --name multi-builder --driver docker-container --use 2>/dev/null || docker buildx use multi-builder

5. Verify supported platforms
     docker buildx inspect --bootstrap

EOF
}

podman_instructions() {
  cat >&2 <<'EOF'
Podman multi-arch support is missing or incomplete.

Install / configure the following:

1. Install Podman
   Fedora / RHEL example:
     sudo dnf install -y podman

2. Install & register QEMU binfmt handlers
     podman run --rm --privileged tonistiigi/binfmt --install all

3. Verify registrations exist
     ls -1 /proc/sys/fs/binfmt_misc/
     # Look for entries such as:
     #   qemu-aarch64
     #   qemu-x86_64
     #   qemu-arm
     #   qemu-ppc64le
     #   qemu-s390x

EOF
}

normalize_arch() {
  case "$1" in
    linux/amd64|amd64|x86_64) echo "amd64" ;;
    linux/arm64|arm64|aarch64) echo "arm64" ;;
    linux/arm/v7|arm/v7|armhf) echo "arm/v7" ;;
    linux/arm/v6|arm/v6) echo "arm/v6" ;;
    linux/ppc64le|ppc64le) echo "ppc64le" ;;
    linux/s390x|s390x) echo "s390x" ;;
    linux/riscv64|riscv64) echo "riscv64" ;;
    *) echo "" ;;
  esac
}

normalize_platform() {
  case "$1" in
    linux/amd64|amd64|x86_64) echo "linux/amd64" ;;
    linux/arm64|arm64|aarch64) echo "linux/arm64" ;;
    linux/arm/v7|arm/v7|armhf) echo "linux/arm/v7" ;;
    linux/arm/v6|arm/v6) echo "linux/arm/v6" ;;
    linux/ppc64le|ppc64le) echo "linux/ppc64le" ;;
    linux/s390x|s390x) echo "linux/s390x" ;;
    linux/riscv64|riscv64) echo "linux/riscv64" ;;
    *) echo "" ;;
  esac
}

host_arch_to_normalized() {
  case "$1" in
    x86_64|amd64) echo "amd64" ;;
    aarch64|arm64) echo "arm64" ;;
    armv7l|armv7|armhf) echo "arm/v7" ;;
    armv6l|armv6) echo "arm/v6" ;;
    ppc64le) echo "ppc64le" ;;
    s390x) echo "s390x" ;;
    riscv64) echo "riscv64" ;;
    *) echo "" ;;
  esac
}

platform_to_binfmt() {
  case "$1" in
    linux/amd64)  echo "qemu-x86_64" ;;
    linux/arm64)  echo "qemu-aarch64" ;;
    linux/arm/v7|linux/arm/v6) echo "qemu-arm" ;;
    linux/ppc64le) echo "qemu-ppc64le" ;;
    linux/s390x) echo "qemu-s390x" ;;
    linux/riscv64) echo "qemu-riscv64" ;;
    *) echo "" ;;
  esac
}

binfmt_enabled() {
  local entry="$1"
  local path="/proc/sys/fs/binfmt_misc/${entry}"

  [[ -n "$entry" ]] || return 1
  [[ -f "$path" ]] || return 1

  grep -q '^enabled' "$path" 2>/dev/null
}

check_docker() {
  local requested=("$@")

  if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: docker is not installed or not in PATH." >&2
    docker_instructions
    exit 14
  fi

  if ! docker buildx version >/dev/null 2>&1; then
    echo "ERROR: docker buildx is not installed or not available." >&2
    docker_instructions
    exit 14
  fi

  local inspect_output
  if ! inspect_output="$(docker buildx inspect --bootstrap 2>/dev/null)"; then
    echo "ERROR: docker buildx exists, but no usable builder is configured." >&2
    docker_instructions
    exit 14
  fi

  local platforms_line
  platforms_line="$(printf '%s\n' "$inspect_output" | awk -F': ' '/Platforms:/ {print $2; exit}')"

  if [[ -z "$platforms_line" ]]; then
    echo "ERROR: could not determine supported platforms from docker buildx inspect output." >&2
    docker_instructions
    exit 14
  fi

  local missing=()
  local p np
  for p in "${requested[@]}"; do
    np="$(normalize_platform "$p")"
    if [[ -z "$np" ]]; then
      missing+=("$p")
      continue
    fi

    if ! printf '%s\n' "$platforms_line" | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -Fxq "$np"; then
      missing+=("$np")
    fi
  done

  if ((${#missing[@]} > 0)); then
    echo "ERROR: docker buildx does not support all requested platforms." >&2
    echo "Requested: ${requested[*]}" >&2
    echo "Supported: $platforms_line" >&2
    echo "Missing:   ${missing[*]}" >&2
    docker_instructions
    exit 14
  fi

  exit 0
}

check_podman() {
  local requested=("$@")

  if ! command -v podman >/dev/null 2>&1; then
    echo "ERROR: podman is not installed or not in PATH." >&2
    podman_instructions
    exit 1
  fi

  local host_arch_raw host_arch
  host_arch_raw="$(podman info --format '{{.Host.Arch}}' 2>/dev/null || uname -m)"
  host_arch="$(host_arch_to_normalized "$host_arch_raw")"

  local missing=()
  local p np req_arch binfmt_name
  for p in "${requested[@]}"; do
    np="$(normalize_platform "$p")"
    if [[ -z "$np" ]]; then
      missing+=("$p")
      continue
    fi

    req_arch="$(normalize_arch "$np")"

    # Native host arch is always considered supported.
    if [[ -n "$host_arch" && "$req_arch" == "$host_arch" ]]; then
      continue
    fi

    # Cross-arch support requires a matching enabled binfmt/QEMU registration.
    binfmt_name="$(platform_to_binfmt "$np")"
    if ! binfmt_enabled "$binfmt_name"; then
      missing+=("$np")
    fi
  done

  if ((${#missing[@]} > 0)); then
    echo "ERROR: podman does not support all requested platforms on this host." >&2
    echo "Requested: ${requested[*]}" >&2
    echo "Host arch:  ${host_arch:-unknown} (${host_arch_raw:-unknown})" >&2
    echo "Missing:    ${missing[*]}" >&2
    podman_instructions
    exit 1
  fi

  exit 0
}

main() {
  if (($# < 2)); then
    usage
    exit 2
  fi

  local engine="$1"
  shift

  case "$engine" in
    docker)
      check_docker "$@"
      ;;
    podman)
      check_podman "$@"
      ;;
    *)
      echo "ERROR: first argument must be either 'docker' or 'podman'." >&2
      usage
      exit 2
      ;;
  esac
}

main "$@"
