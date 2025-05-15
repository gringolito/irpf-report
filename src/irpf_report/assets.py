from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from datetime import date

from irpf_report.asset_types import StockType
from irpf_report.utils import format_date


@dataclass
class Asset(metaclass=ABCMeta):
    """Base class for all investment assets.

    Attributes:
        name (str): Name of the asset
        broker (str): Name of the broker holding the asset
    """

    name: str
    broker: str

    @property
    def key(self) -> str:
        return self.name

    @abstractmethod
    def get_group(self) -> int:
        pass

    @abstractmethod
    def get_code(self) -> int:
        pass

    @abstractmethod
    def get_description_fmt(self) -> str:
        pass

    def get_type(self) -> str:
        return str(self.__class__.__name__)

    def get_cnpj(self) -> str:
        return "N/A"

    def get_ticker(self) -> str | None:
        return None

    def get_maturity_date(self) -> str | None:
        return None

    def get_issuer(self) -> str | None:
        return None

    def has_matured(self, current_year: int) -> bool:
        return False


@dataclass
class StockExchangeListed(Asset):
    """
    A stock exchange listed asset representation with its essential information.

    Attributes:
        ticker (str): Trading symbol/ticker of the asset
        type (StockExchangeAssetType): Type of the asset
        cnpj (str): Brazilian company registration number (CNPJ) of the asset
    """

    ticker: str
    cnpj: str | None = field(default=None)
    type: StockType | None = field(default=None)

    @property
    def key(self) -> str:
        return self.ticker

    def get_cnpj(self) -> str:
        if self.cnpj is None:
            return "Desconhecido"
        if len(self.cnpj) != 14:
            return self.cnpj
        return "{}.{}.{}/{}-{}".format(self.cnpj[:2], self.cnpj[2:5], self.cnpj[5:8], self.cnpj[8:12], self.cnpj[12:])

    def get_ticker(self) -> str:
        return self.ticker

    @property
    def asset_name(self) -> str:
        return self.name.split("-", 1)[1].strip()


class Stock(StockExchangeListed):
    def get_group(self) -> int:
        return 3

    def get_code(self) -> int:
        return 1

    def get_description_fmt(self) -> str:
        assert self.type, "Missing stock type"
        type_mapping = {
            StockType.ON: "ações ON",
            StockType.PN: "ações PN",
            StockType.UNIT: "UNITs",
        }

        return f"%d {type_mapping[self.type]} emitidas pela empresa {self.asset_name}"

    def get_type(self) -> str:
        assert self.type, "Missing stock type"
        return self.type.name


class ETF(StockExchangeListed):
    def get_group(self) -> int:
        return 7

    def get_code(self) -> int:
        return 8

    def get_description_fmt(self) -> str:
        return f"%d cotas do ETF {self.asset_name}"


class BDR(StockExchangeListed):
    def get_group(self) -> int:
        return 4

    def get_code(self) -> int:
        return 4

    def get_description_fmt(self) -> str:
        return f"%d BDRs da empresa {self.asset_name}"


class FII(StockExchangeListed):
    def get_group(self) -> int:
        return 7

    def get_code(self) -> int:
        return 3

    def get_description_fmt(self) -> str:
        return f"%d cotas do fundo {self.asset_name}"


class FIIReceipt(StockExchangeListed):
    def get_group(self) -> int:
        return 99

    def get_code(self) -> int:
        return 99

    def get_description_fmt(self) -> str:
        return f"%d recibos de subscrição do fundo {self.asset_name} (código de negociação: {self.ticker})"


class FIDC(StockExchangeListed):
    def get_group(self) -> int:
        return 7

    def get_code(self) -> int:
        return 10

    def get_description_fmt(self) -> str:
        return f"%d cotas do fundo {self.asset_name}"


@dataclass
class FixedIncome(Asset):
    """
    A fixed income asset representation with its essential information.

    Attributes:
        maturity_date (date): When the title/bond matures
        issuer (str | None): Institution that issued the title/bond (defaults to: None)
    """

    maturity_date: date
    issuer: str | None = field(default=None)

    @property
    def key(self) -> str:
        return f"{self.name} - {self.broker}"

    def get_maturity_date(self) -> str:
        return format_date(self.maturity_date)

    def has_matured(self, current_year: int) -> bool:
        return self.maturity_date < date(current_year, 12, 31)

    def get_issuer(self) -> str | None:
        return self.issuer


class CDB(FixedIncome):
    def get_group(self) -> int:
        return 4

    def get_code(self) -> int:
        return 2

    def get_description_fmt(self) -> str:
        return f"%d CDBs emitidos pelo banco {self.issuer}, com vencimento em {format_date(self.maturity_date)}, sob custódia da corretora {self.broker}"


class LCI(FixedIncome):
    def get_group(self) -> int:
        return 4

    def get_code(self) -> int:
        return 3

    def get_description_fmt(self) -> str:
        return f"%d LCIs emitidas pelo banco {self.issuer}, com vencimento em {format_date(self.maturity_date)}, sob custódia da corretora {self.broker}"


class LCA(FixedIncome):
    def get_group(self) -> int:
        return 4

    def get_code(self) -> int:
        return 3

    def get_description_fmt(self) -> str:
        return f"%d LCAs emitidas pelo banco {self.issuer}, com vencimento em {format_date(self.maturity_date)}, sob custódia da corretora {self.broker}"


class Treasury(FixedIncome):
    def get_group(self) -> int:
        return 4

    def get_code(self) -> int:
        return 2

    def get_description_fmt(self) -> str:
        return f"%s títulos do {self.name}, com vencimento em {format_date(self.maturity_date)}, sob custódia da corretora {self.broker}"


# LC - Group 4 - Code 2
# CRI - Group 4 - Code 3
# CRA - Group 4 - Code 3
