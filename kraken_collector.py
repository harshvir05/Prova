"""Explicit Kraken linear-perpetual USD dataset, independent of Binance history."""
import argparse
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import urllib.error
from collector import SYMBOLS, now_ms, save_batch, book_metrics
import json
import time
import urllib.parse
import urllib.request

BASE = 'https://futures.kraken.com/derivatives/api/v3'
MAPPING = {s: 'PF_'+('XBT' if s == 'BTCUSDT' else s[:-4])+'USD' for s in SYMBOLS}


def fetch(endpoint, params=None):
    if endpoint not in ('/instruments', '/orderbook'): raise ValueError('Public endpoints only')
    url = BASE+endpoint+'?'+urllib.parse.urlencode(params or {})
    # Metadata failure affects all12 markets: allow a longer, bounded recovery.
    # Book requests keep two attempts to bound work per run.
    attempts = 4 if endpoint == '/instruments' else 2
    for attempt in range(attempts):
        sent = now_ms()
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'Prova-market-research/2'})
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.load(response)
            return payload, sent, now_ms()
        except urllib.error.HTTPError as error:
            error.close()
            if error.code not in (429, 500, 502, 503, 504) or attempt == attempts-1:
                raise
            wait = (2, 5, 10)[attempt]
            retry_after = error.headers.get('Retry-After') if error.headers else None
            if retry_after:
                # Do not retry earlier than a server's numeric Retry-After.
                try:
                    requested = float(retry_after)
                except ValueError:
                    # An HTTP-date or unknown value: leave recovery to the next batch.
                    raise error
                if not 0 <= requested <= 10: raise error
                wait = max(wait, requested)
            print(json.dumps({'event': 'request_retry', 'endpoint': endpoint,
                              'http_status': error.code, 'failed_attempt': attempt+1,
                              'wait_seconds': wait}), flush=True)
            time.sleep(wait)
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt == attempts-1: raise
            wait = (2, 5, 10)[attempt]
            print(json.dumps({'event': 'request_retry', 'endpoint': endpoint,
                              'error_type': type(error).__name__, 'failed_attempt': attempt+1,
                              'wait_seconds': wait}), flush=True)
            time.sleep(wait)


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None: raise ValueError('Server time must have timezone')
    return int(parsed.timestamp()*1000)


def validate_instrument(instrument, research_symbol):
    if (instrument['symbol'] != MAPPING[research_symbol]
        or instrument.get('type') != 'flexible_futures'
        or instrument.get('quote') != 'USD'
        or instrument.get('base') != research_symbol[:-4]
        or not instrument.get('tradeable') or instrument.get('suspended', False)
        or Decimal(str(instrument.get('contractSize'))) != 1):
        raise ValueError('Unsupported or non-tradeable instrument, quote or contract unit')
    return {k: instrument[k] for k in ('symbol', 'type', 'base', 'quote', 'contractSize', 'tickSize', 'tradeable')}


def normalize(payload):
    if payload.get('result') != 'success': raise ValueError('Kraken response not successful')
    normalized = {}
    for side, reverse in (('bids', True), ('asks', False)):
        rows = payload['orderBook'][side]
        # REST ordering is not guaranteed; validate all levels before taking top100.
        converted = [(Decimal(str(p)), Decimal(str(q))) for p, q in rows]
        if any(not p.is_finite() or not q.is_finite() or p <= 0 or q <= 0 for p, q in converted):
            raise ValueError('Invalid book level')
        if len({p for p, _ in converted}) != len(converted): raise ValueError('Duplicate price level')
        converted.sort(key=lambda x: x[0], reverse=reverse)
        normalized[side] = [[str(p), str(q)] for p, q in converted[:100]]
    return normalized


def collect():
    try:
        instruments, sent, received = fetch('/instruments')
        if instruments.get('result') != 'success': raise ValueError('Instrument lookup failed')
        server = timestamp(instruments['serverTime'])
        offset = server-(sent+received)/2
        metadata = {r['symbol']: r for r in instruments['instruments']}
        clock = {'server_ms': server, 'sent_ms': sent, 'received_ms': received,
                 'offset_estimate_ms': offset, 'uncertainty_ms': (received-sent)/2, 'venue': 'kraken'}
    except Exception as error:
        return [{'symbol': s, 'venue': 'kraken', 'status': 'not_collected', 'reason': 'instrument_metadata_unavailable',
                 'http_status': error.code if isinstance(error, urllib.error.HTTPError) else None,
                 'error_type': type(error).__name__} for s in SYMBOLS], None
    records = []
    for research in SYMBOLS:
        record = {'symbol': research, 'symbol_role': 'research_watchlist_identifier_only',
                  'source_symbol': MAPPING[research], 'venue': 'kraken', 'market': 'linear_perpetual',
                  'quote_currency': 'USD', 'depth_limit_normalized': 100, 'book_update_ms': None}
        try:
            info = validate_instrument(metadata[MAPPING[research]], research)
            record['instrument'] = info
            payload, start, end = fetch('/orderbook', {'symbol': info['symbol']})
            record.update({'sent_ms': start, 'received_ms': end, 'latency_ms': end-start, 'raw': payload})
            normalized = normalize(payload)
            response_ms = timestamp(payload['serverTime'])
            response_age = end+offset-response_ms
            if response_age > 20_000 or response_age < -5000: raise ValueError('Stale or future server response time')
            record.update({'status': 'ok', 'server_response_ms': response_ms,
                           'estimated_response_age_ms': response_age, 'normalized_book': normalized,
                           'metrics': book_metrics(normalized, 'USD'),
                           'book_update_time_available': False})
        except Exception as error:
            record.update({'status': 'error', 'http_status': error.code if isinstance(error, urllib.error.HTTPError) else None,
                           'error_type': type(error).__name__, 'message': str(error)[:200]})
        records.append(record)
    return records, clock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('output'))
    args = parser.parse_args()
    records, clock = collect()
    result = save_batch(args.output, records, clock, schema_version=2)
    return 0 if result['complete'] else 1


if __name__ == '__main__': raise SystemExit(main())
