variable "region" {
  type    = string
  default = "us-east-1"
}

variable "github_token" {
  type      = string
  sensitive = true
}

variable "github_owner" {
  type = string
}

variable "github_repo" {
  type = string
}

variable "sprites_token" {
  type      = string
  sensitive = true
}

variable "secret_code" {
  type      = string
  sensitive = true
  default   = "super-secret-textractor-code"
}
