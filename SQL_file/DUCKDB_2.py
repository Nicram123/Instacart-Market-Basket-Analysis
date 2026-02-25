import duckdb as db
con = db.connect()

def create_table_orders_bs(con):
    con.execute("""
    COPY (
        SELECT *
        FROM 'orders_new.parquet' o
        LEFT JOIN 'basket_size.parquet' b
        ON o.order_id = b.order_id
    )
    TO 'orders_bs.parquet' (FORMAT PARQUET);
    """)

def create_basket_size(con):
    con.execute("""
    COPY (
        SELECT 
            order_id,
            COUNT(*) AS basket_size
        FROM 'orders_new.parquet'
        GROUP BY order_id
        ORDER BY order_id
    )
    TO 'basket_size.parquet' (FORMAT PARQUET);
    """)


def create_user_product_orders(con):
    con.execute("""
    COPY (
        SELECT
            order_id,
            user_id,
            order_number,
            order_dow,
            order_hour_of_day,
            reordered,
            days_since_prior_order,
            add_to_cart_order,
            product_id
        FROM 'orders_new.parquet'
        ORDER BY user_id, product_id, order_number
    )
    TO 'user_product_orders.parquet' (FORMAT PARQUET);
    """)

#
def create_user_product_with_counts(con):
    con.execute("""
    COPY (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY user_id, product_id
                ORDER BY order_number
            ) - 1 AS times_user_bought_product_so_far
        FROM 'user_product_orders.parquet'
    )
    TO 'upo_step1.parquet' (FORMAT PARQUET);
    """)

def create_upo_step2(con):
  con.execute("""
      COPY (
        SELECT
            *,
            LAG(order_number) OVER (
                PARTITION BY user_id, product_id
                ORDER BY order_number
            ) AS last_order_number
        FROM 'upo_step1.parquet'
        ORDER BY user_id, product_id, order_number
  )
  TO 'upo_step2.parquet' (FORMAT PARQUET);
  """)


def create_upo_step3(con):
  con.execute("""
     COPY (
        SELECT
            *,
            CASE
                WHEN last_order_number IS NULL THEN 0
                ELSE order_number - last_order_number
            END AS orders_since_last_purchase
        FROM 'upo_step2.parquet'
    )
    TO 'upo_step3.parquet' (FORMAT PARQUET);
  """)


def create_upo_step5(con):
  con.execute("""
     COPY (
        SELECT
            *,
            AVG(days_since_prior_order) OVER (
                PARTITION BY user_id
                ORDER BY order_number
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
            ) AS user_avg_days_between_orders_so_far
        FROM 'upo_step3.parquet'
    )
    TO 'upo_step5.parquet' (FORMAT PARQUET);
  """)

def create_orders_bs(con):
  con.execute("""
     COPY (
        SELECT
            user_id,
            order_id,
            COUNT(*) AS basket_size
        FROM 'user_product_orders.parquet'
        GROUP BY user_id, order_id
    )
    TO 'orders_bs.parquet' (FORMAT PARQUET);
  """)



def create_upo_step6(con):
  con.execute("""
     COPY (
        SELECT
            upo.*,
            AVG(bs.basket_size) OVER (
                PARTITION BY upo.user_id
                ORDER BY upo.order_number
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
            ) AS user_avg_basket_size_so_far
        FROM 'upo_step5.parquet' upo
        JOIN 'orders_bs.parquet' bs USING(user_id, order_id)
    )
    TO 'upo_step6.parquet' (FORMAT PARQUET);
  """)

def create_upo_step7(con):
  con.execute("""
     COPY (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY product_id
                ORDER BY order_number
            ) - 1 AS product_total_purchases_so_far
        FROM 'upo_step6.parquet'
        ORDER BY order_number, order_id
    )
    TO 'upo_step7.parquet' (FORMAT PARQUET);
  """)

def create_upo_step8(con):
  con.execute("""
     COPY (
        SELECT
            *,
            COUNT(DISTINCT user_id) OVER (
                PARTITION BY product_id
                ORDER BY order_number
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
            ) AS product_unique_users_so_far
        FROM 'upo_step7.parquet'
    )
    TO 'upo_step8.parquet' (FORMAT PARQUET);
  """)

def create_upo_final(con):
  con.execute("""
     COPY (
        SELECT
            *,
            AVG(reordered) OVER (
                PARTITION BY user_id, product_id
                ORDER BY order_number
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
            ) AS user_product_reorder_rate_so_far
        FROM 'upo_step8.parquet'
    )
    TO 'upo_final.parquet' (FORMAT PARQUET);
  """)


#




