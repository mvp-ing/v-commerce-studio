 
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "6.49.2"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.region
}
