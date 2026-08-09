import os
import tempfile
import unittest

import app as webapp


class AuthStoreTests(unittest.TestCase):
    def test_hash_and_verify_password(self):
        auth_store = webapp.AuthStore(path=None)
        password_hash = auth_store._hash_password('super-secret')
        self.assertTrue(auth_store._verify_password('super-secret', password_hash))
        self.assertFalse(auth_store._verify_password('wrong-password', password_hash))

    def test_create_and_authenticate_user(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = os.path.join(tmpdir, 'users.json')
            auth_store = webapp.AuthStore(path=store_path)
            auth_store.create_user('alice', 's3cr3t')
            self.assertIsNotNone(auth_store.authenticate('alice', 's3cr3t'))
            self.assertIsNone(auth_store.authenticate('alice', 'wrong'))
            self.assertIsNone(auth_store.authenticate('bob', 's3cr3t'))

    def test_session_token_roundtrip(self):
        token = webapp._make_session_token('alice', 'csrf-value')
        payload = webapp._parse_session_token(token)
        self.assertEqual(payload['username'], 'alice')
        self.assertEqual(payload['csrf_token'], 'csrf-value')


if __name__ == '__main__':
    unittest.main()
