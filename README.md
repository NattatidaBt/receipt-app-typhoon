# การใช้เทคโนโลยี Optical Character Recognition (OCR) ร่วมกับ เทคโนโลยี Large Language Model (LLM) เพื่อการอ่านและสกัดข้อมูลจากใบเสร็จรับเงิน 📄

**Applying Optical Character Recognition (OCR) and Large Language Model (LLM) Technologies for Receipt Reading and Information Extraction**

ระบบเว็บแอปพลิเคชันต้นแบบ (Web Prototype) สำหรับการอ่านและสกัดข้อมูลสำคัญจากเอกสารใบเสร็จรับเงินและใบกำกับภาษีโดยอัตโนมัติ พัฒนาขึ้นภายใต้หลักสูตรวิศวกรรมคอมพิวเตอร์และปัญญาประดิษฐ์ มหาวิทยาลัยวลัยลักษณ์

## 🛠️ สถาปัตยกรรมระบบ (System Architecture)
ระบบทำงานในรูปแบบ **Single Process Pipeline** ไหลเป็นเส้นตรงเดี่ยวเพื่อประสิทธิภาพและความเสถียรสูงสุด:
1. **Image Preprocessing:** OpenCV (Deskewing แก้ภาพเอียงอัตโนมัติ + Method 4: Sharpening & Denoising เพื่อลดค่า CER)
2. **OCR Engine:** Typhoon OCR API (สกัดข้อความดิบรองรับภาษาผสม ไทย-อังกฤษ)
3. **Post-Processing & Correction:** Rule-based Correction (ล้างสระลอยและคำผิดภาษาไทยยอดนิยม)
4. **Information Extraction:** Typhoon LLM API (`typhoon-v2.5-30b-a3b-instruct`) ดึงข้อมูลเชิงความหมายให้อยู่ในโครงสร้างมาตรฐาน JSON object
5. **User Interface:** Streamlit Framework จัดวางโครงสร้างหน้าจอแบบแบ่งสองฝั่ง (Split-Screen Layout) แสดงภาพอ้างอิงและฟอร์มสำหรับตรวจสอบ/แก้ไขข้อมูลโดยมนุษย์ก่อนบันทึก

## 📂 โครงสร้างโฟลเดอร์โปรเจกต์ (Project Structure)
```text
receipt_app/
├── .streamlit/
│   └── secrets.toml        # ที่สำหรับเก็บ API Key ในเครื่องเครื่องคอมพิวเตอร์ (ห้ามอัปโหลดขึ้น GitHub)
├── .gitignore              # ระบุไฟล์/โฟลเดอร์ที่ Git จะละเว้นเพื่อความปลอดภัย
├── README.md               # เอกสารแนะนำและคู่มือโปรเจกต์ฉบับนี้
├── app.py                  # ไฟล์แอปพลิเคชันหลัก จัดการระบบ Web UI ทั้งหมด
├── ocr_engine.py           # โมดูลจัดการเตรียมภาพ (OpenCV) และเรียกใช้ Typhoon OCR API
└── llm_engine.py           # โมดูลล้างคำผิด (Rule-based) และเรียกใช้ Typhoon LLM API เพื่อจัดโครงสร้างข้อมูล