import pandas as pd
import numpy as np
import os


def calculate_10DayPriceMomentum(data):
    # Ensure the required column 'close' is present
    if 'close' not in data.columns:
        raise KeyError('Column close is missing from the input data.')

    # Calculate the 10-day price momentum
    momentum = (data['close'] - data['close'].shift(10)) / data['close'].shift(10)
    momentum = momentum.rename('10DayPriceMomentum')
    return momentum


def main():
    # Check if the file exists
    file_path = 'sample_price_data.csv'
    if not os.path.exists(file_path):
        print(f'The file {file_path} does not exist. Please ensure the file is in the current directory.')
        return

    # Load sample data
    data = pd.read_csv(file_path, parse_dates=['datetime'], index_col=['datetime', 'instrument'])

    # Handle missing data
    data['close'] = data['close'].fillna(method='ffill')

    # Calculate the 10-day price momentum
    result = calculate_10DayPriceMomentum(data)

    # Ensure the result has the correct MultiIndex format
    if not isinstance(result.index, pd.MultiIndex):
        raise ValueError('The index of the result DataFrame is not a MultiIndex. Please check the data format.')

    # Save the result to a HDF5 file
    with pd.HDFStore('result.h5', 'w') as store:
        store.put('data', result, format='table', data_columns=True)

if __name__ == '__main__':
    main()
