WITH
  sonic AS (
    SELECT
      userId, status, startTimestamp, endTimestamp,
      CASE
        WHEN status = "ACTIVE" THEN TIMESTAMP(startTimestamp)
        ELSE TIMESTAMP(endTimestamp) END
        AS date_time,
      CASE WHEN status = "ACTIVE" THEN TRUE ELSE FALSE END
        AS is_active
    FROM `flanders-raw-production.videos_sonic.subscriptions` AS subs
      INNER JOIN `flanders-raw-production.socialmedia_insights.country_codes` AS countries
        ON subs.subscribedInCountry = LOWER(countries.Two_Letter_Country_Code)
    WHERE countries.Continent_Name = "Europe"
  ),
  
  ordered_sonic AS (
    SELECT *,
      EXTRACT(YEAR FROM date_time) AS yr,
      EXTRACT(MONTH FROM date_time) AS mnth
    FROM sonic
    WHERE date_time >= "2020-06-01"
  ),
  
  dates AS (
    SELECT *
    FROM (
      SELECT DISTINCT CONCAT(yr, "-", LPAD(CAST(mnth AS STRING), 2, "0")) AS yr_mnth,
        DATE_ADD(DATE(yr, mnth, 1), INTERVAL 1 MONTH) AS start_of_next_mnth
      FROM ordered_sonic
      WHERE DATE(date_time) BETWEEN "2020-06-01" AND CURRENT_DATE()
    )
  ),
  
  user_ids AS (
    SELECT userId, yr_mnth, start_of_next_mnth
    FROM (SELECT DISTINCT userId FROM ordered_sonic)
      CROSS JOIN dates
  ),
  
  user_ids_and_active_date AS (
    SELECT user_ids.userId, user_ids.yr_mnth, user_ids.start_of_next_mnth, active_sonic.date_time,
      ROW_NUMBER() OVER (PARTITION BY user_ids.userId, user_ids.yr_mnth, user_ids.start_of_next_mnth ORDER BY active_sonic.date_time DESC) AS r_n
    FROM user_ids
      INNER JOIN (SELECT * FROM ordered_sonic WHERE is_active) AS active_sonic
      USING (userId)
    WHERE DATE(active_sonic.date_time) < user_ids.start_of_next_mnth
  ),
  
  user_ids_and_term_or_canc_date AS (
    SELECT user_ids.userId, user_ids.yr_mnth, user_ids.start_of_next_mnth, term_or_canc_sonic.date_time,
      ROW_NUMBER() OVER (PARTITION BY user_ids.userId, user_ids.yr_mnth, user_ids.start_of_next_mnth ORDER BY term_or_canc_sonic.date_time DESC) AS r_n
    FROM user_ids
      INNER JOIN (SELECT * FROM ordered_sonic WHERE NOT is_active) AS term_or_canc_sonic
      USING (userId)
    WHERE DATE(term_or_canc_sonic.date_time) < user_ids.start_of_next_mnth
  ),
  
  user_ids_new AS (
    SELECT userId, yr_mnth, start_of_next_mnth FROM user_ids_and_active_date
    UNION ALL
    SELECT userId, yr_mnth, start_of_next_mnth FROM user_ids_and_term_or_canc_date
  ),
  
  user_ids_and_dates AS (
    SELECT user_ids_new.yr_mnth, user_ids_new.start_of_next_mnth, user_ids_new.userId,
      IFNULL(active_sonic.date_time, TIMESTAMP("1000-01-01 00:00:00 UTC")) AS start_time,
      IFNULL(term_or_canc_sonic.date_time, TIMESTAMP("3000-01-01 00:00:00 UTC")) AS end_time
    FROM user_ids_new
      LEFT JOIN (SELECT * FROM user_ids_and_active_date WHERE r_n = 1) AS active_sonic
        USING (userId, yr_mnth, start_of_next_mnth)
      LEFT JOIN (SELECT * FROM user_ids_and_term_or_canc_date WHERE r_n = 1) AS term_or_canc_sonic
        USING (userId, yr_mnth, start_of_next_mnth)
  ),
  
  is_active_in_mnth AS (
    SELECT yr_mnth, start_of_next_mnth, userId,
      CASE WHEN (DATE(start_time) >= DATE_SUB(start_of_next_mnth, INTERVAL 1 MONTH) AND DATE(start_time) < start_of_next_mnth) OR DATE(end_time) >= start_of_next_mnth THEN TRUE
        ELSE FALSE
        END AS is_active
    FROM user_ids_and_dates
  )

SELECT yr_mnth, COUNT(DISTINCT CASE WHEN is_active THEN userId END) AS distinct_active_subs
FROM is_active_in_mnth
GROUP BY yr_mnth
ORDER BY yr_mnth
