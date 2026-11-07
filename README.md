# FruitBlend24

วิเคราะห์ยอดขาย ราคา โปรโมชัน กำไรแต่ละครัว และแผนวัตถุดิบล่วงหน้า 3 เดือน ด้วย Python และ Streamlit

**เริ่มอ่าน:** [ผลวิเคราะห์และข้อเสนอ](REPORT.md) · [Notebook](analysis.ipynb)

## เปิดแอป

เปิด Terminal ในโฟลเดอร์โครงการ แล้วติดตั้งแพ็กเกจ:

```powershell
python -m pip install -r requirements.txt
```

เปิด Streamlit:

```powershell
python -m streamlit run app.py
```

มี CSV พร้อมใช้งานอยู่แล้ว จึงเปิดแอปได้ทันทีหลังติดตั้งแพ็กเกจ

## รันผลวิเคราะห์ใหม่

เปิด `analysis.ipynb` แล้วเลือก **Run All** เพื่อสร้างข้อมูลและผลวิเคราะห์ใหม่

- **เปลี่ยนข้อมูลต้นฉบับหรือวิธีคลีน:** Run All จากต้น Notebook
- **แก้เฉพาะการวิเคราะห์:** เมื่อมี `cleaned_data/` ครบแล้ว เริ่มรันจากหัวข้อ 2 ได้ แม้ Restart Kernel
- **ดูผลล่าสุดในแอป:** รัน Notebook ให้เสร็จ แล้วรีเฟรช Streamlit

### ลำดับข้อมูล

**Excel → คลีนใน Notebook → cleaned_data → วิเคราะห์ → app_data → Streamlit**

CSV บันทึกไว้ท้ายหัวข้อที่คำนวณตารางนั้น:

| หัวข้อ | ผลที่บันทึก |
|---|---|
| 1. Data quality | ข้อมูลคลีนใน cleaned_data และรายการตรวจย้อนหลัง |
| 2. Demand & pricing | ยอดขายรายชั่วโมง |
| 3. Promotions & rate codes | โปรและผลแยกแพลตฟอร์ม |
| 4. Portfolio & budget performance | P&L ครัว เมนู กะดึก และผลเทียบแถวซ้ำ |
| 5. Inventory & 3-month outlook | พยากรณ์ วัตถุดิบ ข้อมูลรอบพยากรณ์ และ stress test |

## ไฟล์ในโปรเจค

```text
.
├── README.md                         # วิธีเปิดงาน
├── REPORT.md                         # ผลวิเคราะห์และข้อเสนอ
├── analysis.ipynb                    # คลีนข้อมูลและคำนวณ
├── app.py                            # แอป Streamlit
├── requirements.txt                  # แพ็กเกจ Python
├── .gitignore
├── FruitBlend24_Case_Brief.docx       # โจทย์
├── FruitBlend24_Intern_Case_Data.xlsx # ข้อมูลต้นฉบับ
├── cleaned_data/                     # ข้อมูลพร้อมวิเคราะห์
│   └── review/                       # รายการสำหรับตรวจย้อนหลัง
├── app_data/                         # CSV ที่แอปใช้
└── .streamlit/
    └── config.toml                  # การตั้งค่าแอป
```

## ตารางสำหรับตรวจสอบ

| ประเด็น | ไฟล์ใน app_data |
|---|---|
| ผลของการตัดแถวซ้ำ | [duplicate_sensitivity.csv](app_data/duplicate_sensitivity.csv) |
| Stress test 18 กรณี | [scenario_sensitivity.csv](app_data/scenario_sensitivity.csv) |
| ผลแยกแพลตฟอร์ม | [platform_performance.csv](app_data/platform_performance.csv) |
| ข้อมูลกะดึก | [night_shift.csv](app_data/night_shift.csv) |

ใช้ Python, pandas, NumPy, openpyxl, Plotly และ Streamlit
เหตุผลของวิธีที่เลือก สมมติฐาน และข้อจำกัดอยู่ใน [REPORT.md](REPORT.md)
