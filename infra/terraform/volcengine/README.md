# 火山引擎 Terraform 基础设施

## 目标

创建 Kubernetes 基础运行所需 IaaS：

1. VPC
2. 子网
3. 安全组
4. 1 台控制平面 ECS
5. N 台工作节点 ECS
6. 对应公网 EIP

## 使用方式

1. 准备变量文件

```bash
cp /Users/01411043/code/spatial-intelligence-data-factory/infra/terraform/volcengine/terraform.tfvars.example \
  /Users/01411043/code/spatial-intelligence-data-factory/infra/terraform/volcengine/terraform.tfvars
```

2. 设置凭据

```bash
export VOLCENGINE_ACCESS_KEY="<your_ak>"
export VOLCENGINE_SECRET_KEY="<your_sk>"
```

3. 执行

```bash
cd /Users/01411043/code/spatial-intelligence-data-factory/infra/terraform/volcengine
terraform init
terraform plan
terraform apply
```

## 关键变量

1. `zone_id`: 可用区，例如 `cn-beijing-a`
2. `image_id`: 镜像 ID（建议 Ubuntu 22.04）
3. `ssh_public_key`: SSH 公钥字符串（可使用 `file("~/.ssh/id_rsa.pub")`）
4. `worker_count`: 工作节点数量

## 销毁

```bash
cd /Users/01411043/code/spatial-intelligence-data-factory/infra/terraform/volcengine
terraform destroy
```
