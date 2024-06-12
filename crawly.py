import pickle
import os
import argparse

from src.scraper import PageScraper
from src.utils.adminlink import string_filter

def crawly_go_crawl(args):
    """
    Crawler utility to be used on a command line call
    """
    if args.predefined_link is not None:
        scraper = PageScraper(predefined_links=[args.predefined_link])
    else:
        scraper = PageScraper()

    scraper.crawl_page(
        write_dir=args.write_dir, 
        write=args.write,
        verbose=args.verbose, 
        filter_function=args.filter_function, 
        filter_string=args.filter_string, 
    )

    with open(os.path.join(args.write_dir, '_overview', 'scraper_class.pkl'), 'wb') as con:
        pickle.dump(scraper, con)


if __name__ == "__main__":
    # add parser
    parser = argparse.ArgumentParser(description='Arguments')

    parser.add_argument("--predefined_link", 
                        type=str,
                        default=None)
    parser.add_argument("--write_dir",
                        type=str, 
                        default='./crawled_data')
    parser.add_argument("--write",
                        type=bool,
                        default=True)
    parser.add_argument('--verbose',
                        type=bool,
                        default=True)
    parser.add_argument('--filter_function',
                        type=string_filter,
                        default=string_filter)
    parser.add_argument('--filter_string',
                        type=str,
                        default='astra/de|classified-compilation|fedlex')


    args = parser.parse_args()

    crawly_go_crawl(args)