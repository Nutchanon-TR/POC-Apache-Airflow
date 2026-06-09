# Questions

Q: ทำไม `create_mock_file_task = PythonOperator(...)` ถึงยังไม่สร้างไฟล์ทันที?
A: เพราะตอน Airflow parse DAG จะสร้างแค่ task definition ก่อน ไฟล์จะถูกสร้างจริงตอน DAG Run ทำงาน

Q: ทำไมต้องเขียน `create_mock_file_task >> should_trigger_ct2 >> trigger_ct2_dag_task`?
A: เพราะ `>>` ใช้กำหนดลำดับ task ให้สร้างไฟล์ก่อน แล้วค่อยเช็กว่าจะ trigger CT2 หรือไม่

Q: params อ่านจากตรงไหน?
A: callable ของ `PythonOperator` รับ Airflow context ผ่าน `**context` แล้วอ่านจาก `context["params"]`

Q: ข้อมูลจาก task ก่อนหน้าส่งต่ออย่างไร?
A: function ที่อยู่ใน `PythonOperator` return ค่าเข้า XCom แล้ว task ถัดไปอ่านด้วย `context["ti"].xcom_pull(task_ids="...")`

Q: CT1 trigger CT2 ตรงไหน?
A: ตรง `requests.post()` ใน `trigger_ct2_dag()` ที่ยิงไป `/api/v1/dags/ct2_pipeline/dagRuns`

Q: CT1 ใช้ Azure Key Vault อยู่ไหม?
A: ไม่ใช้ใน Docker version; `trigger_ct2_dag()` อ่าน CT2 API URL, user, password จาก environment variables

Q: `trigger` parameter ใช้ทำอะไร?
A: ใช้บอกว่าเมื่อสร้างไฟล์เสร็จแล้วจะ trigger CT2 ต่อ หรือหยุดแค่ CT1

Q: context คืออะไร ทำไมต้องมี?
A: Airflow inject ข้อมูลการรัน task เข้ามาให้อัตโนมัติ เช่น params, ti, ds

Q: ["params"] ต้องเป็นคำนี้เพราะอะไร?
A: Airflow กำหนดตายตัว เปลี่ยนไม่ได้ แต่ key ข้างใน เช่น "context", "trigger" เราตั้งเองได้

Q: ** ใน **context คืออะไร?
A: กระจาย dict เป็น keyword args (ส่ง) หรือรวม keyword args กลับเป็น dict (รับ) เหมือน ...spread ใน JS

Q: Airflow รู้ได้ยังไงว่าต้องส่ง params ไปให้ function ไหน?
A: ไม่ได้ match ชื่อเลย ส่ง context ก้อนเดิมให้ทุก function เสมอ แต่ละ function หยิบเองว่าจะใช้อะไร

Q: return ค่าออกจาก function แทน xcom_push ได้มั้ย?
A: ได้ Airflow push เข้า XCom ให้อัตโนมัติ ต่างกันแค่ตอนดึงออกไม่ต้องระบุ key

Q: ti มาจากไหน หมายถึงอะไร?
A: Airflow ใส่เข้า context ให้อัตโนมัติ ย่อจาก TaskInstance คือ object แทน "การรันครั้งนี้" โดยเฉพาะ

Q: dag_conf ทำไร?
A: ดึง config JSON ที่ส่งมาตอน trigger DAG ออกมาใช้

Q: CT2 ได้ไฟล์จาก CT1 ยังไงใน Docker version?
A: CT1 เขียนไฟล์ลง shared Docker volume แล้ว CT2 copy ไฟล์จาก path ที่รับใน `dag_run.conf`

Q: context มาจากไหน ในเมื่อเราไม่ได้กำหนด parameter?
A: Airflow inject ให้อัตโนมัติตอนรัน PythonOperator

Q: **context รับค่าอะไรมา?
A: รับ dict ที่ Airflow เตรียมไว้ให้ มี dag_run, ti, ds ฯลฯ ให้ใช้ได้เลย
