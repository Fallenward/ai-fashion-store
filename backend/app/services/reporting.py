from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.money import money
from app.models import Order, Product, Role, User
from app.services.catalog_admin import low_stock
from app.services.serializers import order_summary

SALES_STATUSES = ("paid", "processing", "shipped", "delivered")


def dashboard(db: Session) -> dict:
    sales = db.scalar(select(func.coalesce(func.sum(Order.total), 0)).where(Order.status.in_(SALES_STATUSES)))
    orders = db.scalar(select(func.count()).select_from(Order).where(Order.status != "cancelled")) or 0
    products = db.scalar(select(func.count()).select_from(Product).where(Product.is_active.is_(True))) or 0
    customers = db.scalar(
        select(func.count()).select_from(User).join(Role).where(Role.name == "customer", User.is_active.is_(True))
    ) or 0
    recent = db.scalars(
        select(Order).options(selectinload(Order.items), selectinload(Order.payment)).order_by(Order.created_at.desc()).limit(8)
    ).all()
    start = datetime.now(timezone.utc).date() - timedelta(days=13)
    day = func.date_trunc("day", Order.created_at)
    series = db.execute(
        select(day, func.coalesce(func.sum(Order.total), 0))
        .where(Order.status.in_(SALES_STATUSES), Order.created_at >= datetime.combine(start, datetime.min.time(), timezone.utc))
        .group_by(day)
        .order_by(day)
    ).all()
    by_day = {row[0].date().isoformat(): float(row[1]) for row in series if row[0] is not None}
    chart = []
    for offset in range(14):
        key = (start + timedelta(days=offset)).isoformat()
        chart.append({"date": key, "total": f"{by_day.get(key, 0):.2f}"})
    return {
        "total_sales": money(sales),
        "total_orders": int(orders),
        "total_products": int(products),
        "total_customers": int(customers),
        "recent_orders": [order_summary(order) for order in recent],
        "low_stock": low_stock(db),
        "sales_chart": chart,
    }
