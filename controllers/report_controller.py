import logging
import traceback
from database.db import get_connection

logger = logging.getLogger(__name__)


def daily_summary(target_date: str) -> tuple[bool, dict | str]:
    try:
        conn = get_connection()
        sales = conn.execute(
            """SELECT COUNT(*) as count, COALESCE(SUM(total_amount),0) as revenue,
                      COALESCE(SUM(discount_value),0) as discounts,
                      COALESCE(SUM(tax_amount),0) as taxes
               FROM sales WHERE DATE(created_at)=? AND status='completed'""",
            (target_date,),
        ).fetchone()
        expenses = conn.execute(
            "SELECT COALESCE(SUM(amount),0) as total FROM expenses WHERE DATE(created_at)=?",
            (target_date,),
        ).fetchone()
        cost = conn.execute(
            """SELECT COALESCE(SUM(si.quantity * p.unit_price_buy),0) as total
               FROM sale_items si
               JOIN products p ON si.product_id = p.id
               JOIN sales s ON si.sale_id = s.id
               WHERE DATE(s.created_at)=? AND s.status='completed'""",
            (target_date,),
        ).fetchone()
        revenue = float(sales["revenue"])
        expense_total = float(expenses["total"])
        cost_total = float(cost["total"])
        profit = revenue - cost_total - expense_total
        return True, {
            "date": target_date,
            "sales_count": sales["count"],
            "revenue": revenue,
            "discounts": float(sales["discounts"]),
            "taxes": float(sales["taxes"]),
            "expenses": expense_total,
            "cost_of_goods": cost_total,
            "gross_profit": revenue - cost_total,
            "net_profit": profit,
        }
    except Exception:
        logger.error("report_controller.daily_summary\n%s", traceback.format_exc())
        return False, "Failed to generate daily summary"


def range_summary(date_from: str, date_to: str) -> tuple[bool, list | str]:
    try:
        conn = get_connection()
        rows = conn.execute(
            """SELECT DATE(s.created_at) as day,
                      COUNT(*) as sales_count,
                      COALESCE(SUM(s.total_amount),0) as revenue,
                      COALESCE(SUM(s.discount_value),0) as discounts,
                      COALESCE(SUM(s.tax_amount),0) as taxes
               FROM sales s
               WHERE DATE(s.created_at) BETWEEN ? AND ? AND s.status='completed'
               GROUP BY day ORDER BY day""",
            (date_from, date_to),
        ).fetchall()
        return True, [dict(r) for r in rows]
    except Exception:
        logger.error("report_controller.range_summary\n%s", traceback.format_exc())
        return False, "Failed to generate range summary"


def product_performance(date_from: str, date_to: str,
                        limit: int = 20) -> tuple[bool, dict | str]:
    try:
        conn = get_connection()
        best = conn.execute(
            """SELECT p.name, p.barcode,
                      SUM(si.quantity) as qty_sold,
                      SUM(si.subtotal) as revenue
               FROM sale_items si
               JOIN products p ON si.product_id=p.id
               JOIN sales s ON si.sale_id=s.id
               WHERE DATE(s.created_at) BETWEEN ? AND ? AND s.status='completed'
               GROUP BY p.id ORDER BY qty_sold DESC LIMIT ?""",
            (date_from, date_to, limit),
        ).fetchall()
        slow = conn.execute(
            """SELECT p.name, p.barcode,
                      COALESCE(SUM(si.quantity),0) as qty_sold,
                      p.stock_qty
               FROM products p
               LEFT JOIN sale_items si ON si.product_id=p.id
               LEFT JOIN sales s ON si.sale_id=s.id AND DATE(s.created_at) BETWEEN ? AND ? AND s.status='completed'
               WHERE p.is_active=1
               GROUP BY p.id ORDER BY qty_sold ASC LIMIT ?""",
            (date_from, date_to, limit),
        ).fetchall()
        return True, {
            "best_sellers": [dict(r) for r in best],
            "slow_movers": [dict(r) for r in slow],
        }
    except Exception:
        logger.error("report_controller.product_performance\n%s", traceback.format_exc())
        return False, "Failed to generate product performance report"


def customer_debt_summary() -> tuple[bool, list | str]:
    try:
        conn = get_connection()
        rows = conn.execute(
            """SELECT c.id, c.full_name, c.phone,
                      c.debt_amount, c.total_purchases, c.loyalty_points
               FROM customers c WHERE c.debt_amount > 0 ORDER BY c.debt_amount DESC"""
        ).fetchall()
        return True, [dict(r) for r in rows]
    except Exception:
        logger.error("report_controller.customer_debt_summary\n%s", traceback.format_exc())
        return False, "Failed to generate debt summary"


def end_of_day(target_date: str) -> tuple[bool, dict | str]:
    try:
        ok, summary = daily_summary(target_date)
        if not ok:
            return False, summary
        conn = get_connection()
        payment_breakdown = conn.execute(
            """SELECT payment_method, COUNT(*) as count, SUM(total_amount) as total
               FROM sales WHERE DATE(created_at)=? AND status='completed'
               GROUP BY payment_method""",
            (target_date,),
        ).fetchall()
        refunds = conn.execute(
            """SELECT COUNT(*) as count, COALESCE(SUM(total_refund),0) as total
               FROM returns WHERE DATE(created_at)=?""",
            (target_date,),
        ).fetchone()
        summary["payment_breakdown"] = [dict(r) for r in payment_breakdown]
        summary["refunds_count"] = refunds["count"]
        summary["refunds_total"] = float(refunds["total"])
        return True, summary
    except Exception:
        logger.error("report_controller.end_of_day\n%s", traceback.format_exc())
        return False, "Failed to generate end-of-day report"


def profit_report(date_from: str, date_to: str) -> tuple[bool, dict | str]:
    try:
        conn = get_connection()
        revenue_row = conn.execute(
            """SELECT COALESCE(SUM(total_amount),0) as revenue,
                      COALESCE(SUM(discount_value),0) as discounts
               FROM sales WHERE DATE(created_at) BETWEEN ? AND ? AND status='completed'""",
            (date_from, date_to),
        ).fetchone()
        cost_row = conn.execute(
            """SELECT COALESCE(SUM(si.quantity * p.unit_price_buy),0) as cost
               FROM sale_items si
               JOIN products p ON si.product_id=p.id
               JOIN sales s ON si.sale_id=s.id
               WHERE DATE(s.created_at) BETWEEN ? AND ? AND s.status='completed'""",
            (date_from, date_to),
        ).fetchone()
        expense_row = conn.execute(
            "SELECT COALESCE(SUM(amount),0) as total FROM expenses WHERE DATE(created_at) BETWEEN ? AND ?",
            (date_from, date_to),
        ).fetchone()
        revenue = float(revenue_row["revenue"])
        cost = float(cost_row["cost"])
        expenses = float(expense_row["total"])
        return True, {
            "date_from": date_from,
            "date_to": date_to,
            "revenue": revenue,
            "discounts": float(revenue_row["discounts"]),
            "cost_of_goods": cost,
            "gross_profit": revenue - cost,
            "expenses": expenses,
            "net_profit": revenue - cost - expenses,
        }
    except Exception:
        logger.error("report_controller.profit_report\n%s", traceback.format_exc())
        return False, "Failed to generate profit report"
