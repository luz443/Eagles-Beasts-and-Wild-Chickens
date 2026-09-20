"""Structured conditions survive the contract, storage, and dedup boundaries."""

import json
import tempfile
import unittest
from pathlib import Path

from rra.contracts.models import Archive, Library
from rra.contracts.validator import Validator
from rra.library.dedup import Deduplicator
from rra.library.store import LibraryStore
from rra.seed.generator import SeedGenerator
from rra.skills.condition_compare import ConditionCompareSkill

ROOT = Path(__file__).resolve().parents[1]


class TestConditions(unittest.TestCase):
    def setUp(self):
        self.raw = json.loads((ROOT / 'contracts/fixtures/valid_record.json').read_text(encoding='utf-8'))

    def test_structured_conditions_survive_store_roundtrip(self):
        self.raw['conditions'] = {'seq_len': '2048', 'hardware': 'RTX 4090（24G）'}
        self.raw['links'] = []
        self.raw['evidence_refs'] = []
        with tempfile.TemporaryDirectory() as directory:
            store = LibraryStore(Path(directory) / 'library.json')
            store.save(Library(version='0.1.0', records=[Archive.from_dict(self.raw)]))
            loaded = store.load().records[0].to_dict()
        self.assertEqual(self.raw['conditions'], loaded.get('conditions'))

    def test_missing_and_empty_conditions_keep_legacy_serialization(self):
        legacy = Archive.from_dict(self.raw).to_dict()
        self.assertNotIn('conditions', legacy)
        self.assertEqual(legacy, Archive.from_dict(dict(self.raw, conditions={})).to_dict())

    def test_validator_accepts_all_nine_dimensions_and_empty_object(self):
        conditions = dict(model='Llama-3-8B', seq_len='2048', batch='32', micro_batch='4',
                          precision='bf16', hardware='24G', dataset_version='v2',
                          stage='微调', framework='PyTorch')
        for value in (conditions, {}, {'model': ' '}):
            with self.subTest(value=value):
                self.assertEqual([], Validator().validate_archive(dict(self.raw, conditions=value)))

    def test_validator_reports_condition_type_key_and_value_paths(self):
        cases = [(None, 'conditions'), ([], 'conditions'), ('bad', 'conditions'),
                 ({'gpu': '4090'}, 'conditions.gpu'), ({'seq_len': ''}, 'conditions.seq_len'),
                 ({'seq_len': 2048}, 'conditions.seq_len'), ({'batch': None}, 'conditions.batch')]
        for value, path in cases:
            with self.subTest(value=value):
                violations = Validator().validate_archive(dict(self.raw, conditions=value))
                self.assertIn(path, [violation.path for violation in violations])

    def test_dedup_distinguishes_changed_conditions_and_ignores_order(self):
        dedup = Deduplicator()
        a = Archive.from_dict(dict(self.raw, conditions={'seq_len': '2048', 'precision': 'BF16'}))
        b = Archive.from_dict(dict(self.raw, conditions={'precision': ' bf16 ', 'seq_len': '2048'}))
        c = Archive.from_dict(dict(self.raw, conditions={'seq_len': '512', 'precision': 'bf16'}))
        self.assertEqual(dedup.key_of(a), dedup.key_of(b))
        self.assertNotEqual(dedup.key_of(a), dedup.key_of(c))
        legacy = dedup.key_of(Archive.from_dict(self.raw))
        self.assertEqual(legacy, dedup.key_of(Archive.from_dict(dict(self.raw, conditions={}))))
        self.assertEqual(legacy + '\x1f[["precision","bf16"],["seq_len","2048"]]', dedup.key_of(a))

    def test_condition_dedup_preserves_version_punctuation(self):
        dedup = Deduplicator()
        a = Archive.from_dict(dict(self.raw, conditions={'dataset_version': 'v1.10'}))
        b = Archive.from_dict(dict(self.raw, conditions={'dataset_version': 'v11.0'}))
        self.assertNotEqual(dedup.key_of(a), dedup.key_of(b))

    def test_condition_dedup_normalizes_width_case_and_repeated_spaces(self):
        dedup = Deduplicator()
        a = Archive.from_dict(dict(self.raw, conditions={'model': ' Ａ   V1.10 '}))
        b = Archive.from_dict(dict(self.raw, conditions={'model': 'a v1.10'}))
        c = Archive.from_dict(dict(self.raw, conditions={'model': 'av1.10'}))
        self.assertEqual(dedup.key_of(a), dedup.key_of(b))
        self.assertNotEqual(dedup.key_of(a), dedup.key_of(c))

    def test_seed_conditions_expose_multiscenario_comparison(self):
        records = {record['id']: record for record in SeedGenerator().generate()}
        self.assertEqual({'seq_len': '2048', 'batch': '32', 'hardware': 'RTX 4090（24G）',
                          'precision': 'bf16', 'stage': '微调'}, records['R-001'].get('conditions'))
        self.assertEqual('512（稳定） / 2048（OOM）', records['R-002'].get('conditions', {}).get('seq_len'))
        skill = ConditionCompareSkill()
        self.assertEqual(['seq_len', 'batch'], skill.differing_dims(records['R-001'], records['R-002']))
        self.assertEqual('条件不同', skill.verdict(records['R-001'], records['R-002']))
        self.assertNotIn('model', records['R-001']['conditions'])
        self.assertNotIn('conditions', records['R-014'])


if __name__ == '__main__':
    unittest.main()
