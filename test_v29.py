"""Release completeness: all page entry points and original local theme assets."""
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET
import app as server

ROOT=Path(__file__).resolve().parent
class V29ReleaseTests(unittest.TestCase):
    def test_all_thirteen_pages_and_restored_modules_ship_together(self):
        with server.app.test_client() as client:
            html=client.get('/45-fitness-coach').get_data(as_text=True)
            for name in ['home','workout','calendar','leader','cardio','health','character','profile','vip','rewards','challenges','friends','admin']:
                self.assertIn(f'id="{name}Page"',html,name)
                self.assertIn(f'id="{name}Tab"',html,name)
            for name in ['v28.css','navigation-v28.js','character.js','character-renderer.js','rewards.js','vip.js','themes-v29.js','theme-icons-v29.css','themes-v29.css']:
                self.assertIn(f'/static/{name}?v=31',html)
            self.assertNotIn('/static/v27.css',html)
            self.assertIn('id="coachAudioEnabled"',html)
            self.assertIn('id="resetCamera"',html)
            self.assertEqual(server.GENTLE_COACH_VERSION,31)

    def test_all_original_theme_assets_are_local_valid_and_served(self):
        paths=list((ROOT/'static/images/themes').glob('*.svg'))
        self.assertEqual(len(paths),42)
        with server.app.test_client() as client:
            for path in paths:
                ET.fromstring(path.read_text())
                response=client.get('/'+str(path.relative_to(ROOT))+'?v=29')
                self.assertEqual(response.status_code,200,path.name)
                self.assertIn('must-revalidate',response.headers['Cache-Control'])
                response.close()
            css=''.join((ROOT/'static'/name).read_text() for name in ['theme-icons-v29.css','themes-v29.css'])
            for url in re.findall(r'url\([\'\"]?(/static/[^)\'\" ]+)',css):
                self.assertTrue(url.endswith('?v=29'),url)
                self.assertTrue((ROOT/url.lstrip('/').split('?')[0]).is_file(),url)

    def test_phone_qr_roundtrips_multiple_long_keys_with_uniform_modules(self):
        import base64, hashlib, cv2, numpy as np
        from unittest.mock import patch
        with server.app.test_client() as client, patch.object(server,'lan_addresses',return_value=['192.168.1.25']):
            for index in range(16):
                key=base64.urlsafe_b64encode(hashlib.sha256(f'v29-qr-{index}'.encode()).digest()).decode().rstrip('=')
                with patch.object(server,'ACCESS_KEY',key):
                    expected=client.get('/connection').json['links'][0]['url']
                    response=client.get('/connection-qr/0')
                    image=cv2.imdecode(np.frombuffer(response.data,np.uint8),cv2.IMREAD_GRAYSCALE)
                    self.assertEqual(cv2.QRCodeDetector().detectAndDecode(image)[0],expected)
                    modules=cv2.QRCodeEncoder_create().encode(expected).shape[0]+16
                    self.assertEqual(image.shape[0] % modules,0)

    def test_qr_logo_and_model_are_in_complete_release(self):
        for name in ['static/images/store/payment-qr.png','static/images/45-team-logo.png','models/pose_landmarker_lite.task']:
            self.assertGreater((ROOT/name).stat().st_size,1000,name)
        with server.app.test_client() as client:
            for url in ['/static/images/store/payment-qr.png','/static/images/45-team-logo.png']:
                response=client.get(url)
                self.assertEqual(response.status_code,200)
                self.assertIn('must-revalidate',response.headers['Cache-Control'])
                response.close()

if __name__=='__main__':unittest.main()
