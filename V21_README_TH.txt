45 Fitness Coach v21
- ใส่โลโก้ทีมในหน้าหลัก เพิ่มสีการ์ดหมวดหมู่และกล้ามเนื้อ
- เพิ่มนักกล้ามการ์ตูนแบบ SVG ยกดัมเบลด้วย CSS (ภาพวาดใหม่แนวเดียวกับโลโก้ ไม่ใช่การขยับภาพบุคคลต้นฉบับ) ปิดการเคลื่อนไหวได้และรองรับ reduced motion
- โปรไฟล์ > วิเคราะห์พัฒนาการ: กราฟแท่งแนวตั้ง มุมเฉลี่ย/SD จุดกลับตัวรายเซตและรายวัน พร้อมคำแนะนำและ CSV ใช้ข้อมูลจริงเดิม ไม่มีข้อมูลจะแสดงว่าง
- ค่าเฉลี่ยมุมที่ลดลงไม่ได้แปลว่าดีขึ้นเสมอ เปรียบเทียบท่า ข้าง วิธีวัด น้ำหนักและตำแหน่งกล้องเดียวกัน SD วัดความสม่ำเสมอ ไม่ยืนยันกล้ามเนื้อโตหรือความถูกต้องทั้งหมด
- คง session-camera.js และ sessions.py เดิม ไม่ตั้งขีดจำกัดหยุดกล้องที่ 200 ครั้ง

ลิงก์ถาวร (ยังต้องตั้งบัญชีและโดเมนจริง)
1. มีโดเมนของคุณใน Cloudflare และเปิด Cloudflare One > Networks > Connectors > Cloudflare Tunnels (ชื่อเมนูอาจเปลี่ยน)
2. Create tunnel แบบ Cloudflared ตั้งชื่อ 45-fitness เลือก Windows แล้วใช้คำสั่งติดตั้ง connector ที่ Dashboard ให้ใน PowerShell Administrator เก็บ token ไว้กับตัว ไม่ส่งแชต
3. Published application: เลือกชื่อเช่น fitness บนโดเมนที่เป็นเจ้าของ Service HTTP localhost:5000 ไม่แก้ Host header เป็น localhost
4. หยุดเว็บและตัว Quick Tunnel เก่า ก่อนตั้งค่าต่อไปนี้ (เปลี่ยนโดเมนตัวอย่างเป็นของจริง):
   powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup-Permanent-Link.ps1 -PublicUrl "https://fitness.your-domain.com"
5. เปิดเว็บด้วย Start-AlwaysOn.ps1 หรือ Start-Configured.ps1 ลิงก์คือ https://โดเมนจริง/45-fitness-coach แล้วทดสอบมือถือผ่านเน็ตมือถือ
6. ต่อไปใช้ลิงก์นี้เดิม ไม่ต้องรัน Start-Share.ps1 ปิดคอมเว็บยังเข้าไม่ได้ หากต้องการทำงานเมื่อคอมปิดต้องย้าย Python และฐานข้อมูลไปโฮสต์ที่รันตลอด
7. อัปเดตโค้ด: หยุดเว็บ อัปเดต แล้วเปิดใหม่ ชื่อโดเมนและข้อมูลใน data คงเดิม
ย้อนกลับชั่วคราว: เปลี่ยนชื่อ data\public-site.json แล้วเปิด PowerShell ใหม่และรันเว็บ/Start-Share.ps1
คู่มือทางการ: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/
ไม่มีการซื้อโดเมน สร้างบัญชี หรือติดตั้ง connector บนเครื่องผู้ใช้โดยไฟล์อัปเดตนี้
