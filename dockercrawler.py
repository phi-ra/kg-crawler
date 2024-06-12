import pickle
import os
import argparse

from src.scraper import PageScraper
from src.utils.adminlink import string_filter

if __name__ == "__main__":
    scraper = PageScraper()

    scraper.crawl_page(
        write_dir='./crawled_data',
        write=True,
        verbose=True, 
        filter_function=string_filter, 
        filter_string='astra/de|classified-compilation|fedlex', 
    )

