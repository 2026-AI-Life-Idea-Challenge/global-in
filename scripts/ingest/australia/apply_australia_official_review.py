"""Apply or verify the dated Australian official-page comparison annotations."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from scripts.ingest.australia.review_support import refresh_reviews

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    refresh_reviews(check=parser.parse_args().check)
