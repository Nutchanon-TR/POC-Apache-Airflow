# K8sTesting — Airflow บน AKS + KubernetesPodOperator (Terraform up/down)

โฟลเดอร์นี้แสดง **ท่ายอดนิยมของ Airflow (pattern 1–6)** ด้วย `KubernetesPodOperator`
รันบน **AKS (Azure)** โดยใช้ **Terraform** เป็นตัว provision ขึ้น/ลบทั้งก้อน เพื่อคุม credit

> Logic ตั้งใจให้ง่าย: job ปริ้น `HelloA` / `HelloB` และ job วางไฟล์ `Hello.txt` ลง Blob storage

---

## โครงสร้าง

```
K8sTesting/
├── terraform/              # provision RG + AKS + storage + Airflow + auto-stop
│   ├── main.tf             # resource group ใหม่ + random suffix
│   ├── aks.tf              # AKS 1 node (Free control plane)
│   ├── storage.tf          # storage account + container hello-demo
│   ├── airflow.tf          # Airflow Helm (LocalExecutor) + Secret + RBAC
│   ├── airflow-values.yaml.tpl
│   ├── autostop.tf         # Automation Account -> stop AKS หลัง 4 ชม.
│   ├── stop-aks.ps1.tpl    # runbook ที่สั่ง az aks stop ผ่าน REST
│   ├── variables.tf / outputs.tf / versions.tf
│   └── terraform.tfvars.example
├── dags/                   # git-sync จาก repo public มาที่ Airflow
│   ├── common/cluster_aware_kpo.py   # ClusterAwareKPO + factory print/upload pod
│   ├── 00_hello_basic_dag.py         # พื้นฐาน: HelloA -> HelloB -> upload (sequential)
│   ├── 01_parallel_hello_dag.py      # #1 Parallel
│   ├── 02_dynamic_mapping_hello_dag.py # #2 Dynamic Task Mapping (.expand)
│   ├── 03_taskgroup_hello_dag.py     # #3 TaskGroup
│   ├── 04_branch_hello_dag.py        # #4 @task.branch
│   ├── 05_trigger_downstream_dag.py  # #5 TriggerDagRunOperator
│   └── 06_wasb_sensor_hello_dag.py   # #6 WasbBlobSensor (รอไฟล์ตกใน blob)
├── up.ps1                  # terraform apply + โชว์คำสั่ง connect
└── down.ps1                # terraform destroy
```

> **dag_id = ชื่อไฟล์ตัวหน้า** เช่นไฟล์ `06_wasb_sensor_hello_dag.py` -> dag_id `06_wasb_sensor_hello`
> เห็นใน UI ปุ๊บรู้เลยว่ามาจากไฟล์ไหน

---

## วิธีใช้

### ขึ้น (provision)
```powershell
cd K8sTesting
.\up.ps1
# หรือ: cd terraform; terraform init; terraform apply
```
ใช้เวลา ~8–12 นาที (สร้าง AKS + ติดตั้ง Airflow + git-sync DAG)

### เข้า Airflow UI
```powershell
az aks get-credentials --resource-group k8s-airflow-poc-rg --name k8s-airflow-poc-aks --overwrite-existing
kubectl -n airflow port-forward svc/airflow-webserver 8080:8080
# เปิด http://localhost:8080  (login: admin / admin)
```

### ลบทิ้ง (กลับเป็น $0)
```powershell
.\down.ps1     # terraform destroy
```

---

## คุม Credit

| กลไก | ทำอะไร | ค่าใช้จ่าย |
|------|--------|-----------|
| **Auto-stop 4 ชม.** (อัตโนมัติ) | Automation Account สั่ง `az aks stop` หลัง apply 4 ชม. กันลืมปิด — ยิงได้แม้ปิดเครื่อง | compute ≈ $0 |
| `az aks start ...` | เปิด cluster กลับมา (~1 นาที) | เริ่มคิดเงิน node อีกครั้ง |
| `terraform destroy` | ลบทั้ง RG (รวม storage + ไฟล์) | $0 จริง |

> ปรับชั่วโมง auto-stop ได้ที่ `auto_stop_hours` ใน `terraform.tfvars`
> control plane เป็น **Free tier = $0** จ่ายเฉพาะ node (`Standard_B2ms`) ตอนที่เปิดอยู่จริง

---

## สถาปัตยกรรม (ย่อ)

```
git repo (public, K8sTesting/dags)
        │  git-sync sidecar
        ▼
┌──────────────────────── AKS (namespace: airflow) ────────────────────────┐
│  Airflow (LocalExecutor)  ── scheduler รัน task เอง                        │
│      │  SA: airflow-kpo (RBAC สร้าง pod ได้)                               │
│      ▼  in_cluster=True                                                    │
│  KubernetesPodOperator -> spawn pod (busybox echo / azure-cli upload)      │
│                                   │                                        │
└───────────────────────────────────┼────────────────────────────────────────┘
                                     ▼  az storage blob upload / WasbBlobSensor
                          Azure Blob (container: hello-demo)
```

- **Executor:** LocalExecutor + Postgres (chart) — เบา เหมาะ POC/student sub
- **DAG delivery:** git-sync จาก repo public (แก้ DAG แล้ว push เห็นผลโดยไม่ rebuild image)
- **Azure provider** (`WasbBlobSensor`) ติดตั้งผ่าน `_PIP_ADDITIONAL_REQUIREMENTS` ตอน pod boot
- **Secret `azure-storage`** เก็บ connection string — ฉีดให้ scheduler (sensor) และ upload pod

---

## End-to-end ลองเล่น (DAG 05 -> 06)

1. เปิด DAG `06_wasb_sensor_hello` (จะรอ blob `hello/Hello.txt`)
2. trigger DAG `05_trigger_downstream` — มัน upload `Hello.txt` แล้วยิง trigger ไป 06
3. sensor ใน 06 เจอไฟล์ -> ทำ task ต่อ

> หมายเหตุ: Sensor คือ **Pull** (DAG ต้องเริ่มก่อนถึงจะ poll) ไม่ใช่ push จาก blob
> ถ้าอยากได้ push จริง (ไฟล์ตก blob แล้ว DAG เด้งเอง) ต้องตั้ง **Event Grid** ฝั่ง Azure ยิงเข้า Airflow REST API
