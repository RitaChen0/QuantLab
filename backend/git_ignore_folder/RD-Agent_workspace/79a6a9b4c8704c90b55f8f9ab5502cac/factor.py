import pandas as pd
import os


def calculate_20DaySMA(data):
    # Ensure the 'close' column exists in the dataframe
    if 'close' not in data.columns:
        raise ValueError('The required column \'close\' is not present in the data.')
    # Calculate the 20-day Simple Moving Average with strict 20-day window
    sma_20 = data['close'].rolling(window=20, min_periods=20).mean()
    return sma_20


def main():
    # Load historical data
    if not os.path.exists('data.h5'):
        print('data.h5 file not found. Please ensure the file is in the current directory.')
        return
    data = pd.read_hdf('data.h5', 'stock_data')

    # Verify and set the required MultiIndex ['datetime', 'instrument']
    if 'datetime' not in data.columns or 'instrument' not in data.columns:
        raise ValueError('Required columns \'datetime\' or \'instrument\' are missing from the data.')
    data.set_index(['datetime', 'instrument'], inplace=True)

    # Ensure 'close' is still in the data columns after indexing
    if 'close' not in data.columns:
        raise ValueError('Column \'close\' is missing after setting index.')

    # Calculate 20-day SMA
    data['20DaySMA'] = calculate_20DaySMA(data)

    # Prepare the result DataFrame with correct MultiIndex format
    result_df = pd.DataFrame(data['20DaySMA'])
    result_df.columns = ['20DaySMA']

    # Save the result to HDF5 file ensuring the correct directory
    result_path = 'result.h5'
    result_df.to_hdf(result_path, key='df', mode='w', format='table', data_columns=True)
    if not os.path.exists(result_path):
        raise Exception('Failed to create the result.h5 file. Check directory permissions and disk space.')

if __name__ == '__main__':
    main()
