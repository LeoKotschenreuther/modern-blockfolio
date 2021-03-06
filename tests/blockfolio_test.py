import coinmarketcap
import pytest
from pytest import approx

from .context import diversifiedblockfolio as diblo
from .test_utils import buys_equal, holdings_equal

buy_calls = []


@pytest.fixture(params=[
    [],
    [{}],
    [{'symbol': ''}],
])
def bad_asset_allocation(request):
    return request.param


@pytest.fixture(params=[0, -0.12, -5])
def bad_deposit(request):
    return request.param


@pytest.fixture
def asset_allocation():
    return [
        {'symbol': 'BTC'},
        {'symbol': 'ETH'},
        {'symbol': 'LTC'}
    ]


@pytest.fixture
def market():
    return coinmarketcap.Market()


def mock_buy(buy_symbol, give_symbol, give_amount):
    buy_calls.append((buy_symbol, give_symbol, give_amount))
    return


def mock_ticker(currency="", **kwargs):
    return [
        {'symbol': 'BTC', 'price_usd': '1000'},
        {'symbol': 'ETH', 'price_usd': '100'},
        {'symbol': 'LTC', 'price_usd': '10'}
    ]


class TestBlockfolio(object):

    def test_deposit_bad_input(self, asset_allocation, market, bad_deposit):
        blockfolio = diblo.Blockfolio(diblo.Exchange(), asset_allocation,
                                      market)
        with pytest.raises(ValueError):
            blockfolio.deposit(bad_deposit)

    @pytest.mark.parametrize(
        'fiat_exchange, asset_allocation, amount, buys', [
            # no preexisting holdings
            (
                diblo.Exchange({'holdings': [
                    {'symbol': 'USD', 'amount': 300}
                ]}),
                [{'symbol': 'BTC'}, {'symbol': 'ETH'}, {'symbol': 'LTC'}],
                300,
                [('BTC', 'USD', 100), ('ETH', 'USD', 100), ('LTC', 'USD', 100)]
            ),
            # preexisting holdings, all assets get bought
            (
                diblo.Exchange({'holdings': [
                    {'symbol': 'USD', 'amount': 300.01},
                    {'symbol': 'BTC', 'amount': .2},
                    {'symbol': 'ETH', 'amount': 2.4982},
                    {'symbol': 'LTC', 'amount': 10.43}
                ]}),
                [{'symbol': 'BTC'}, {'symbol': 'ETH'}, {'symbol': 'LTC'}],
                300.01,
                [
                    ('BTC', 'USD', 84.71),
                    ('ETH', 'USD', 34.89),
                    ('LTC', 'USD', 180.41)
                ]

            ),
            # preexisting holdings, not all assets get bought
            (
                diblo.Exchange({'holdings': [
                    {'symbol': 'USD', 'amount': 300.04},
                    {'symbol': 'BTC', 'amount': .8},
                    {'symbol': 'ETH', 'amount': 2.4982},
                    {'symbol': 'LTC', 'amount': 10.43}
                ]}),
                [{'symbol': 'BTC'}, {'symbol': 'ETH'}, {'symbol': 'LTC'}],
                300.04,
                [
                    ('ETH', 'USD', 77.26),
                    ('LTC', 'USD', 222.78)
                ]
            )
        ]
    )
    def test_deposit(self, fiat_exchange, asset_allocation, market, amount,
                     buys, monkeypatch):
        monkeypatch.setattr(market, 'ticker', mock_ticker)
        monkeypatch.setattr(fiat_exchange, 'buy', mock_buy)
        global buy_calls
        buy_calls = []
        blockfolio = diblo.Blockfolio(fiat_exchange, asset_allocation, market)
        blockfolio.deposit(amount)
        assert buys_equal(buy_calls, buys)

    def test_init_bad_asset_allocation(self, bad_asset_allocation, market):
        with pytest.raises(ValueError):
            diblo.Blockfolio(diblo.Exchange(), bad_asset_allocation, market)

    @pytest.mark.parametrize(
        'holdings, fiat_exchange', [
            (
                [{'symbol': 'BTC', 'amount': 0, 'price': 1000, 'value': 0},
                 {'symbol': 'ETH', 'amount': 0, 'price': 100, 'value': 0},
                 {'symbol': 'LTC', 'amount': 0, 'price': 10, 'value': 0}],
                diblo.Exchange()
            ),
            (
                [{'symbol': 'BTC', 'amount': 0, 'price': 1000, 'value': 0},
                 {'symbol': 'ETH', 'amount': 3.4982, 'price': 100,
                    'value': 349.82},
                 {'symbol': 'LTC', 'amount': 0, 'price': 10, 'value': 0}],
                diblo.Exchange({'holdings': [
                    {'symbol': 'ETH', 'amount': 3.4982}
                ]})
            ),
            (
                [{'symbol': 'BTC', 'amount': .4, 'price': 1000,
                    'value': 400},
                 {'symbol': 'ETH', 'amount': 3.4982, 'price': 100,
                    'value': 349.82},
                 {'symbol': 'LTC', 'amount': 10.43, 'price': 10,
                    'value': 104.3}],
                diblo.Exchange({'holdings': [
                    {'symbol': 'BTC', 'amount': .4},
                    {'symbol': 'ETH', 'amount': 3.4982},
                    {'symbol': 'LTC', 'amount': 10.43}
                ]})
            ),
        ]
    )
    def test_holdings(self, fiat_exchange, asset_allocation, market, holdings,
                      monkeypatch):
        monkeypatch.setattr(market, 'ticker', mock_ticker)
        blockfolio = diblo.Blockfolio(fiat_exchange, asset_allocation, market)
        assert holdings_equal(blockfolio.holdings, holdings)

    @pytest.mark.parametrize(
        'value, fiat_exchange', [
            (0, diblo.Exchange()),
            (0, diblo.Exchange({'holdings': []})),
            (0, diblo.Exchange({'holdings': [
                {'symbol': 'BTC', 'amount': 0}
            ]})),
            (500, diblo.Exchange({'holdings': [
                {'symbol': 'BTC', 'amount': .5}
            ]})),
            (750, diblo.Exchange({'holdings': [
                {'symbol': 'BTC', 'amount': 0.5},
                {'symbol': 'ETH', 'amount': 2.5}
            ]}))
        ]
    )
    def test_value(self, fiat_exchange, asset_allocation, market, value,
                   monkeypatch):
        monkeypatch.setattr(market, 'ticker', mock_ticker)
        blockfolio = diblo.Blockfolio(fiat_exchange, asset_allocation, market)
        assert blockfolio.value() == approx(value)
