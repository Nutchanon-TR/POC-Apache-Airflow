variable "subscription_id" {
  type        = string
  description = "Azure subscription id (Azure for Students)."
  default     = "59c0dcd7-abab-419f-808d-e6b1c11aa6ef"
}

variable "location" {
  type        = string
  description = "Azure region. Student policy allows: malaysiawest, japanwest, centralindia, eastasia, japaneast."
  default     = "japaneast"
}

variable "resource_group_name" {
  type        = string
  description = "Brand-new resource group for this POC (deleted on destroy)."
  default     = "airflow-aci-poc-rg"
}

variable "prefix" {
  type        = string
  description = "Short prefix for resource names (also the DNS label base)."
  default     = "airflowaci"
}

variable "airflow_image" {
  type        = string
  description = "Airflow container image."
  default     = "apache/airflow:2.9.3"
}

variable "blob_container_name" {
  type        = string
  description = "Container used by the upload task and WasbBlobSensor demo."
  default     = "hello-demo"
}

# ── Auto-stop safety net ─────────────────────────────────────────────────────
variable "auto_stop_hours" {
  type        = number
  description = "Hours the container group runs before self-stopping (sidecar) to save credit."
  default     = 4
}
