import pickle
import os
import argparse

from src.scraper import PageScraper, FedlexScraper
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

    os.mkdir('./crawled_data/fedlex')
    scraper_fedlex = FedlexScraper()
    scraper_fedlex._scrap_feldex(write_dir='./crawled_data/fedlex', 
                                 reset_counter=0)

    with open('.crawled_data/fedlex/_overview_fedlex.pkl', 'wb') as con:
        pickle.dump(scraper_fedlex.crawled_legal_knowledge, con)