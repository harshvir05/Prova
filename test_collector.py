import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
from collector import SYMBOLS, collect, metrics, save_batch


def sample():
    return {'E': 1000, 'T': 999, 'lastUpdateId': 7,
            'bids': [['99', '2'], ['98', '1']], 'asks': [['101', '1'], ['102', '1']]}


class TestCollector(unittest.TestCase):
    def test_mid_spread_and_truncated_band(self):
        r = metrics(sample())
        self.assertEqual(r['mid_price'], 100)
        self.assertEqual(r['spread_bps'], 200)
        self.assertIsNone(r['bands_bps']['5']['imbalance_observed'])

    def test_imbalance_notional_and_coverage(self):
        s = sample(); s['bids'] = [['99.99', '2'], ['99.5', '1']]; s['asks'] = [['100.01', '1'], ['100.5', '1']]
        r = metrics(s)['bands_bps']['5']
        self.assertTrue(r['band_complete'])
        self.assertAlmostEqual(r['imbalance_observed'], (199.98-100.01)/(199.98+100.01))
        s['bids'] = s['bids'][:1]
        self.assertFalse(metrics(s)['bands_bps']['5']['band_complete'])

    def test_reject_bad_book(self):
        for bids in ([['103', '1']], [['99', '0']], [['NaN', '2']], [['98', '1'], ['99', '1']]):
            s = sample(); s['bids'] = bids
            with self.assertRaises(ValueError): metrics(s)

    def test_invalid_exchange_time(self):
        s = sample(); s['T'] = 1001
        with self.assertRaises(ValueError): metrics(s)

    def test_block_is_not_an_exchange_fallback(self):
        error = urllib.error.HTTPError('https://fapi.binance.com', 451, 'blocked', {}, None)
        with patch('collector.fetch', side_effect=error) as fetch:
            records, clock = collect()
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(len(records), 12)
        self.assertTrue(all(r['http_status'] == 451 and r['status'] == 'not_collected' for r in records))

    def test_partial_data_and_raw_content_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            records = [{'symbol': s, 'status': 'ok' if i == 0 else 'error', 'raw': sample() if i == 0 else None} for i, s in enumerate(SYMBOLS)]
            stats = save_batch(Path(temp), records, None)
            self.assertFalse(stats['complete']); self.assertEqual(stats['valid'], 1)
            with gzip.open(Path(temp)/stats['file'], 'rt') as stream: stored = json.load(stream)
            self.assertEqual(stored['records'], records)


if __name__ == '__main__': unittest.main()
