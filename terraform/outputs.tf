output "app_hostname" {
  description = "Public hostname for the deployed Fly app"
  value       = "${fly_app.service.name}.fly.dev"
}

output "app_url" {
  description = "Public URL for the deployed Fly app"
  value       = "https://${fly_app.service.name}.fly.dev"
}
