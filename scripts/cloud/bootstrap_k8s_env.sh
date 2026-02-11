#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ANSIBLE_DIR="$ROOT_DIR/infra/ansible"

if ! command -v ansible-playbook >/dev/null 2>&1; then
  echo "[ERROR] ansible-playbook 未安装。请先安装 Ansible。" >&2
  exit 1
fi

if [[ ! -f "$ANSIBLE_DIR/inventory.ini" ]]; then
  echo "[ERROR] 缺少 $ANSIBLE_DIR/inventory.ini" >&2
  echo "请先基于 inventory.example.ini 填写目标云主机信息。" >&2
  exit 1
fi

export ANSIBLE_CONFIG="$ANSIBLE_DIR/ansible.cfg"

echo "[1/3] 节点基础初始化"
ansible-playbook "$ANSIBLE_DIR/playbooks/00-prereq.yml"

echo "[2/3] 控制平面初始化"
ansible-playbook "$ANSIBLE_DIR/playbooks/01-control-plane.yml"

echo "[3/3] 工作节点加入"
ansible-playbook "$ANSIBLE_DIR/playbooks/02-workers.yml"

echo "[DONE] Kubernetes 集群基础安装完成。"
echo "可在控制平面节点执行: kubectl get nodes -o wide"
