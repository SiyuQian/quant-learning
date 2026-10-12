#!/usr/bin/env python3
"""Synthetic single-asset teaching lab. Python 3.10+, standard library only.

No external cash flows, tax, live trading or actual market calendar.
Backtest: two-close signal, next-open fills, one unit, zero cash interest.
No borrowing; stop before an actual sale would leave nonpositive cash/NAV.
"""
import argparse
import csv
import json
import math
import sys
import tempfile
from datetime import date
from pathlib import Path

COLUMNS = {
    'analyze': ('nav',),
    'backtest': ('open', 'close'),
    'actions': ('raw_close', 'split_ratio', 'dividend'),
}


def validate_rows(rows, mode):
    if len(rows) < 2:
        raise ValueError('At least two dated rows are required.')
    previous = None
    currency = None
    for line, row in enumerate(rows, 2):
        try:
            day = date.fromisoformat(row['date'])
            if day.isoformat() != row['date']:
                raise ValueError('Use YYYY-MM-DD.')
            if previous is not None and day <= previous:
                raise ValueError('Dates must be unique and strictly increasing.')
            if not row['currency'] or (currency and row['currency'] != currency):
                raise ValueError('One nonempty currency is required; mixed currency is unsupported.')
            for key in COLUMNS[mode]:
                value = float(row[key])
                if not math.isfinite(value) or (value < 0 if key == 'dividend' else value <= 0):
                    raise ValueError(f'{key} must be finite and {"nonnegative" if key == "dividend" else "positive"}.')
                row[key] = value
            previous, currency = day, row['currency']
        except (ValueError, TypeError, KeyError) as error:
            raise ValueError(f'CSV line {line}: {error}') from error
    return rows


def load_csv(path, mode):
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        expected = {'date', 'currency', *COLUMNS[mode]}
        if not reader.fieldnames or len(reader.fieldnames) != len(expected) or set(reader.fieldnames) != expected:
            raise ValueError(f'Required columns: {", ".join(sorted(expected))}')
        rows = list(reader)
        if any(None in row for row in rows):
            raise ValueError('Unexpected extra field in CSV row.')
    return validate_rows(rows, mode)


def metrics(points):
    rows = validate_rows([{'date': day, 'nav': value, 'currency': 'unit'} for day, value in points], 'analyze')
    days = (date.fromisoformat(rows[-1]['date']) - date.fromisoformat(rows[0]['date'])).days
    peak = rows[0]['nav']
    peak_day = rows[0]['date']
    max_drawdown = 0.0
    worst_peak, worst_trough = peak_day, peak_day
    trough_index = 0
    longest = 0
    for index, row in enumerate(rows):
        value, day = row['nav'], row['date']
        if value >= peak:
            longest = max(longest, (date.fromisoformat(day) - date.fromisoformat(peak_day)).days if index and rows[index-1]['nav'] < peak else 0)
            peak, peak_day = value, day
        else:
            longest = max(longest, (date.fromisoformat(day) - date.fromisoformat(peak_day)).days)
        drawdown = 1 - value / peak
        if drawdown > max_drawdown:
            max_drawdown = drawdown
            worst_peak, worst_trough, trough_index = peak_day, day, index
    worst_peak_value = next(row['nav'] for row in rows if row['date'] == worst_peak)
    recovery = next((row['date'] for row in rows[trough_index+1:] if row['nav'] >= worst_peak_value), None) if max_drawdown else None
    recovery_or_end = recovery or rows[-1]['date']
    total_return = rows[-1]['nav'] / rows[0]['nav'] - 1
    return {
        'start': rows[0]['date'], 'end': rows[-1]['date'], 'days': days,
        'return': total_return,
        'cagr': (1 + total_return) ** (365.25 / days) - 1,
        'max_drawdown': max_drawdown, 'peak_date': worst_peak, 'trough_date': worst_trough,
        'recovery_date': recovery,
        'drawdown_days_to_recovery_or_end': (date.fromisoformat(recovery_or_end) - date.fromisoformat(worst_peak)).days if max_drawdown else 0,
        'longest_underwater_days': longest,
        'underwater_at_end': rows[-1]['nav'] < peak,
    }


def backtest(rows, initial_cash=200, fee=1):
    validate_rows(rows, 'backtest')
    if not math.isfinite(initial_cash) or initial_cash <= 0 or not math.isfinite(fee) or fee < 0:
        raise ValueError('Initial cash must be positive and fee nonnegative, both finite.')
    cash, shares, target = initial_cash, 0, 0
    ledger = []
    for index, row in enumerate(rows):
        trade, paid = 'hold', 0
        if target > shares:
            if cash >= row['open'] + fee:
                cash -= row['open'] + fee
                shares, trade, paid = 1, 'buy', fee
            else:
                trade = 'rejected_cash'
        elif target < shares:
            sale_cash = cash + row['open'] - fee
            if sale_cash <= 0:
                raise ValueError(f'Backtest stopped on {row["date"]}: sale fee would leave nonpositive cash; no borrowing and positive NAV required.')
            cash = sale_cash
            shares, trade, paid = 0, 'sell', fee
        equity = cash + shares * row['close']
        next_target = int(index >= 1 and row['close'] > (rows[index-1]['close'] + row['close']) / 2)
        ledger.append({'date': row['date'], 'signal_date': rows[index-1]['date'] if index else None,
                       'executed_target': target, 'trade': trade, 'fee': paid,
                       'cash': cash, 'shares': shares, 'close': row['close'],
                       'equity': equity, 'next_target': next_target})
        target = next_target
    # Benchmark holds the same one unit, remaining money stays in cash at 0%.
    benchmark_shares = int(initial_cash >= rows[0]['open'] + fee)
    benchmark_cash = initial_cash - benchmark_shares * (rows[0]['open'] + fee)
    benchmark = benchmark_cash + benchmark_shares * rows[-1]['close']
    result = {'initial_cash': initial_cash, 'ending_equity': ledger[-1]['equity'],
              'return': ledger[-1]['equity'] / initial_cash - 1,
              'trades': sum(row['trade'] in ('buy', 'sell') for row in ledger),
              'fees': sum(row['fee'] for row in ledger),
              'exposure': sum(row['shares'] > 0 for row in ledger) / len(ledger),
              'benchmark_ending_equity': benchmark,
              'benchmark_liquidated_equity': benchmark - benchmark_shares * fee,
              'benchmark_return': benchmark / initial_cash - 1,
              'ledger': ledger}
    result['risk'] = metrics([(rows[0]['date'], initial_cash)] + [(row['date'], row['equity']) for row in ledger[1:]])
    result['assumptions'] = 'Synthetic prices; one unit; next-open execution; 0% cash return; fixed fee per buy/sell; no borrowing; stop before an actual sale leaves nonpositive cash/NAV; no spread/slippage/tax; final strategy holdings marked at close, no forced sale. Benchmark bought at first open, plus separate final liquidation value. Exposure is fraction of closing observations held.'
    return result


def corporate_actions(rows):
    validate_rows(rows, 'actions')
    if rows[0]['split_ratio'] != 1 or rows[0]['dividend'] != 0:
        raise ValueError('First row must establish pre-action holding: split_ratio=1, dividend=0.')
    shares, cash = 1.0, 0.0
    ledger = []
    for row in rows:
        shares *= row['split_ratio']
        cash += shares * row['dividend']
        ledger.append({'date': row['date'], 'shares': shares, 'cash': cash,
                       'equity': cash + shares * row['raw_close']})
    return ledger


def self_test():
    points = [('2022-01-01', 100), ('2023-01-01', 120), ('2024-01-01', 90), ('2025-01-01', 110)]
    result = metrics(points)
    assert math.isclose(result['return'], .1) and result['max_drawdown'] == .25
    assert result['recovery_date'] is None and result['longest_underwater_days'] == 731
    assert metrics([('2022-01-01', 100), ('2023-01-01', 100)])['max_drawdown'] == 0
    assert math.isclose(metrics([('2022-01-01', 100), ('2023-01-01', 90)])['max_drawdown'], .1)
    recovered = metrics(points + [('2026-01-01', 120)])
    assert recovered['recovery_date'] == '2026-01-01' and not recovered['underwater_at_end']
    rows = [{'date': f'2026-01-0{i+5}', 'open': op, 'close': cl, 'currency': 'CNY'} for i, (op, cl) in enumerate([(100,100),(101,102),(103,101),(100,99)])]
    b = backtest(rows)
    assert b['ending_equity'] == 195 and b['trades'] == 2 and b['fees'] == 2
    assert [r['trade'] for r in b['ledger']] == ['hold', 'hold', 'buy', 'sell']
    assert b['ledger'][2]['signal_date'] == rows[1]['date'] and b['ledger'][2]['cash'] == 96
    assert b['benchmark_ending_equity'] == 198 and b['benchmark_liquidated_equity'] == 197
    assert backtest(rows, fee=0)['ending_equity'] == 197
    assert backtest(rows, fee=2)['ending_equity'] == 193
    assert backtest(rows, initial_cash=50)['trades'] == 0
    a = corporate_actions([{'date':f'2026-01-0{i+5}', 'raw_close':price, 'split_ratio':split, 'dividend':div, 'currency':'CNY'} for i,(price,split,div) in enumerate([(100,1,0),(50,2,0),(49,1,1)])])
    assert [r['equity'] for r in a] == [100,100,100]
    bad_pairs = [[], [('2022-01-01',100)], [('2022-01-01',0),('2023-01-01',1)], [('2022-01-01',-1),('2023-01-01',1)], [('2022-01-01',float('nan')),('2023-01-01',1)], [('2022-01-01',float('inf')),('2023-01-01',1)], [('2022-01-01',100),('2022-01-01',110)], [('2023-01-01',100),('2022-01-01',110)], [('bad',100),('2023-01-01',110)]]
    for points in bad_pairs:
        try: metrics(points)
        except ValueError: pass
        else: raise AssertionError(f'Invalid points accepted: {points}')
    with tempfile.TemporaryDirectory() as folder:
        for text in ['date,nav,currency\n2022-01-01,,CNY\n2023-01-01,100,CNY\n', 'date,nav,currency\n2022-01-01,100,CNY\n2023-01-01,110,USD\n', 'date,value\n2022-01-01,100\n2023-01-01,110\n']:
            path = Path(folder) / 'bad.csv'; path.write_text(text)
            try: load_csv(path, 'analyze')
            except ValueError: pass
            else: raise AssertionError('Invalid CSV accepted')
    print('Self-test: metrics, recovery, next-open ledger, both fees, benchmark, actions and invalid inputs PASS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', nargs='?', choices=COLUMNS)
    parser.add_argument('csv_file', nargs='?', type=Path)
    parser.add_argument('--fee', type=float, default=1, help='Fixed fee per actual trade (backtest only).')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if not args.mode or not args.csv_file:
        parser.error('Supply mode and CSV file, or --self-test.')
    try:
        rows = load_csv(args.csv_file, args.mode)
        if args.mode == 'analyze':
            result = metrics([(row['date'], row['nav']) for row in rows])
            result.update(currency=rows[0]['currency'], assumptions='Synthetic total-return NAV; no external cash flows; CAGR uses elapsed days/365.25. No extra dividend/fee adjustment. Not a market forecast.')
        elif args.mode == 'backtest':
            result = backtest(rows, fee=args.fee)
        else:
            result = corporate_actions(rows)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, OSError, OverflowError, csv.Error) as error:
        print(f'Input error: {error}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
