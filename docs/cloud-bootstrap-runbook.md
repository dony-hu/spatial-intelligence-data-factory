# 云上环境搭建运行手册（专网可迁移基线）

## 1. 目标

基于基础 IaaS 能力搭建一套可在公有云与专网同构迁移的运行环境，最小可用范围：

1. 1 个 Kubernetes 控制平面节点
2. 2 个 Kubernetes 工作节点
3. 后续可部署 PostgreSQL、Redis、MinIO、Harbor、Prometheus/Grafana

## 2. 前置约束

1. 操作系统默认 `Ubuntu 22.04 LTS`
2. 所有节点可互通内网，放通以下端口：
- `22`（SSH）
- `6443`（K8s API Server）
- `2379-2380`（etcd）
- `10250`（kubelet）
- `30000-32767`（NodePort，若需要）
3. 运维机已安装 `terraform`、`ansible-playbook`、`jq`
4. 在 macOS 环境可通过以下脚本安装到仓库本地目录（不依赖 Homebrew）：

```bash
bash /Users/01411043/code/spatial-intelligence-data-factory/scripts/cloud/install_local_prereqs.sh
```

## 3. 建议规格（起步）

1. 控制平面：`4 vCPU / 8 GB RAM / 100 GB 系统盘`
2. 工作节点：`8 vCPU / 16 GB RAM / 200 GB 系统盘`（每台）
3. 专网迁移时保持同等或更高规格

## 4. 执行步骤（火山引擎）

1. 准备火山引擎凭据并导出环境变量：

```bash
export VOLCENGINE_ACCESS_KEY=\"<your_ak>\"
export VOLCENGINE_SECRET_KEY=\"<your_sk>\"
```

2. 基于样例生成 Terraform 变量文件并填写：

```bash
cp /Users/01411043/code/spatial-intelligence-data-factory/infra/terraform/volcengine/terraform.tfvars.example \
  /Users/01411043/code/spatial-intelligence-data-factory/infra/terraform/volcengine/terraform.tfvars
```

重点填写：`region`、`zone_id`、`image_id`、`ssh_public_key`。

3. 一键创建火山引擎基础设施并安装 K8s：

```bash
bash /Users/01411043/code/spatial-intelligence-data-factory/scripts/cloud/provision_volcengine_k8s.sh
```

该脚本会自动执行：
- Terraform 创建 VPC/子网/安全组/ECS/EIP
- 渲染 Ansible `inventory.ini`
- 执行 Ansible Playbook 初始化 Kubernetes

4. 在控制平面节点验证：

```bash
kubectl get nodes -o wide
kubectl get pods -A
```

## 5. 当前已交付文件

1. Ansible 配置：`/Users/01411043/code/spatial-intelligence-data-factory/infra/ansible/ansible.cfg`
2. 主机清单模板：`/Users/01411043/code/spatial-intelligence-data-factory/infra/ansible/inventory.example.ini`
3. 默认清单：`/Users/01411043/code/spatial-intelligence-data-factory/infra/ansible/inventory.ini`
4. 全局变量：`/Users/01411043/code/spatial-intelligence-data-factory/infra/ansible/group_vars/all.yml`
5. 基础初始化：`/Users/01411043/code/spatial-intelligence-data-factory/infra/ansible/playbooks/00-prereq.yml`
6. 控制平面安装：`/Users/01411043/code/spatial-intelligence-data-factory/infra/ansible/playbooks/01-control-plane.yml`
7. 工作节点加入：`/Users/01411043/code/spatial-intelligence-data-factory/infra/ansible/playbooks/02-workers.yml`
8. 一键入口脚本：`/Users/01411043/code/spatial-intelligence-data-factory/scripts/cloud/bootstrap_k8s_env.sh`
9. 火山引擎 Terraform：`/Users/01411043/code/spatial-intelligence-data-factory/infra/terraform/volcengine/`
10. Terraform 渲染 inventory：`/Users/01411043/code/spatial-intelligence-data-factory/scripts/cloud/render_inventory_from_tf.sh`
11. 火山引擎一键入口：`/Users/01411043/code/spatial-intelligence-data-factory/scripts/cloud/provision_volcengine_k8s.sh`
12. 本地依赖安装脚本：`/Users/01411043/code/spatial-intelligence-data-factory/scripts/cloud/install_local_prereqs.sh`

## 6. 下一阶段（建议顺序）

1. 部署 Harbor（制品仓库）
2. 部署 MinIO（对象存储）
3. 部署 PostgreSQL 与 Redis（基础数据服务）
4. 部署 Argo CD（GitOps 发布）
5. 部署 Prometheus + Grafana + Loki（可观测）
