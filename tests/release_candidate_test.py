"""Offline release gate tests: no authenticated calls, agent operations or target runs."""
import importlib.util, unittest
from pathlib import Path
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('release_candidate', Path(__file__).resolve().parents[1] / 'tools/release_candidate.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class PublicationGateTests(unittest.TestCase):
    def release(self, draft=True):
        return {'draft': draft, 'prerelease': True, 'tag_name': module.TAG,
                'assets': [{'name': name, 'id': index + 1, 'size': 1, 'state': 'uploaded'}
                           for index, name in enumerate(sorted(module.INITIAL))]}
    def test_public_release_cannot_enter_signing(self):
        with self.assertRaises(ValueError):
            module.assets_by_name(self.release(False), module.INITIAL, True)
    def test_signature_or_extra_asset_collision_is_not_clobbered(self):
        release = self.release()
        release['assets'].append({'name': 'SHA256SUMS.txt.sig', 'id': 99, 'size': 1, 'state': 'uploaded'})
        with self.assertRaises(ValueError):
            module.assets_by_name(release, module.INITIAL, True)
    def test_duplicate_json_fields_fail(self):
        with self.assertRaises(ValueError):
            module.json.loads('{"commit":"a","commit":"b"}', object_pairs_hook=module.unique_pairs)
    def test_missing_native_proof_fails(self):
        with self.assertRaises((ValueError, KeyError)):
            module.check_stage({'schema': 'project08-draft-stage-v1', 'repository': module.REPO,
                                'tag': module.TAG, 'commit': 'a'*40, 'sdk': '10.0.404',
                                'runtime': '10.0.15', 'reportSchema': 'fix-session-harness-report-v2',
                                'nativeProofs': {}, 'assets': {}})
    def test_mismatched_gate_never_publishes(self):
        github = Mock()
        verified = {'stage': {}, 'schema': 'wrong', 'fingerprint': module.FINGERPRINT}
        with self.assertRaises(ValueError):
            module.publish(verified, {}, Path('unused'), github)
        github.publish.assert_not_called()
        github.release.assert_not_called()
    def test_asset_size_and_identity_must_match(self):
        release = self.release()
        release['assets'][0]['size'] = 10**9
        with self.assertRaises(ValueError):
            module.assets_by_name(release, module.INITIAL, True)
    def test_path_traversal_is_not_an_asset_name(self):
        release = self.release()
        release['assets'][0]['name'] = '../SHA256SUMS.txt'
        with self.assertRaises(ValueError):
            module.assets_by_name(release, module.INITIAL, True)

if __name__ == '__main__':
    unittest.main()
