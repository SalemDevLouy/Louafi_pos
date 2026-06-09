# POS System

A desktop Point of Sale (POS) application built with Python and PyQt5.

## Features

- **Dashboard**: Overview of sales and inventory.
- **Product Management**: Add, update, and delete products with barcode generation.
- **Inventory Tracking**: Monitor stock levels.
- **Sales Management**: Process transactions and generate receipts.
- **Customer & Supplier Management**: Maintain records of customers and suppliers.
- **Reports**: Generate sales reports and export to CSV.
- **Multilingual Support**: Supports multiple languages via local translation files.

## Project Structure

- `main.py`: Application entry point.
- `views/`: PyQt5 UI components and layouts.
- `controllers/`: Business logic and database interaction layers.
- `models/`: Data representations.
- `database/`: Database schema and connection management (SQLite).
- `utils/`: Utility functions for barcodes, translations, receipts, and icons.
- `receipts/`: Generated PDF/Text receipts.
- `styles.qss`: Global application styling.

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd pos_system
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
   ```

3. **Install dependencies**:
   ```bash
   pip install PyQt5 qtawesome
   ```

## Usage

Run the application:
```bash
python main.py
```

## License

MIT
