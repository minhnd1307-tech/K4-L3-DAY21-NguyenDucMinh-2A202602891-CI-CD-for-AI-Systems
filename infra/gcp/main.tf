terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.0"
    }
  }
}

variable "project_id" {
  type    = string
  default = "project-cd10db9a-96d8-4227-8ab"
}

variable "ssh_public_key" {
  type        = string
  description = "Public deployment key for the income user; never pass a private key."
}

provider "google" {
  project = var.project_id
  region  = "us-central1"
  zone    = "us-central1-a"
}

resource "google_project_service" "lab" {
  for_each           = toset(["compute.googleapis.com", "storage.googleapis.com", "iam.googleapis.com", "iamcredentials.googleapis.com", "sts.googleapis.com"])
  service            = each.value
  disable_on_destroy = false
}

resource "google_storage_bucket" "lab" {
  name                        = "income-lab-2a202602891"
  location                    = "US-CENTRAL1"
  uniform_bucket_level_access = true
  force_destroy               = false
  depends_on                  = [google_project_service.lab]
}

resource "google_service_account" "lab" {
  account_id   = "income-lab-sa"
  display_name = "Income Lab SA"
  depends_on   = [google_project_service.lab]
}

resource "google_storage_bucket_iam_member" "lab" {
  bucket = google_storage_bucket.lab.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.lab.email}"
}

resource "google_compute_instance" "api" {
  name                      = "income-api"
  machine_type              = "e2-small"
  allow_stopping_for_update = true
  tags                      = ["income-api"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 10
      type  = "pd-balanced"
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  service_account {
    email  = google_service_account.lab.email
    scopes = ["https://www.googleapis.com/auth/devstorage.read_only"]
  }

  metadata = {
    ssh-keys = "income:${trimspace(var.ssh_public_key)}"
  }

  depends_on = [google_project_service.lab]
}

resource "google_compute_firewall" "api" {
  name          = "allow-income-api"
  network       = "default"
  target_tags   = ["income-api"]
  source_ranges = ["0.0.0.0/0"]

  allow {
    protocol = "tcp"
    ports    = ["8080"]
  }

  depends_on = [google_project_service.lab]
}

output "artifact_bucket" {
  value = google_storage_bucket.lab.name
}

output "server_host" {
  value = google_compute_instance.api.network_interface[0].access_config[0].nat_ip
}

output "server_user" {
  value = "income"
}

output "service_account_email" {
  value = google_service_account.lab.email
}
