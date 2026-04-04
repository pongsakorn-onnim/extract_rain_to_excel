# 🌧️ Extract Rain to Excel (Forecast vs Normal 30y)

เครื่องมือ Automation สำหรับดึงข้อมูลฝนคาดการณ์ (Forecast) รายเดือน จากไฟล์ Raster (`.asc`) มาคำนวณค่าเฉลี่ยรายพื้นที่ (Zonal Statistics) เทียบกับค่าปกติ 30 ปี และส่งออกเป็นไฟล์ Excel

## 🚀 ฟีเจอร์หลัก (Features)
* **Multi-Model Support:** รองรับโมเดล HII และ OneMap (Mean, Upper, Lower)
* **Automated Extraction:** ดึงข้อมูลรายลุ่มน้ำ (Basin) และรายภาค (Region) พร้อมกันในรันเดียว
* **Anomaly Calculation:** คำนวณค่าต่างจากปกติ (Anomaly) และ % Anomaly ให้อัตโนมัติ
* **Geometry Auto-Fix:** มีระบบซ่อม Shapefile อัตโนมัติ (On-the-fly buffer fix) ด้วย `buffer(0)` เพื่อป้องกันโปรแกรมหยุดทำงาน
* **Excel Report:** รวมผลลัพธ์ทั้งหมดไว้ในไฟล์ Excel เดียว แยก Sheet (Basin/Region)

---

## 🛠️ การติดตั้ง (Installation)

### 1. Clone หรือดาวน์โหลดโปรเจค
นำไฟล์ทั้งหมดไปวางไว้ในเครื่องของคุณ

### 2. สร้าง Virtual Environment (แนะนำ)
```bash
python -m venv .venv
# สำหรับ Windows:
.venv\Scripts\activate
# สำหรับ Mac/Linux:
source .venv/bin/activate
```

### 3. สร้างไฟล์ requirements.txt
สร้างไฟล์ชื่อ `requirements.txt` ที่ Root Folder และวางเนื้อหานี้ลงไป:
```text
affine==2.4.0
attrs==25.4.0
certifi==2026.1.4
click==8.3.1
click-plugins==1.1.1.2
cligj==0.7.2
colorama==0.4.6
et_xmlfile==2.0.0
fiona==1.10.1
geopandas==1.1.2
numpy==2.4.1
openpyxl==3.1.5
packaging==26.0
pandas==3.0.0
pyogrio==0.12.1
pyparsing==3.3.2
pyproj==3.7.2
python-dateutil==2.9.0.post0
PyYAML==6.0.3
rasterio==1.5.0
rasterstats==0.20.0
shapely==2.1.2
simplejson==3.20.2
six==1.17.0
tzdata==2025.3
```

### 4. ติดตั้ง Dependencies
```bash
pip install -r requirements.txt
```

---

## ⚙️ การตั้งค่า (Configuration)

แก้ไข Path และค่าเริ่มต้นที่: `configs/config.yaml`

```yaml
run:
  init_month: "202602"  # เดือนเริ่มต้น (YYYYMM)
  leads: [0, 1, 2, 3, 4, 5]

paths:
  fcst_root: "D:/HII/..."
  normal30y_ascii_dir: "..."
  basin_shp: "..."
  region_shp: "..."
```

---

## ▶️ วิธีใช้งาน (Usage)

### 1. รันแบบปกติ (ใช้ค่าจาก Config)
```bash
python main.py
```

### 2. รันโดยระบุเดือนใหม่ (Override CLI)
```bash
python main.py --init 2026031
```

---

## 📂 ผลลัพธ์ (Output)

ไฟล์จะถูกสร้างที่: `outputs/extract/rain_summary_{YYYYMM}.xlsx`
* **Sheet "Basin":** สรุปรายลุ่มน้ำ (`MB_CODE`, `MBASIN_T`)
* **Sheet "Region":** สรุปรายภาค (`REG_CODE`, `FIRST_REGI`)

---

## 🏗️ โครงสร้างโปรเจค (Project Structure)

```text
extract_rain_to_excel/
├── configs/
│   └── config.yaml          # การตั้งค่า
├── src/
│   ├── core/
│   │   ├── raster_processor.py # Zonal Stats & Geo-fix
│   │   └── calculator.py       # Metrics calculation
│   ├── export/
│   │   └── excel_writer.py     # Excel export
│   └── utils/
│       └── config_loader.py    # YAML loader
├── main.py                     # Entry point
└── requirements.txt            # Dependencies
```

---

## 📝 Troubleshooting

* **Error: 'dict' object has no attribute 'to_excel'**: เช็ค `src/export/excel_writer.py` ว่ารองรับการเขียนหลาย Sheet หรือยัง
* **Invalid Geometry Warning**: โปรแกรมจะทำการ "Auto-fix" ด้วย `buffer(0)` ให้เองอัตโนมัติ
* **ภาษาไทยใน Excel**: ระบบใช้ `openpyxl` ซึ่งรองรับ UTF-8 หากเปิดใน Excel แล้วเพี้ยน ให้ตรวจสอบฟอนต์เครื่อง