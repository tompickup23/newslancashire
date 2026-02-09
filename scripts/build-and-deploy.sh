#!/bin/bash
# Build and deploy News Lancashire
set -e

cd ~/newslancashire/site

# Build site
hugo --minify

# Fix permissions
sudo chown -R www-data:www-data ~/newslancashire/site/public

echo "Site built and deployed at $(date)"
