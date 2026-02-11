#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TF_DIR="$ROOT_DIR/infra/terraform/volcengine"
INV_FILE="$ROOT_DIR/infra/ansible/inventory.ini"

export PATH="$ROOT_DIR/tools/bin:$PATH"

SSH_KEY_PATH_DEFAULT="$ROOT_DIR/tools/keys/volcengine_ed25519"

cd "$TF_DIR"

cp_ip="$(terraform output -raw control_plane_public_ip)"
mapfile -t worker_ips < <(terraform output -json worker_public_ips | jq -r '.[]')

ssh_key_path="${SSH_KEY_PATH:-$SSH_KEY_PATH_DEFAULT}"

{
  echo "[k8s_control_plane]"
  echo "$cp_ip ansible_user=root ansible_ssh_private_key_file=$ssh_key_path"
  echo
  echo "[k8s_workers]"
  for ip in "${worker_ips[@]}"; do
    echo "$ip ansible_user=root ansible_ssh_private_key_file=$ssh_key_path"
  done
  echo
  echo "[k8s_all:children]"
  echo "k8s_control_plane"
  echo "k8s_workers"
} > "$INV_FILE"

echo "已生成 inventory: $INV_FILE"
