"""Behavior checks for the downloadable standard-library example."""
import csv
import importlib.util
import math
import subprocess
import sys
import tempfile
from pathlib import Path

path = Path('examples/analysis.py')
assert path.exists(), 'downloadable analysis/backtest program is missing'
spec = importlib.util.spec_from_file_location('analysis', path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
rows = m.load_csv(Path('examples/net-values.csv'), 'analyze')
r = m.metrics([(row['date'], row['nav']) for row in rows])
assert math.isclose(r['return'], .1)
assert math.isclose(r['max_drawdown'], .25)
assert r['peak_date'] == '2023-01-01' and r['trough_date'] == '2024-01-01'
assert r['recovery_date'] is None
prices = m.load_csv(Path('examples/prices.csv'), 'backtest')
b = m.backtest(prices, fee=1)
assert math.isclose(b['ending_equity'], 195)
assert [row['trade'] for row in b['ledger']] == ['hold', 'hold', 'buy', 'sell']
assert [row['cash'] for row in b['ledger']] == [200, 200, 96, 195]
assert b['trades'] == 2 and b['fees'] == 2
assert b['ledger'][2]['signal_date'] == '2026-01-06'
assert b['benchmark_ending_equity'] == 198 and b['benchmark_liquidated_equity'] == 197
assert b['exposure'] == .25
assert m.backtest(prices, fee=0)['ending_equity'] == 197
assert m.backtest(prices, fee=2)['ending_equity'] == 193
assert m.backtest(prices, initial_cash=50)['trades'] == 0
assert m.metrics([(rows[0]['date'], 100), (rows[1]['date'], 100)])['max_drawdown'] == 0
assert m.metrics([(rows[0]['date'], 100), (rows[1]['date'], 90)])['max_drawdown'] == .1 or math.isclose(m.metrics([(rows[0]['date'], 100), (rows[1]['date'], 90)])['max_drawdown'], .1)
# Corporate actions must be checked on raw prices, never on adjusted NAV.
a = m.corporate_actions(m.load_csv(Path('examples/corporate-actions.csv'), 'actions'))
assert [row['shares'] for row in a] == [1, 2, 2]
assert [row['equity'] for row in a] == [100, 100, 100]
for text in ['date,nav,currency\n', 'date,nav,currency\n2022-01-01,0,CNY\n2023-01-01,100,CNY\n', 'date,nav,currency\n2022-01-01,nan,CNY\n2023-01-01,100,CNY\n', 'date,nav,currency\n2022-01-01,inf,CNY\n2023-01-01,100,CNY\n', 'date,nav,currency\n2022-01-01,100,CNY\n2022-01-01,110,CNY\n', 'date,nav,currency\n2023-01-01,100,CNY\n2022-01-01,110,CNY\n', 'date,nav,currency\nnot-a-date,100,CNY\n2023-01-01,110,CNY\n', 'date,nav,currency\n2022-01-01,,CNY\n2023-01-01,110,CNY\n', 'date,nav,currency\n2022-01-01,100,CNY\n2023-01-01,110,USD\n']:
 with tempfile.TemporaryDirectory() as folder:
  p = Path(folder)/'bad.csv'; p.write_text(text)
  try: m.load_csv(p, 'analyze')
  except ValueError: pass
  else: raise AssertionError(f'invalid CSV accepted: {text!r}')


def test_backtest_sale_fee_exceeds_available_cash():
    errors = []
    for sale_open in [.5, 1]:
        rows = [{'date': f'2026-01-0{i+5}', 'open': op, 'close': cl, 'currency': 'CNY'}
                for i, (op, cl) in enumerate([(1, 1), (1, 1.2), (1, 1.1), (sale_open, .5)])]
        try:
            m.backtest(rows, initial_cash=2, fee=1)
        except ValueError as error:
            errors.append(str(error))
        else:
            raise AssertionError('Sale must stop before fee leaves nonpositive cash')
    assert all('Backtest stopped on 2026-01-08' in error and 'sale fee' in error
               and 'positive NAV' in error and 'CSV' not in error for error in errors), errors
    rows[-1]['open'] = 1.01
    result = m.backtest(rows, initial_cash=2, fee=1)
    assert result['ledger'][-1]['trade'] == 'sell'
    assert math.isclose(result['ending_equity'], .01)
    assert all(row['cash'] >= 0 and row['equity'] > 0 for row in result['ledger'])


def test_cli_csv_parser_error():
    with tempfile.TemporaryDirectory() as folder:
        oversized = Path(folder) / 'oversized.csv'
        oversized.write_text('date,nav,currency\n2022-01-01,100,' + 'X' * (csv.field_size_limit() + 1) + '\n2023-01-01,110,CNY\n')
        result = subprocess.run([sys.executable, str(path), 'analyze', str(oversized)], capture_output=True, text=True)
        assert result.returncode == 2, result.stderr
        assert 'Input error:' in result.stderr and 'field larger than field limit' in result.stderr
        assert 'Traceback' not in result.stderr and not result.stdout


test_cli_csv_parser_error()
test_backtest_sale_fee_exceeds_available_cash()
print('metrics, next-open cash/position/fees/benchmark, corporate actions and invalid CSV: PASS')
