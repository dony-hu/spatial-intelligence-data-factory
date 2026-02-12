variable "region" {
  description = "火山引擎地域，例如 cn-beijing"
  type        = string
  default     = "cn-beijing"
}

variable "zone_id" {
  description = "可用区，例如 cn-beijing-a"
  type        = string
}

variable "name_prefix" {
  description = "资源名称前缀"
  type        = string
  default     = "sidf"
}

variable "vpc_cidr" {
  description = "VPC 网段"
  type        = string
  default     = "10.10.0.0/16"
}

variable "subnet_cidr" {
  description = "子网网段"
  type        = string
  default     = "10.10.1.0/24"
}

variable "image_id" {
  description = "ECS 镜像 ID。建议留空并使用 image_name/name_regex 自动选择 Ubuntu 22.04 公共镜像。"
  type        = string
  default     = ""
}

variable "image_name" {
  description = "镜像名称过滤（可选）。例如 Ubuntu 22.04。"
  type        = string
  default     = ""
}

variable "image_name_regex" {
  description = "镜像名称正则过滤（可选）。优先级高于 image_name。"
  type        = string
  default     = "(?i)ubuntu.*22\\.04"
}

variable "instance_type_control_plane" {
  description = "控制平面实例规格"
  type        = string
  default     = ""
}

variable "instance_type_worker" {
  description = "工作节点实例规格"
  type        = string
  default     = ""
}

variable "worker_count" {
  description = "工作节点数量"
  type        = number
  default     = 2
}

variable "system_volume_type" {
  description = "系统盘类型"
  type        = string
  default     = "ESSD_PL0"
}

variable "system_volume_size" {
  description = "系统盘大小 GB"
  type        = number
  default     = 100
}

variable "internet_bandwidth_mbps" {
  description = "每台机器公网带宽（Mbps）"
  type        = number
  default     = 10
}

variable "enable_eip" {
  description = "是否创建并绑定 EIP（账户余额不足时建议先关闭，仅创建内网资源）"
  type        = bool
  default     = false
}

variable "ssh_allowed_cidr" {
  description = "允许 SSH 登录来源"
  type        = string
  default     = "0.0.0.0/0"
}

variable "ssh_public_key" {
  description = "ECS 登录公钥内容"
  type        = string
}

variable "project_name" {
  description = "火山引擎项目名"
  type        = string
  default     = "default"
}

variable "tags" {
  description = "资源标签"
  type        = map(string)
  default = {
    Project = "spatial-intelligence-data-factory"
    Managed = "terraform"
  }
}
