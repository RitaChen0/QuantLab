import pandas as pd
import os
import time


def calculate_simple_20_day_momentum(data):
    # Calculate the momentum based on the closing prices
    momentum = (data['close'] - data['close'].shift(20)) / data['close'].shift(20)
    momentum = momentum.dropna()
    return momentum


def main():
    # Load data
    if not os.path.exists('price_data.h5'):
        print("price_data.h5 file not found.")
        return
    data = pd.read_hdf('price_data.h5', 'data')
    
    # Calculate the 20-day momentum factor
    momentum_factor = calculate_simple_20_day_momentum(data)
    
    # Prepare the result as a MultiIndex DataFrame
    momentum_factor = momentum_factor.reset_index()
    momentum_factor.columns = ['datetime', 'instrument', 'Simple20DayMomentum']
    momentum_factor.set_index(['datetime', 'instrument'], inplace=True)
    
    # Save the result
    result_path = 'result.h5'
    with pd.HDFStore(result_path) as store:
        store.put('Simple20DayMomentum', momentum_factor, format='table', data_columns=True)
        store.get_storer('Simple20DayMomentum').table.flush()
    
    # Ensure the file is properly closed and flushed
    time.sleep(1)  # Wait for the file system to update
    if not os.path.exists(result_path):
        print(f"Failed to save the file {result_path}.")
    else:
        print(f"File {result_path} saved successfully.")

if __name__ == '__main__':
    main()
