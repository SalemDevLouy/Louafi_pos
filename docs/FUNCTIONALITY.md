# File & Functionality Explanation

This document provides a breakdown of every file in the POS System and its specific functionality.

## Root Directory
- **[main.py](main.py)**: The entry point of the application. It initializes the SQLite database, sets up the PyQt5 `QApplication`, applies the global stylesheet, and launches the `MainWindow`.
- **[styles.qss](styles.qss)**: A CSS-like file used by PyQt5 to define the visual appearance (colors, fonts, borders, etc.) of all UI components.

## [database/](database/)
- **[db.py](database/db.py)**: Handles all database-related infrastructural tasks.
  - `get_connection()`: Creates a connection to `pos.db`.
  - `init_db()`: Defines the schema (Tables: `products`, `sales`, `sale_items`, `customers`, `debt_entries`, `suppliers`) and creates them if they don't exist.

## [controllers/](controllers/)
This layer contains the core logic for data manipulation.
- **[product_controller.py](controllers/product_controller.py)**: Logic for CRUD operations on products, including inventory updates and barcode assignment.
- **[sales_controller.py](controllers/sales_controller.py)**: Manages the checkout process, recording sales, updating stock levels, and linking sale items.
- **[customer_controller.py](controllers/customer_controller.py)**: Manages customer records and debt tracking.
- **[supplier_controller.py](controllers/supplier_controller.py)**: Manages supplier information and their product categories.

## [views/](views/)
This layer contains the UI definitions using PyQt5.
- **[main_window.py](views/main_window.py)**: The primary shell of the app. Contains the sidebar navigation and a stacked widget to swap between different content views.
- **[dashboard_view.py](views/dashboard_view.py)**: Displays summary statistics (e.g., total sales, popular products) and quick-action charts.
- **[sales_view.py](views/sales_view.py)**: The Point-of-Sale interface where products are scanned/selected, quantities added, and transactions completed.
- **[products_view.py](views/products_view.py)**: The management interface for the product catalog.
- **[inventory_view.py](views/inventory_view.py)**: A focused view for tracking stock levels and low-stock alerts.
- **[customers_view.py](views/customers_view.py)**: Interface for managing the customer database and viewing debts.
- **[suppliers_view.py](views/suppliers_view.py)**: Interface for managing supplier information.
- **[reports_view.py](views/reports_view.py)**: Page for generating sales reports, filtering by date, and exporting data to CSV.

## [models/](models/)
Data structures representing the entities.
- **[product.py](models/product.py)**: Represents a single product item.
- **[sale.py](models/sale.py)** & **[sale_item.py](models/sale_item.py)**: Represent a transaction and the individual items within it.
- **[supplier.py](models/supplier.py)**: Represents a supplier entity.

## [utils/](utils/)
Helper modules for cross-cutting concerns.
- **[barcode.py](utils/barcode.py)**: Generates random/sequential barcodes for products.
- **[lang.py](utils/lang.py)** & **[tr.py](utils/tr.py)**: Manage multi-language support (localization).
- **[receipt.py](utils/receipt.py)**: Generates text-based receipts formatted for POS printers and saves them in the `receipts/` folder.
- **[icons.py](utils/icons.py)**: A wrapper for `qtawesome` to provide consistent icons across the UI.
- **[categories.py](utils/categories.py)**: Contains predefined product category lists used in dropdowns.

## [receipts/](receipts/)
A directory where the system automatically saves generated receipt files (e.g., `receipt_1_20260219_162923.txt`).
