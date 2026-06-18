variable "subscription_id" {
  type        = string
  description = "Azure subscription id to deploy into (Azure for Students)."
  default     = "59c0dcd7-abab-419f-808d-e6b1c11aa6ef"
}

variable "location" {
  type        = string
  description = "Azure region. Student-subscription policy only allows: malaysiawest, japanwest, centralindia, eastasia, japaneast."
  default     = "japaneast"
}

variable "resource_group_name" {
  type        = string
  description = "Brand-new resource group created for this POC (deleted on destroy)."
  default     = "k8s-airflow-poc-rg"
}

variable "prefix" {
  type        = string
  description = "Short prefix for resource names."
  default     = "k8sairflow"
}

variable "aks_name" {
  type        = string
  description = "AKS cluster name."
  default     = "k8s-airflow-poc-aks"
}

variable "node_size" {
  type        = string
  description = "VM size for the single AKS node. B2s_v2 = 2 vCPU / 8GB (allowed for student subs in japaneast)."
  default     = "Standard_B2s_v2"
}

variable "automation_location" {
  type        = string
  description = "Region for the Automation Account. Student subs can't host it in japaneast; japanwest is the only region allowed by BOTH the automation service and the deployment-region policy."
  default     = "japanwest"
}

variable "node_count" {
  type        = number
  description = "Number of AKS nodes."
  default     = 1
}

# ── DAG delivery (git-sync) ──────────────────────────────────────────────────
variable "git_repo_url" {
  type        = string
  description = "Public Git repo Airflow git-sync pulls DAGs from."
  default     = "https://github.com/Nutchanon-TR/POC-Apache-Airflow.git"
}

variable "git_branch" {
  type        = string
  default     = "main"
}

variable "git_subpath" {
  type        = string
  description = "Folder inside the repo that holds the DAGs."
  default     = "K8sTesting/dags"
}

# ── Auto-stop safety net ─────────────────────────────────────────────────────
variable "auto_stop_hours" {
  type        = number
  description = "Hours after apply before the cluster is auto-stopped (az aks stop) to save credit."
  default     = 4
}

variable "blob_container_name" {
  type        = string
  description = "Container used by the Hello-file job and WasbBlobSensor demo."
  default     = "hello-demo"
}

variable "airflow_chart_version" {
  type        = string
  description = "apache-airflow Helm chart version."
  default     = "1.15.0"
}
