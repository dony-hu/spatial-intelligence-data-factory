# Ansible K8s Bootstrap

## 快速使用

1. 复制并编辑清单

```bash
cp /Users/01411043/code/spatial-intelligence-data-factory/infra/ansible/inventory.example.ini \
  /Users/01411043/code/spatial-intelligence-data-factory/infra/ansible/inventory.ini
```

2. 执行一键安装

```bash
bash /Users/01411043/code/spatial-intelligence-data-factory/scripts/cloud/bootstrap_k8s_env.sh
```

## 说明

1. 默认适配 Ubuntu/Debian 系统。
2. 默认 CNI 为 Calico。
3. Kubernetes 版本由 `group_vars/all.yml` 中 `kubernetes_version` 控制。
