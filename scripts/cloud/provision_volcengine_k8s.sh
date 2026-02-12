#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TF_DIR="$ROOT_DIR/infra/terraform/volcengine"

export PATH="$ROOT_DIR/tools/bin:$ROOT_DIR/tools/venv/bin:$PATH"

SSH_KEY_PATH_DEFAULT="$ROOT_DIR/tools/keys/volcengine_ed25519"

for cmd in terraform jq ansible-playbook; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[ERROR] 缺少命令: $cmd" >&2
    exit 1
  fi
done

if [[ -f "$TF_DIR/secrets.env" ]]; then
  # shellcheck disable=SC1090
  source "$TF_DIR/secrets.env"
fi

if [[ -z "${VOLCENGINE_ACCESS_KEY:-}" || -z "${VOLCENGINE_SECRET_KEY:-}" ]]; then
  echo "[ERROR] 请先设置 VOLCENGINE_ACCESS_KEY / VOLCENGINE_SECRET_KEY" >&2
  echo "你可以在 $TF_DIR/secrets.env 中设置（该文件已在 .gitignore 中忽略）。" >&2
  exit 1
fi

if [[ ! -f "$TF_DIR/terraform.tfvars" ]]; then
  echo "[ERROR] 缺少 $TF_DIR/terraform.tfvars" >&2
  echo "请先基于 terraform.tfvars.example 生成并填写。" >&2
  exit 1
fi

# Inject SSH public key via TF_VAR to avoid putting secrets/functions in tfvars.
if [[ -z "${TF_VAR_ssh_public_key:-}" ]]; then
  if [[ -f "${SSH_KEY_PATH:-$SSH_KEY_PATH_DEFAULT}.pub" ]]; then
    export TF_VAR_ssh_public_key
    TF_VAR_ssh_public_key="$(cat "${SSH_KEY_PATH:-$SSH_KEY_PATH_DEFAULT}.pub")"
  elif [[ -f "$HOME/.ssh/id_ed25519.pub" ]]; then
    export TF_VAR_ssh_public_key
    TF_VAR_ssh_public_key="$(cat "$HOME/.ssh/id_ed25519.pub")"
  elif [[ -f "$HOME/.ssh/id_rsa.pub" ]]; then
    export TF_VAR_ssh_public_key
    TF_VAR_ssh_public_key="$(cat "$HOME/.ssh/id_rsa.pub")"
  else
    echo "[ERROR] 未找到 SSH 公钥：$HOME/.ssh/id_ed25519.pub 或 $HOME/.ssh/id_rsa.pub" >&2
    echo "也未找到默认项目密钥：${SSH_KEY_PATH_DEFAULT}.pub" >&2
    exit 1
  fi
fi

cd "$TF_DIR"
terraform init
terraform plan -out tfplan
terraform apply -auto-approve tfplan

bash "$ROOT_DIR/scripts/cloud/render_inventory_from_tf.sh"

cp_ip="$(terraform output -raw control_plane_public_ip 2>/dev/null || true)"
if [[ -z "$cp_ip" || "$cp_ip" == "null" ]]; then
  echo "[WARN] 未创建 EIP（enable_eip=false 或账户余额不足）。已生成 inventory，但无法从公网 SSH 连接安装 K8s。" >&2
  echo "下一步：充值后将 terraform.tfvars 中 enable_eip 设置为 true，再重新执行该脚本即可继续安装。" >&2
  exit 0
fi

bash "$ROOT_DIR/scripts/cloud/bootstrap_k8s_env.sh"

echo "[DONE] 火山引擎主机创建与 K8s 基础安装完成。"
