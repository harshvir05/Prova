"""Finite, public-market-only Binance USD-M order-book snapshot collector."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = 'https://fapi.binance.com'
SYMBOLS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT',
           'DOGEUSDT', 'AVAXUSDT', 'LINKUSDT', 'LTCUSDT', 'DOTUSDT', 'TRXUSDT')


def now_ms(): return time.time_ns()//1_000_000


def fetch(endpoint, params=None):
    if endpoint not in ('/fapi/v1/time', '/fapi/v1/depth'):
        raise ValueError('Only public time/depth endpoints are allowed')
    url = BASE+endpoint+'?'+urllib.parse.urlencode(params or {})
    for attempt in range(2):
        sent = now_ms()
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'Prova-market-research/1'})
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.load(response)
            return payload, sent, now_ms()
        except urllib.error.HTTPError as error:
            if error.code in (429, 500, 502, 503, 504) and attempt == 0:
                time.sleep(2); continue
            raise


def book_metrics(payload, quote_currency='USDT'):
    def levels(side, descending):
        rows = payload[side]
        if not rows or len(rows) > 100: raise ValueError('Invalid depth length')
        out = [(Decimal(p), Decimal(q)) for p, q in rows]
        if any(not p.is_finite() or not q.is_finite() or p <= 0 or q <= 0 for p, q in out):
            raise ValueError('Non-positive or non-finite level')
        prices = [p for p, _ in out]
        if any((a <= b if descending else a >= b) for a, b in zip(prices, prices[1:])):
            raise ValueError('Unsorted or duplicate prices')
        return out
    bids, asks = levels('bids', True), levels('asks', False)
    if bids[0][0] >= asks[0][0]: raise ValueError('Crossed or locked book')
    mid = (bids[0][0]+asks[0][0])/2
    bands = {}
    for bps in (5, 10, 25):
        width = Decimal(bps)/10000
        lower, upper = mid*(1-width), mid*(1+width)
        bid = sum(p*q for p, q in bids if p >= lower)
        ask = sum(p*q for p, q in asks if p <= upper)
        complete = bids[-1][0] <= lower and asks[-1][0] >= upper
        quote = quote_currency.lower()
        bands[str(bps)] = {f'bid_notional_{quote}_observed': float(bid), f'ask_notional_{quote}_observed': float(ask),
                           'imbalance_observed': float((bid-ask)/(bid+ask)) if bid+ask else None,
                           'band_complete': complete}
    return {'mid_price': float(mid), 'spread_bps': float((asks[0][0]-bids[0][0])/mid*10000),
            'notional_currency': quote_currency, 'bands_bps': bands}


def metrics(payload):
    result = book_metrics(payload)
    for key in ('E', 'T', 'lastUpdateId'):
        if not isinstance(payload[key], int) or isinstance(payload[key], bool) or payload[key] <= 0:
            raise ValueError('Invalid exchange timestamps or update ID')
    if payload['T'] > payload['E']: raise ValueError('Transaction after output time')
    return result


def collect():
    records = []
    try:
        clock, sent, received = fetch('/fapi/v1/time')
        server = clock['serverTime']
        if not isinstance(server, int) or isinstance(server, bool) or server <= 0:
            raise ValueError('Invalid server time')
        offset = server-(sent+received)/2
        clock_info = {'server_ms': server, 'sent_ms': sent, 'received_ms': received,
                      'offset_estimate_ms': offset, 'uncertainty_ms': (received-sent)/2}
    except Exception as error:
        status = error.code if isinstance(error, urllib.error.HTTPError) else None
        return [{'symbol': s, 'status': 'not_collected', 'reason': 'server_clock_unavailable',
                 'http_status': status, 'error_type': type(error).__name__} for s in SYMBOLS], None
    blocked = None
    for symbol in SYMBOLS:
        if blocked is not None:
            records.append({'symbol': symbol, 'status': 'not_collected', 'reason': 'endpoint_blocked', 'http_status': blocked})
            continue
        record = {'symbol': symbol, 'venue': 'binance', 'market': 'usd_m_perpetual', 'depth_limit': 100}
        payload = None
        try:
            payload, start, end = fetch('/fapi/v1/depth', {'symbol': symbol, 'limit': 100})
            record.update({'sent_ms': start, 'received_ms': end, 'latency_ms': end-start, 'raw': payload})
            values = metrics(payload)
            age = end+offset-payload['E']
            if not math.isfinite(age) or age > 20_000 or age < -5000:
                raise ValueError('Stale or future exchange output time')
            record.update({'status': 'ok', 'estimated_age_ms': age, 'metrics': values})
        except Exception as error:
            status = error.code if isinstance(error, urllib.error.HTTPError) else None
            if status in (403, 418, 451): blocked = status
            record.update({'status': 'error', 'http_status': status,
                           'error_type': type(error).__name__, 'message': str(error)[:200]})
        records.append(record)
    return records, clock_info


def save_batch(folder, records, clock, schema_version=1):
    folder.mkdir(parents=True, exist_ok=True)
    current = datetime.now(timezone.utc)
    run = os.environ.get('GITHUB_RUN_ID', 'local')
    attempt = os.environ.get('GITHUB_RUN_ATTEMPT', '1')
    stamp = current.strftime('%Y%m%dT%H%M%S%fZ')
    name = f'book-{stamp}-{run}-{attempt}.json.gz'
    payload = {'schema_version': schema_version, 'saved_utc': current.isoformat(), 'run_id': run, 'attempt': attempt,
               'source_commit': os.environ.get('GITHUB_SHA'), 'clock': clock,
               'snapshot_sampling': True, 'records': records}
    path = folder/name
    with path.open('xb') as target:
        with gzip.GzipFile(fileobj=target, mode='wb', mtime=0) as stream:
            stream.write(json.dumps(payload, allow_nan=False, separators=(',', ':')).encode())
    good = sum(r['status'] == 'ok' for r in records)
    stats = {'date_utc': current.strftime('%Y-%m-%d'), 'file': name, 'bytes': path.stat().st_size,
             'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'valid': good,
             'expected': len(SYMBOLS), 'complete': good == len(SYMBOLS)}
    (folder/'status.json').write_text(json.dumps(stats, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(stats), flush=True)
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('output'))
    args = parser.parse_args()
    records, clock = collect()
    stats = save_batch(args.output, records, clock)
    return 0 if stats['complete'] else 1


if __name__ == '__main__': raise SystemExit(main())
