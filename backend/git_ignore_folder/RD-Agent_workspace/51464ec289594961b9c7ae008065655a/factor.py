import pandas as pd
import numpy as np
import h5py


def calculate_simple_10_day_momentum(price_data):
    # Calculate the momentum based on the formula given
    momentum = (price_data - price_data.shift(10)) / price_data.shift(10)
    return momentum


def main():
    # Assuming 'price_data.h5' is the file where daily closing prices are stored
    # Load data
    with h5py.File('price_data.h5', 'r') as f:
        price_data = pd.DataFrame(np.array(f['closing_prices']), columns=['closing_price'])
        price_data.index = pd.to_datetime(np.array(f['dates'], dtype='str'))

    # Calculate the 10-day momentum
    result = calculate_simple_10_day_momentum(price_data['closing_price'])

    # Prepare the result in the required format
    result_df = pd.DataFrame(result, columns=['Simple 10-Day Momentum'])
    result_df.index.name = 'datetime'
    result_df.reset_index(inplace=True)
    result_df['instrument'] = 'Default_Instrument'  # Replace with actual instrument identifier if available
    result_df.set_index(['datetime', 'instrument'], inplace=True)

    # Save the result to an HDF5 file
    with pd.HDFStore('result.h5', 'w') as store:
        store.put('data', result_df, format='table')

if __name__ == '__main__':
    main()
