#!/bin/bash
set -e

# This script runs as root to fix permissions before starting the application

# Create RD-Agent workspace directories
echo "Setting up RD-Agent workspace..."
mkdir -p /app/git_ignore_folder/RD-Agent_workspace
mkdir -p /app/git_ignore_folder/factor_implementation_source_data
mkdir -p /app/git_ignore_folder/factor_implementation_source_data_debug
mkdir -p /app/pickle_cache
mkdir -p /app/log

# Fix ownership for RD-Agent directories
echo "Fixing RD-Agent workspace permissions..."
chown -R quantlab:quantlab /app/git_ignore_folder/ || true
chown -R quantlab:quantlab /app/pickle_cache || true
chown -R quantlab:quantlab /app/log || true

# Switch to quantlab user and execute the original command
echo "Switching to quantlab user..."
exec gosu quantlab "$@"
