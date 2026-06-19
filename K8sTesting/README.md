# K8sTesting — Airflow บน Azure Container Instances (Terraform up/down)

> หมายเหตุชื่อโฟลเดอร์: เดิมเคยเป็น AKS/KubernetesPodOperator ตอนนี้เปลี่ยนเป็น
> **container ธรรมดาบน Azure (ACI)** + DAG แบบ **TaskFlow (`@task`)** แล้ว (ชื่อโฟลเดอร์คงเดิมไว้)

แสดงท่ายอดนิยมของ Airflow ด้วย **TaskFlow API** รันบน **Azure Container Instances**
โดยใช้ **Terraform** provision ขึ้น/ลบทั้งก้อนเพื่อคุม credit

---

## โครงสร้าง

```
K8sTesting/
├── terraform/
│   ├── main.tf            # resource group ใหม่ + random suffix
│   ├── storage.tf         # storage account + blob container + file share (อัป DAG)
│   ├── aci.tf             # container group: postgres + airflow (LocalExecutor), public IP
│   ├── autostop.tf        # Automation Account -> stop container หลัง 4 ชม.
│   ├── stop-aci.ps1.tpl   # runbook สั่ง az container stop ผ่าน REST
│   ├── variables.tf / outputs.tf / versions.tf
│   └── terraform.tfvars.example
├── dags/                  # อัปขึ้น Azure File Share แล้ว mount เข้า container
│   ├── 01_taskgroup_hello_dag.py        # TaskGroup
│   ├── 02_branch_hello_dag.py           # @task.branch: if A->B->C else X->Y->C
│   ├── 03_trigger_downstream_dag.py     # TriggerDagRunOperator -> 04
│   ├── 04_wasb_sensor_hello_dag.py      # WasbBlobSensor (รอไฟล์ตกใน blob)
│   └── 05_parallel_with_group_dag.py    # parallel tasks รันคู่กับ TaskGroup
├── up.ps1                 # terraform apply + โชว์ URL
└── down.ps1               # terraform destroy
```

> **dag_id = ชื่อไฟล์ตัวหน้า** เช่น `04_wasb_sensor_hello` มาจาก `04_wasb_sensor_hello_dag.py`

---

## วิธีใช้

### ขึ้น (provision)
```powershell
cd K8sTesting
.\up.ps1            # หรือ: cd terraform; terraform init; terraform apply
```
ใช้เวลา ~3-5 นาที (สร้าง container + boot Airflow + ติดตั้ง azure provider)

### เข้า Airflow UI
ดู URL จาก output `airflow_ui_url` (เช่น `http://airflowaciXXXXXX.japaneast.azurecontainer.io:8080`)
login: **admin / admin** — ไม่ต้อง port-forward เพราะ container มี public IP

### ลบทิ้ง (กลับเป็น $0)
```powershell
.\down.ps1          # terraform destroy
```

---

## คุม Credit

| กลไก | ทำอะไร | ค่าใช้จ่าย |
|------|--------|-----------|
| **Self-stop 4 ชม.** | sidecar `autostop` ในกลุ่ม sleep 4 ชม. แล้วสั่ง `az container stop` ตัวเอง ผ่าน managed identity (ยิงได้แม้ปิดเครื่อง) | container ที่ stop = $0 |
| `az container start ...` | เปิดกลับ (DB เริ่มใหม่ แต่ migrate อัตโนมัติตอน boot) — **และตั้งเวลา self-stop ใหม่อีก 4 ชม.** | เริ่มคิดเงินตอนรัน |
| `terraform destroy` | ลบทั้ง RG | $0 จริง |

> self-stop **รีเซ็ตทุกครั้งที่ start** (ต่างจาก Automation Account แบบครั้งเดียว) — เปิดกลับมาก็ได้ 4 ชม. ใหม่อัตโนมัติ

---

## สถาปัตยกรรม (ย่อ)

```
Azure File Share (dags) ──mount──┐
                                 ▼
┌──────── ACI container group (public IP :8080) ────────┐
│  airflow container (LocalExecutor)                     │
│    - scheduler + webserver                             │
│    - @task รันใน Airflow เลย (print / upload)          │
│    - azure provider ติดตั้งตอน boot (_PIP)             │
│        │ localhost:5432                                │
│  postgres container (ephemeral metadata DB)            │
└────────────────────────┼──────────────────────────────┘
                          ▼ azure-storage-blob / WasbBlobSensor
              Azure Blob (container: hello-demo)
```

- **ไม่มี Kubernetes / KubernetesPodOperator** แล้ว — task เป็น TaskFlow `@task` รันในตัว Airflow
- **DAG delivery:** Azure File Share (Terraform อัป `.py` ขึ้น share, mount เข้า `/opt/airflow/dags`)
- **postgres ephemeral:** boot ทุกครั้ง `airflow db migrate` + สร้าง admin ใหม่ (self-heal หลัง stop/start)

---

## End-to-end ลองเล่น (03 -> 04)

1. เปิด DAG `04_wasb_sensor_hello` (จะรอ blob `hello/Hello.txt`)
2. trigger `03_trigger_downstream` — upload `Hello.txt` แล้วยิง trigger ไป 04
3. sensor ใน 04 เจอไฟล์ -> ทำ task ต่อ

> Sensor = **Pull** (DAG ต้องเริ่มก่อนถึงจะ poll) ไม่ใช่ push จาก blob
> push จริง (ไฟล์ตก blob แล้ว DAG เด้งเอง) ต้องตั้ง Event Grid ฝั่ง Azure ยิงเข้า Airflow REST API
