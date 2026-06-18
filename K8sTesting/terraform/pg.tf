# Plain Postgres for Airflow metadata.
# The Airflow chart's bundled Bitnami Postgres image was removed from Docker Hub,
# so we run the official postgres:16 image instead and point Airflow at it
# (postgresql.enabled=false in values).
#
# Data lives on a PVC (managed disk) so it survives `az aks stop` / start and
# the 4h auto-stop — an emptyDir would be wiped on node deallocation.
resource "kubernetes_persistent_volume_claim" "pg" {
  metadata {
    name      = "airflow-pg-data"
    namespace = kubernetes_namespace.airflow.metadata[0].name
  }
  spec {
    access_modes = ["ReadWriteOnce"]
    resources {
      requests = {
        storage = "2Gi"
      }
    }
  }
  # Don't block on first-consumer binding (managed-csi binds when the pod mounts).
  wait_until_bound = false
}

resource "kubernetes_deployment" "pg" {
  metadata {
    name      = "airflow-pg"
    namespace = kubernetes_namespace.airflow.metadata[0].name
    labels    = { app = "airflow-pg" }
  }

  spec {
    replicas = 1
    strategy {
      type = "Recreate" # single RWO volume — never run two pods at once
    }
    selector {
      match_labels = { app = "airflow-pg" }
    }
    template {
      metadata {
        labels = { app = "airflow-pg" }
      }
      spec {
        container {
          name  = "postgres"
          image = "postgres:16"

          env {
            name  = "POSTGRES_USER"
            value = "airflow"
          }
          env {
            name  = "POSTGRES_PASSWORD"
            value = "airflow"
          }
          env {
            name  = "POSTGRES_DB"
            value = "airflow"
          }
          env {
            name  = "PGDATA"
            value = "/var/lib/postgresql/data/pgdata"
          }

          port {
            container_port = 5432
          }

          readiness_probe {
            exec {
              command = ["pg_isready", "-U", "airflow"]
            }
            initial_delay_seconds = 10
            period_seconds        = 5
          }

          volume_mount {
            name       = "data"
            mount_path = "/var/lib/postgresql/data"
          }
        }

        volume {
          name = "data"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim.pg.metadata[0].name
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "pg" {
  metadata {
    name      = "airflow-pg"
    namespace = kubernetes_namespace.airflow.metadata[0].name
  }
  spec {
    selector = { app = "airflow-pg" }
    port {
      port        = 5432
      target_port = 5432
    }
  }
}
