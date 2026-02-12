provider "volcengine" {
  region = var.region
}

data "volcengine_images" "ubuntu_2204" {
  # 通过 data source 自动筛选公共 Ubuntu 22.04 镜像，避免手工抄 image_id。
  os_type    = "Linux"
  visibility = "public"
  name_regex = length(trimspace(var.image_name_regex)) > 0 ? var.image_name_regex : null
  image_name = length(trimspace(var.image_name)) > 0 ? var.image_name : null
}

data "volcengine_ecs_available_resources" "instance_types" {
  # 查询指定可用区真实可售卖规格，避免 InstanceType.NotFound
  destination_resource = "InstanceType"
  zone_id              = var.zone_id
  instance_charge_type = "PostPaid"
}

locals {
  control_plane_name = "${var.name_prefix}-cp-01"
  worker_names       = [for i in range(var.worker_count) : format("%s-worker-%02d", var.name_prefix, i + 1)]
  selected_image_id  = length(trimspace(var.image_id)) > 0 ? var.image_id : data.volcengine_images.ubuntu_2204.images[0].image_id
  tags_kv            = [for k, v in var.tags : { key = k, value = v }]

  _zone_matches = [for z in data.volcengine_ecs_available_resources.instance_types.available_zones : z if z.zone_id == var.zone_id]
  _zone         = length(local._zone_matches) > 0 ? local._zone_matches[0] : data.volcengine_ecs_available_resources.instance_types.available_zones[0]
  _it_resources = [for r in local._zone.available_resources : r if r.type == "InstanceType"]
  _it_supported = length(local._it_resources) > 0 ? local._it_resources[0].supported_resources : []

  instance_type_ids = [for sr in local._it_supported : sr.value if sr.status == "Available"]
  auto_cp_type      = contains(local.instance_type_ids, "ecs.g4i.large") ? "ecs.g4i.large" : local.instance_type_ids[0]
  auto_worker_type  = contains(local.instance_type_ids, "ecs.g4i.2xlarge") ? "ecs.g4i.2xlarge" : local.instance_type_ids[0]

  selected_cp_instance_type     = length(trimspace(var.instance_type_control_plane)) > 0 ? var.instance_type_control_plane : local.auto_cp_type
  selected_worker_instance_type = length(trimspace(var.instance_type_worker)) > 0 ? var.instance_type_worker : local.auto_worker_type
}

resource "volcengine_vpc" "this" {
  vpc_name     = "${var.name_prefix}-vpc"
  cidr_block   = var.vpc_cidr
  project_name = var.project_name

  dynamic "tags" {
    for_each = local.tags_kv
    iterator = tag
    content {
      key   = tag.value.key
      value = tag.value.value
    }
  }
}

resource "volcengine_subnet" "this" {
  subnet_name = "${var.name_prefix}-subnet"
  cidr_block  = var.subnet_cidr
  zone_id     = var.zone_id
  vpc_id      = volcengine_vpc.this.id

  dynamic "tags" {
    for_each = local.tags_kv
    iterator = tag
    content {
      key   = tag.value.key
      value = tag.value.value
    }
  }
}

resource "volcengine_security_group" "k8s" {
  security_group_name = "${var.name_prefix}-k8s-sg"
  vpc_id              = volcengine_vpc.this.id
  project_name        = var.project_name

  dynamic "tags" {
    for_each = local.tags_kv
    iterator = tag
    content {
      key   = tag.value.key
      value = tag.value.value
    }
  }
}

resource "volcengine_security_group_rule" "ssh" {
  direction         = "ingress"
  security_group_id = volcengine_security_group.k8s.id
  protocol          = "tcp"
  port_start        = 22
  port_end          = 22
  cidr_ip           = var.ssh_allowed_cidr
}

resource "volcengine_security_group_rule" "k8s_api" {
  direction         = "ingress"
  security_group_id = volcengine_security_group.k8s.id
  protocol          = "tcp"
  port_start        = 6443
  port_end          = 6443
  cidr_ip           = "0.0.0.0/0"
}

resource "volcengine_security_group_rule" "k8s_internal" {
  direction         = "ingress"
  security_group_id = volcengine_security_group.k8s.id
  protocol          = "all"
  port_start        = -1
  port_end          = -1
  cidr_ip           = var.vpc_cidr
}

resource "volcengine_security_group_rule" "egress_all" {
  direction         = "egress"
  security_group_id = volcengine_security_group.k8s.id
  protocol          = "all"
  port_start        = -1
  port_end          = -1
  cidr_ip           = "0.0.0.0/0"
}

resource "volcengine_ecs_key_pair" "this" {
  key_pair_name = "${var.name_prefix}-keypair"
  public_key    = var.ssh_public_key
}

resource "volcengine_ecs_instance" "control_plane" {
  instance_name        = local.control_plane_name
  host_name            = local.control_plane_name
  image_id             = local.selected_image_id
  instance_type        = local.selected_cp_instance_type
  subnet_id            = volcengine_subnet.this.id
  security_group_ids   = [volcengine_security_group.k8s.id]
  key_pair_name        = volcengine_ecs_key_pair.this.key_pair_name
  instance_charge_type = "PostPaid"
  system_volume_type   = var.system_volume_type
  system_volume_size   = var.system_volume_size
  project_name         = var.project_name

  dynamic "tags" {
    for_each = local.tags_kv
    iterator = tag
    content {
      key   = tag.value.key
      value = tag.value.value
    }
  }
}

resource "volcengine_ecs_instance" "workers" {
  count                = var.worker_count
  instance_name        = local.worker_names[count.index]
  host_name            = local.worker_names[count.index]
  image_id             = local.selected_image_id
  instance_type        = local.selected_worker_instance_type
  subnet_id            = volcengine_subnet.this.id
  security_group_ids   = [volcengine_security_group.k8s.id]
  key_pair_name        = volcengine_ecs_key_pair.this.key_pair_name
  instance_charge_type = "PostPaid"
  system_volume_type   = var.system_volume_type
  system_volume_size   = var.system_volume_size
  project_name         = var.project_name

  dynamic "tags" {
    for_each = local.tags_kv
    iterator = tag
    content {
      key   = tag.value.key
      value = tag.value.value
    }
  }
}

resource "volcengine_eip_address" "control_plane" {
  count        = var.enable_eip ? 1 : 0
  billing_type = "PostPaidByTraffic"
  bandwidth    = var.internet_bandwidth_mbps
  project_name = var.project_name

  dynamic "tags" {
    for_each = local.tags_kv
    iterator = tag
    content {
      key   = tag.value.key
      value = tag.value.value
    }
  }
}

resource "volcengine_eip_associate" "control_plane" {
  count         = var.enable_eip ? 1 : 0
  allocation_id = volcengine_eip_address.control_plane[0].id
  instance_id   = volcengine_ecs_instance.control_plane.id
  instance_type = "EcsInstance"
}

resource "volcengine_eip_address" "workers" {
  count        = var.enable_eip ? var.worker_count : 0
  billing_type = "PostPaidByTraffic"
  bandwidth    = var.internet_bandwidth_mbps
  project_name = var.project_name

  dynamic "tags" {
    for_each = local.tags_kv
    iterator = tag
    content {
      key   = tag.value.key
      value = tag.value.value
    }
  }
}

resource "volcengine_eip_associate" "workers" {
  count         = var.enable_eip ? var.worker_count : 0
  allocation_id = volcengine_eip_address.workers[count.index].id
  instance_id   = volcengine_ecs_instance.workers[count.index].id
  instance_type = "EcsInstance"
}
