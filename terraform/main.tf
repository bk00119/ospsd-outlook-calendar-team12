terraform {
  required_version = ">= 1.6.0"

  required_providers {
    fly = {
      source  = "fly-apps/fly"
      version = "0.0.23"
    }
  }
}

provider "fly" {
  fly_api_token    = var.fly_api_token
  useinternaltunnel = true
  internaltunnelorg = var.fly_org
  internaltunnelregion = var.fly_region
}

resource "fly_app" "service" {
  name = var.app_name
  org  = var.fly_org
}

resource "fly_ip" "ipv4" {
  app  = fly_app.service.name
  type = "v4"
}

resource "fly_ip" "ipv6" {
  app  = fly_app.service.name
  type = "v6"
}

resource "fly_machine" "service" {
  app    = fly_app.service.name
  region = var.fly_region
  name   = "${var.app_name}-machine"
  image  = var.image

  services = [
    {
      ports = [
        { port = 443, handlers = ["tls", "http"] },
        { port = 80, handlers = ["http"] }
      ]
      protocol      = "tcp"
      internal_port = 8000
    }
  ]

  env = {
    PORT = "8000"
  }

  cpus     = 1
  memorymb = 512
}
