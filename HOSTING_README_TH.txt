45 Fitness Coach — โฮสต์ถาวรและการค้นหา Google

สถานะชุดนี้: เตรียมโค้ดให้แล้ว ยังไม่ได้ซื้อโดเมน เช่าโฮสต์ หรือเผยแพร่เว็บจริง
Start-AlwaysOn.ps1 ช่วยรันบนคอม แต่เมื่อคอมปิด/Sleep/เน็ตขาด เว็บก็เข้าไม่ได้
Quick Tunnel เดิมสำหรับทดสอบ ไม่มีลิงก์ถาวรหรือการรับประกัน uptime

แนวทางติดตั้งถาวรสำหรับผู้ดูแล
1. ใช้เครื่องเซิร์ฟเวอร์ที่รองรับ Python 3.11 / Docker พร้อมพื้นที่ข้อมูลถาวร และโดเมน HTTPS
2. ใช้ ZIP เต็ม FitnessFormCoach_Python.zip ซึ่งมี models อยู่แล้ว
3. คัดลอกฐานข้อมูลเดิมและข้อมูลที่จำเป็นจาก data อย่างระมัดระวังหลังหยุดเซิร์ฟเวอร์เดิม
   ถ้าฐานข้อมูลว่าง สมาชิก ยศ เหรียญ และสลิปเดิมจะไม่ตามไปด้วย
4. สร้าง Docker image จากโฟลเดอร์โปรเจกต์:
   docker build -t fitness-coach .
5. สร้าง volume และรัน ตัวอย่างนี้ต้องแทน fitness.example.com ด้วยโดเมนที่คุณเป็นเจ้าของ:
   docker volume create fitness-data
   docker run -d --name fitness-coach --restart unless-stopped -p 127.0.0.1:5000:5000 -v fitness-data:/data -e FITNESS_PUBLIC_URL=https://fitness.example.com fitness-coach
6. ตั้ง reverse proxy ที่รองรับ HTTPS ให้ส่ง Host ของโดเมนเดิมไป 127.0.0.1:5000
   แอปยอมรับ Origin ตรง FITNESS_PUBLIC_URL และใช้ cookie แบบ Secure สำหรับโดเมนนั้น
7. ถ้าต้องกำหนดแอดมินหลังย้ายฐานข้อมูล ให้รันในเครื่องผู้ดูแล:
   docker exec fitness-coach python manage_admin.py --email admin@example.com
   บัญชีต้องมีอยู่แล้ว คำสั่งนี้ไม่เปิด endpoint ให้คนทั่วไปตั้งตนเองเป็นแอดมิน
8. ใช้ serve.py / Waitress แบบหนึ่ง process มีหลาย threads เซสชันกล้องเก็บใน process
   อย่าเพิ่ม worker/process/replica โดยไม่ย้าย session state และฐานข้อมูลให้รองรับก่อน
9. สำรอง /data เป็นประจำ ตั้ง SMTP/SlipOK เป็น environment secrets ถ้าต้องการบริการจริง
   ไฟล์ vip-services.secure.json บน Windows เข้ารหัสผูกผู้ใช้ Windows จึงใช้ตรง ๆ บน Linux ไม่ได้

ค้นหา Google
- โหมด FITNESS_PUBLIC_URL เปิดหน้าแรกสาธารณะ พร้อม meta description, robots.txt, sitemap.xml
- เปิด https://โดเมนของคุณ/45-fitness-coach เพื่อตรวจใช้งาน HTTPS และกล้อง
- ยืนยันความเป็นเจ้าของโดเมนใน Google Search Console แล้วส่ง /sitemap.xml
- Google เป็นผู้ตัดสินใจรวบรวมและจัดอันดับ ไม่รับประกันว่าจะค้นเจอทันทีหรือขึ้นอันดับแรก
- API บัญชี หลังบ้าน สุขภาพ สลิป และโปรไฟล์ส่วนตัวไม่เปิดให้ค้นหา

อ้างอิงเอกสารทางการ
https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/
https://docs.pylonsproject.org/projects/waitress/en/latest/
https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl
