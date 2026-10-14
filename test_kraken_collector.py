import unittest
from kraken_collector import MAPPING, normalize, timestamp, validate_instrument
from collector import book_metrics


class TestKrakenCollector(unittest.TestCase):
    def instrument(self):
        return {'symbol': 'PF_XBTUSD', 'type': 'flexible_futures', 'quote': 'USD',
                'base': 'BTC', 'contractSize': 1, 'tickSize': 1, 'tradeable': True}

    def test_mapping_and_actual_quote_are_distinct(self):
        self.assertEqual(len(MAPPING), 12)
        self.assertEqual(MAPPING['BTCUSDT'], 'PF_XBTUSD')
        self.assertEqual(validate_instrument(self.instrument(), 'BTCUSDT')['quote'], 'USD')

    def test_reject_wrong_units_suspended_quote_or_market(self):
        for key, value in [('contractSize', 10), ('quote', 'USDT'), ('type', 'inverse_futures'), ('suspended', True)]:
            info = self.instrument(); info[key] = value
            with self.assertRaises(ValueError): validate_instrument(info, 'BTCUSDT')

    def test_sort_then_top100_and_usd_metrics(self):
        p = {'result': 'success', 'orderBook': {'bids': [[98, 1], [99, 2]], 'asks': [[102, 1], [101, 1]]}}
        n = normalize(p)
        self.assertEqual(n['bids'][0], ['99', '2'])
        self.assertEqual(n['asks'][0], ['101', '1'])
        self.assertEqual(book_metrics(n, 'USD')['notional_currency'], 'USD')
        self.assertIn('bid_notional_usd_observed', book_metrics(n, 'USD')['bands_bps']['5'])

    def test_duplicate_or_invalid_price_rejected_before_truncation(self):
        for bids in ([[99, 1], [99, 2]], [[float('nan'), 1]], [[99, 0]]):
            with self.assertRaises(ValueError): normalize({'result': 'success', 'orderBook': {'bids': bids, 'asks': [[101, 1]]}})

    def test_timezone_required_and_ms_precision(self):
        self.assertEqual(timestamp('1970-01-01T00:00:01.234Z'), 1234)
        with self.assertRaises(ValueError): timestamp('2026-10-14T10:00:00')


if __name__ == '__main__': unittest.main()
