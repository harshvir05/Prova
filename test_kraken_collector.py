import unittest
import io
import urllib.error
from unittest.mock import patch
from kraken_collector import MAPPING, normalize, timestamp, validate_instrument, fetch
from collector import book_metrics


class TestKrakenCollector(unittest.TestCase):
    def http_error(self, code=503, headers=None):
        error = urllib.error.HTTPError('https://futures.kraken.com', code, 'test error', headers or {}, None)
        self.addCleanup(error.close)
        return error

    def test_metadata_recovers_after_two_transient_errors(self):
        with patch('kraken_collector.urllib.request.urlopen', side_effect=[self.http_error(), self.http_error(), io.BytesIO(b'{"result":"success"}')]) as request, patch('kraken_collector.time.sleep') as sleep:
            payload, _, _ = fetch('/instruments')
        self.assertEqual(payload['result'], 'success')
        self.assertEqual(request.call_count, 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [2, 5])

    def test_metadata_failure_is_bounded_and_does_not_invent_data(self):
        with patch('kraken_collector.urllib.request.urlopen', side_effect=self.http_error()) as request, patch('kraken_collector.time.sleep') as sleep:
            with self.assertRaises(urllib.error.HTTPError): fetch('/instruments')
        self.assertEqual(request.call_count, 4)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [2, 5, 10])

    def test_permanent_errors_and_long_retry_after_are_not_retried(self):
        for error in (self.http_error(403), self.http_error(451), self.http_error(429, {'Retry-After': '60'})):
            with patch('kraken_collector.urllib.request.urlopen', side_effect=error) as request, patch('kraken_collector.time.sleep') as sleep:
                with self.assertRaises(urllib.error.HTTPError): fetch('/instruments')
            self.assertEqual(request.call_count, 1)
            sleep.assert_not_called()

    def test_book_network_retry_is_limited_and_metadata_obeys_retry_after(self):
        with patch('kraken_collector.urllib.request.urlopen', side_effect=TimeoutError()) as request, patch('kraken_collector.time.sleep'):
            with self.assertRaises(TimeoutError): fetch('/orderbook', {'symbol': 'PF_XBTUSD'})
        self.assertEqual(request.call_count, 2)
        with patch('kraken_collector.urllib.request.urlopen', side_effect=[self.http_error(503, {'Retry-After': '7'}), io.BytesIO(b'{"result":"success"}')]), patch('kraken_collector.time.sleep') as sleep:
            fetch('/instruments')
        sleep.assert_called_once_with(7)

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
