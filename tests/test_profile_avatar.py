import unittest
from test_v44 import Store
import character

class ProfileAvatarTests(unittest.TestCase):
    def test_measurements_preserve_appearance_without_inferring_muscle(self):
        store=Store();self.addCleanup(store.close)
        appearance={**character.DEFAULT,'hair':'bob','eye_color':'#225588','clothing':'tee','build':.9}
        character.save(store,'account:1',1,{'appearance':appearance})
        fullness=[]
        for height,weight in [(175,58),(175,76),(175,105),(195,95)]:
            character.sync_dimensions(store,1,{'height_cm':height,'weight_kg':weight})
            model=character.overview(store,1,True)
            self.assertEqual(model['appearance'],appearance)
            self.assertEqual(model['visual']['muscle_definition'],.45)
            self.assertTrue(model['visual']['has_dimensions'])
            fullness.append(model['visual']['fullness'])
        self.assertLess(fullness[0],fullness[1]);self.assertLess(fullness[1],fullness[2])
    def test_missing_dimensions_use_default(self):
        store=Store();self.addCleanup(store.close)
        model=character.overview(store,2,True)
        self.assertFalse(model['visual']['has_dimensions'])
        self.assertEqual(model['visual']['height_scale'],1)
