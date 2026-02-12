#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOOLS_BIN="$ROOT_DIR/tools/bin"
VENV_DIR="$ROOT_DIR/tools/venv"

mkdir -p "$TOOLS_BIN" "$VENV_DIR"

install_terraform_darwin() {
  local version="1.7.5"
  local arch
  arch="$(uname -m)"

  case "$arch" in
    x86_64) arch="amd64";;
    arm64)  arch="arm64";;
    *)
      echo "[ERROR] 不支持的 macOS 架构: $arch" >&2
      exit 1
      ;;
  esac

  if [[ -x "$TOOLS_BIN/terraform" ]]; then
    echo "[OK] terraform 已存在: $TOOLS_BIN/terraform"
    return
  fi

  echo "[INFO] 安装 terraform $version (darwin_$arch) 到 $TOOLS_BIN"
  local url_primary="https://releases.hashicorp.com/terraform/${version}/terraform_${version}_darwin_${arch}.zip"
  local url_mirror_tuna="https://mirrors.tuna.tsinghua.edu.cn/hashicorp-releases/terraform/${version}/terraform_${version}_darwin_${arch}.zip"
  local tmp
  tmp="$(mktemp -d)"

  if ! curl -fL --connect-timeout 5 --max-time 180 --retry 3 --retry-delay 1 "$url_primary" -o "$tmp/terraform.zip"; then
    echo "[WARN] 从 HashiCorp 下载失败，尝试镜像源: TUNA" >&2
    curl -fL --connect-timeout 5 --max-time 180 --retry 3 --retry-delay 1 "$url_mirror_tuna" -o "$tmp/terraform.zip"
  fi

  unzip -q "$tmp/terraform.zip" -d "$tmp"
  install -m 0755 "$tmp/terraform" "$TOOLS_BIN/terraform"
  rm -rf "$tmp"
}

install_ansible_venv() {
  if [[ -x "$VENV_DIR/bin/ansible-playbook" ]]; then
    echo "[OK] ansible-playbook 已存在: $VENV_DIR/bin/ansible-playbook"
    return
  fi

  echo "[INFO] 创建 venv 并安装 ansible 到 $VENV_DIR"
  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/python" -m pip install --upgrade pip
  "$VENV_DIR/bin/python" -m pip install ansible
}

if [[ "$(uname -s)" == "Darwin" ]]; then
  command -v curl >/dev/null 2>&1 || { echo "[ERROR] 缺少 curl" >&2; exit 1; }
  command -v unzip >/dev/null 2>&1 || { echo "[ERROR] 缺少 unzip" >&2; exit 1; }
  install_terraform_darwin
  install_ansible_venv
  echo "[DONE] 本地依赖已安装。"
  echo "请确保运行脚本时 PATH 包含: $TOOLS_BIN 和 $VENV_DIR/bin（脚本已自动设置）。"
  exit 0
fi

echo "[ERROR] 当前脚本仅实现了 macOS(Darwin) 安装路径。" >&2
echo "Linux 环境请自行安装 terraform/ansible/jq 后再执行 provision 脚本。" >&2
exit 1
