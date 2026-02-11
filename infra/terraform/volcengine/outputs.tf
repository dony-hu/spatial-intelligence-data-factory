output "control_plane_public_ip" {
  value = var.enable_eip ? volcengine_eip_address.control_plane[0].eip_address : null
}

output "worker_public_ips" {
  value = var.enable_eip ? [for e in volcengine_eip_address.workers : e.eip_address] : []
}

output "control_plane_private_ip" {
  value = volcengine_ecs_instance.control_plane.primary_ip_address
}

output "worker_private_ips" {
  value = [for w in volcengine_ecs_instance.workers : w.primary_ip_address]
}

output "selected_image_id" {
  description = "最终用于创建 ECS 的镜像 ID（若 image_id 为空，则来自 data.volcengine_images）"
  value       = local.selected_image_id
}
