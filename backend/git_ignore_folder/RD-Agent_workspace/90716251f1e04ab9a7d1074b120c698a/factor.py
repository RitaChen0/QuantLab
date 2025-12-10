import pandas as pd
import numpy as np
import os

# Function to calculate VolumeWeightedMomentum10Days
def calculate_volume_weighted_momentum_10_days(prices, volumes):
    # Handle NaN values in prices and volumes
    prices = prices.fillna(method='ffill')
    volumes = volumes.fillna(method='ffill')
    # Calculate weighted prices
    weighted_prices = prices * volumes
    # Sum of weighted prices and volumes for the last 10 days
    sum_weighted_prices = weighted_prices.rolling(window=10).sum()
    sum_volumes = volumes.rolling(window=10).sum()
    # Calculate the volume-weighted average price (VWAP) for the last 10 days
    vwap = np.where(sum_volumes > 0, sum_weighted_prices / sum_volumes, np.nan)
    # Calculate the momentum
    momentum = vwap - prices.shift(10)
    return momentum

# Main function
def calculate_VolumeWeightedMomentum10Days():
    # Ensure data file is in the correct directory
    data_path = 'data.h5'
    if not os.path.exists(data_path):
        print(f"The file {data_path} does not exist. Please ensure the data file is placed in the correct directory.")
        return
    # Load data
    data = pd.read_hdf(data_path, 'data')
    # Check DataFrame structure
    if not {'datetime', 'instrument', 'close', 'volume'}.issubset(data.columns):
        raise ValueError("Dataframe must contain 'datetime', 'instrument', 'close', and 'volume' columns.")
    prices = data['close']
    volumes = data['volume']
    # Calculate factor
    factor_values = calculate_volume_weighted_momentum_10_days(prices, volumes)
    factor_values.name = 'VolumeWeightedMomentum10Days'
    # Prepare DataFrame with MultiIndex
    factor_values = pd.DataFrame(factor_values)
    factor_values['datetime'] = data.index.get_level_values('datetime')
    factor_values['instrument'] = data.index.get_level_values('instrument')
    factor_values.set_index(['datetime', 'instrument'], inplace=True)
    # Check and create output file path
    output_path = 'result.h5'
    # Save to HDF5
    factor_values.to_hdf(output_path, key='data', mode='w')
    print('Output file result.h5 has been successfully created.')

if __name__ == '__main__':
    calculate_VolumeWeightedMomentum10Days()
