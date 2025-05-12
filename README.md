# irpf-report

Brazilian IRPF Report Generator from the B3 holdings reports

## Overview

This Python module processes B3 (Brazilian Stock Exchange) investment holdings reports in Excel format and generates data suitable for IRPF (Brazilian Income Tax) declarations. It supports various types of investments including:

- Stocks (Ações)
- BDRs (Brazilian Depositary Receipts)
- Fixed Income (Renda Fixa)
- Treasury Bonds (Tesouro Direto)
- Investment Funds (Fundos de Investimento)
- Stock Loans (Empréstimo de Ações)

## Installation

### Using pip

```bash
pip install irpf-report
```

### From source

```bash
git clone https://github.com/yourusername/irpf-report.git
cd irpf-report
pip install -e .
```

## Usage

TODO

## Development Setup

### Requirements

- uv (Python package installer)

### Setting up the development environment

1. Install uv (if not already installed):

```bash
pip install uv
```

1. Clone the repository:

```bash
git clone https://github.com/yourusername/irpf-report.git
cd irpf-report
```

1. Create and activate a virtual environment:

```bash
uv venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
```

1. Install dependencies:

```bash
uv sync
```

### Running Tests

TODO

## Contributing

1. Fork the repository
1. Create a feature branch (`git checkout -b feature/amazing-feature`)
1. Make your changes
1. Commit your changes (`git commit -m 'Add some amazing feature'`)
1. Push to the branch (`git push origin feature/amazing-feature`)
1. Open a Pull Request

## License

BEER-WARE License

## Authors

- Filipe Utzig - [GitHub](https://github.com/gringolito)
