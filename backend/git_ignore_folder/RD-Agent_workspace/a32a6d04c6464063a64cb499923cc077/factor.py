import pandas as pd
import os


def calculate_Simple10DayMomentum(prices):
    momentum = (prices - prices.shift(10)) / prices.shift(10)
    return momentum


def main():
    # Define file paths relative to the script location
    script_dir = os.path.dirname(__file__)
    data_file_path = os.path.join(script_dir, 'data.h5')
    result_file_path = os.path.join(script_dir, 'result.h5')

    # Check if the data file exists
    if not os.path.exists(data_file_path):
        print(f"Data file does not exist at {data_file_path}")
        return

    prices = pd.read_hdf(data_file_path, 'prices')

    # Check for the necessary 'close' column and multi-index
    if 'close' not in prices.columns:
        print("'close' column is missing in the data.")
        return
    if not isinstance(prices.index, pd.MultiIndex):
        print("Data index is not a MultiIndex.")
        return

    # Calculate the momentum factor
    momentum_values = calculate_Simple10DayMomentum(prices['close'])

    # Prepare DataFrame to save
    momentum_df = momentum_values.to_frame('Simple10DayMomentum')
    momentum_df.index.name = 'datetime'
    momentum_df['instrument'] = prices.index.get_level_values('instrument')
    momentum_df.set_index(['datetime', 'instrument'], inplace=True)

    # Save to HDF5
    momentum_df.to_hdf(result_file_path, key='Simple10DayMomentum', mode='w', format='table')

if __name__ == '__main__':
    main()
