import pandas as pd
import numpy as np

# ОЖИДАЕМЫЕ КОЛОНКИ В СЫРЬЕ:
# customer_id, order_id, order_date, margin
# РЕКОМЕНДАЦИИ: используйте маржу (margin), окно ~180 дней, исключите возвраты/отмены заранее.

def _safe_qcut(s, q=4, labels=None):
    """qcut с фолбэком на ранги, если мало уникальных значений."""
    s = s.astype(float)
    try:
        return pd.qcut(s, q=q, labels=labels, duplicates="drop")
    except ValueError:
        r = s.rank(method="average", pct=True)
        bins = np.linspace(0, 1, q + 1)
        idx = np.digitize(r, bins, right=True)  # 0..q
        idx[idx == 0] = 1
        idx[idx > q] = q
        if labels is None:
            return pd.Series(idx, index=s.index)
        else:
            lab = np.array(labels)
            return pd.Series(lab[idx - 1], index=s.index)

def rfm_segment(
    df,
    today=None,
    window_days=180,
    n_bins=4,
    value_col="margin",
    id_col="customer_id",
    date_col="order_date",
):
    if today is None:
        today = pd.Timestamp.today().normalize()

    work = df.copy()
    work[date_col] = pd.to_datetime(work[date_col])

    # Окно данных
    cutoff = today - pd.Timedelta(days=window_days)
    work = work.loc[work[date_col] >= cutoff]

    # Агрегация по клиенту
    agg = (work
           .groupby(id_col)
           .agg(last_dt=(date_col, "max"),
                F=("order_id", "count"),
                M=(value_col, "sum"))
           .reset_index())
    agg["R"] = (today - agg["last_dt"]).dt.days

    # Баллы 1..4: для R меньше = лучше (инвертируем метку)
    R_labels = list(range(n_bins, 0, -1))   # 4,3,2,1
    FM_labels = list(range(1, n_bins + 1))  # 1,2,3,4

    agg["R_bin"] = _safe_qcut(agg["R"], q=n_bins, labels=R_labels).astype(int)
    agg["F_bin"] = _safe_qcut(agg["F"], q=n_bins, labels=FM_labels).astype(int)
    agg["M_bin"] = _safe_qcut(agg["M"], q=n_bins, labels=FM_labels).astype(int)

    # Человеческие ярлыки
    R_names = {1: "Спящий", 2: "Остывающий", 3: "Тёплый", 4: "Недавний"}
    F_names = {1: "Единичный", 2: "Редкий", 3: "Регулярный", 4: "Частый"}
    M_names = {1: "Низкая ценность", 2: "Средняя", 3: "Высокая", 4: "Премиум"}

    agg["rfm_tag"] = agg["R_bin"].astype(str) + "-" + agg["F_bin"].astype(str) + "-" + agg["M_bin"].astype(str)
    agg["rfm_name"] = (
        agg["R_bin"].map(R_names) + " · " +
        agg["F_bin"].map(F_names) + " · " +
        agg["M_bin"].map(M_names)
    )

    # (Опционально) укрупнённый операционный ярлык — легко добавить CASE-правилами тут

    # Удобный порядок колонок
    cols = [id_col, "last_dt", "R", "F", "M", "R_bin", "F_bin", "M_bin", "rfm_tag", "rfm_name"]
    return agg[cols]

# === Пример использования ===
# df = pd.read_csv("orders.csv")
# result = rfm_segment(df, window_days=180)
# result.head()
