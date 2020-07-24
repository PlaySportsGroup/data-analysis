import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import pandas as pd
from pandas.plotting import register_matplotlib_converters; register_matplotlib_converters()

def grouped_data(input_df, date_field_name, min_date, max_date):
    new_input_df = input_df.copy()
    new_input_df[f'{date_field_name}YearMonth'] = pd.to_datetime(new_input_df[date_field_name]).dt.to_period('M')
    new_input_df = new_input_df[(new_input_df[f'{date_field_name}YearMonth'] < max_date)
                                & (new_input_df[f'{date_field_name}YearMonth'] >= min_date)]
    date_field_name = new_input_df.groupby([f'{date_field_name}YearMonth']).sum()
    return date_field_name

def return_indices_from_date(df, start_date, end_date):
    start_index = len(df) - len(df[start_date:])
    end_index = len(df) - len(df[:end_date]) + 1
    return start_index, end_index

def basic_regression(x, y):
    regressor = LinearRegression()
    regressor.fit(x, y)
    y_reg = regressor.predict(x)

    return y_reg, regressor

def return_reg_data(df_grouped, metric_name, start_date, end_date, months_to_predict):
    df_grouped = df_grouped[start_date:end_date]
    df_grouped = df_grouped
    x = np.arange(len(df_grouped)).reshape(-1, 1)
    y = df_grouped[metric_name].values.reshape(-1, 1)

    y_reg, regressor = basic_regression(x, y)

    x_extended = np.arange(len(x) + months_to_predict).reshape(-1, 1)
    y_reg_extended = regressor.predict(x_extended)

    return x, y, y_reg, x_extended, y_reg_extended

def return_x_months_arrays(start_date, data_length):
    x = pd.period_range(start=start_date,
                        periods=data_length,
                        freq='M')
    x_timestamp = x.to_timestamp(how='end')
    return x, x_timestamp

def plot_regression(x, y, x_reg, y_reg, scatter_col='red'):
    plt.figure(figsize=(20, 10))
    plt.scatter(x, y, c=scatter_col)
    plt.plot(x_reg, y_reg, c='black')
    plt.show()


def get_weighted_average_yearly(df_grouped, start_date, end_date, years, months):
    df_grouped_yearly = df_grouped[start_date:end_date]
    arr_grouped_yearly = df_grouped_yearly.values.reshape(years, 12)

    normalised_arr_yearly = np.zeros(arr_grouped_yearly.shape)

    arr_length = len(arr_grouped_yearly)

    # Normalising to get the seasonal fluctations
    for counter, yearly_data in enumerate(arr_grouped_yearly):
        x_temp = np.arange(len(yearly_data)).reshape(-1, 1)
        y_temp = yearly_data.reshape(-1, 1)
        y_temp_reg, regressor = basic_regression(x_temp, y_temp)
        normalised_arr_yearly[counter] = (y_temp / y_temp_reg).reshape(-1)

    # Taking a weighted average by year
    weighted_average_arr_yearly = np.zeros(12)

    for i in range(arr_length):
        weighted_average_arr_yearly += (i + 1) * normalised_arr_yearly[i]

    weighted_average_arr_yearly = weighted_average_arr_yearly / (arr_length * (arr_length + 1) / 2)
    return weighted_average_arr_yearly


def plot_data_and_model(weighted_average_arr_yearly, x_months, x_months_extended, x_months_plotting,
                        x_months_extended_plotting, y, y_reg_extended, scatter_colour='red'):
    indexing_arr = [i - 1 for i in x_months_extended.month.values]
    factor_array = weighted_average_arr_yearly[indexing_arr]
    seasonal_reg_model = factor_array * (y_reg_extended.reshape(-1))

    plt.figure(figsize=(20, 10))
    plt.scatter(x_months_plotting, y / 10 ** 6, c=scatter_colour)
    plt.plot(x_months_extended_plotting, seasonal_reg_model / 10 ** 6, c='black')
    matplotlib.rcParams.update({'font.size': 16})
    plt.xlabel('Date')
    plt.ylabel('Monthly views (millions)')
    plt.show()

    return seasonal_reg_model


def months_diff(start_string, end_string):
    strings_arr = [start_string, end_string]
    strings_arr = [s.split("-") for s in strings_arr]
    strings_arr = [12 * int(a[0]) + int(a[1]) for a in strings_arr]
    total_months = strings_arr[1] - strings_arr[0] + 1
    return total_months // 12, total_months % 12


def complete_model_build(csv_loc, strict_start_date, strict_end_date, seasonal_data_start_month,
                         seasonal_data_end_month, months_to_predict, scatter_col='red'):
    '''
    csv_loc: CSV location - CSV should contain two columns, date and views on that date
    strict_start_date: start of the data to consider
    strict_end_date: end of the data to consider
    seasonal_data_start_month: first date to build the seasonal model from, of the form "yyyy-mm", where ideally mm=01
    seasonal_data_end_month: last date to build the model from, of the form "yyyy-mm", where ideally mm=12
    months_to_predict: number of months after the end of the data to predict for

    '''
    df = pd.read_csv(csv_loc).sort_values(by="date")
    df_grouped = grouped_data(df, "date", strict_start_date, strict_end_date)
    x, y, y_reg, x_extended, y_reg_extended = return_reg_data(df_grouped, "views",
                                                              strict_start_date, strict_end_date,
                                                              months_to_predict)
    x_months, x_months_plotting = return_x_months_arrays(min(df['date']), len(x))
    x_months_extended, x_months_extended_plotting = return_x_months_arrays(min(df['date']), len(x_extended))
    plot_regression(x_months_plotting, y, x_months_extended_plotting, y_reg_extended, scatter_col)

    years, months = months_diff(seasonal_data_start_month, seasonal_data_end_month)
    seasonal_arr = get_weighted_average_yearly(df_grouped, seasonal_data_start_month, seasonal_data_end_month, years,
                                               months)

    plt.plot(np.arange(12), seasonal_arr)
    plt.show()
    seasonal_plus_reg_model = plot_data_and_model(seasonal_arr, x_months, x_months_extended, x_months_plotting,
                                                  x_months_extended_plotting, y, y_reg_extended, scatter_col)
    return pd.DataFrame({"month": x_months_extended, "model": seasonal_plus_reg_model})

yt_views_gcn_loc = "/Users/thomas.schafer/Documents/Python/Forecast model/bq-results-20200721-111718-onwq0glk4dx4.csv"
__ = complete_model_build(yt_views_gcn_loc, "2000-01-01", "2020-06-30", '2015-01', '2019-12', 24)

yt_views_gmbn_loc = "/Users/thomas.schafer/Documents/Python/Forecast model/Chan_nel 2014-11-05_2020-07-21 Global Mountain Bike Network/Totals.csv"
__ = complete_model_build(yt_views_gmbn_loc, "2000-01-01", "2020-06-30", '2015-01', '2019-12', 24, 'black')