import json
from test_v44 import Store
import character
import unittest

class AvatarMigrationTests(unittest.TestCase):
    def test_legacy_backup_recreation_and_roundtrip(self):
        store=Store()
        self.addCleanup(store.close)
        legacy=json.dumps({'hair':'bob','gender':'female'})
        with store.connect() as db:
            character.schema(db)
            db.execute('INSERT INTO game_characters(owner,appearance) VALUES(?,?)',('account:1',legacy))
        model=character.overview(store,1)
        self.assertTrue(model['needs_recreation'])
        self.assertFalse(model['created'])
        self.assertEqual(model['appearance'],character.DEFAULT)
        new={**character.DEFAULT,'gender':'female','clothing':'tee','nose':'broad'}
        character.save(store,'account:1',1,{'appearance':new})
        model=character.overview(store,1)
        self.assertEqual(model['appearance'],new)
        self.assertEqual(model['version'],2)
        self.assertFalse(model['needs_recreation'])
        with store.connect() as db:
            character.schema(db)
            self.assertEqual(db.execute('SELECT appearance FROM avatar_legacy_backup').fetchone()[0],legacy)
            self.assertEqual(db.execute('SELECT appearance FROM game_characters').fetchone()[0],legacy)
            self.assertEqual(db.execute('SELECT count(*) FROM profiles').fetchone()[0],2)
        self.assertTrue(character.overview(store,2)['needs_recreation'])
