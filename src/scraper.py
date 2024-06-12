"""
Combiner module for the scraper, contains two classes, one for crawling FEDRO content, 
and the other to crawl fedlex (slightly more efficiently), as there is a SPARQL endpoint
hosted by the confederation that contains additional information.
"""
import logging
import os
import pickle
import time
from typing import Optional, List, Dict, Callable

import requests
import hashlib
import urllib

import re
from bs4 import BeautifulSoup
import lxml

from typing import Optional, Callable

from .utils.adminlink import isolate_simple
from .utils.adminlink import detect_javascript
from .legal.helpers import isolate_legal_xml
from .legal.sparqlqueries import fetch_full_fedlex, fetch_citing_art, fetch_cited_by_art
from .utils.schemas import fedro_filetypes, fedro_filesplit


class PageScraper:
    """
    A class to scrape web pages and manage the scraping process, including storing 
    and processing the data.

    Parameters
    ----------
    predefined_filetypes : Optional[list], optional
        A predefined list of file types to recognize, by default None.
    predefined_filesplit : Optional[dict], optional
        A predefined dictionary specifying where to store different file types, by default None.
    predefined_links : Optional[dict], optional
        A predefined list of links to be crawled, by default None.
    predefined_done_links : Optional[list], optional
        A predefined list of links that have already been crawled, by default None.
    predefined_knowledge : Optional[dict], optional
        A predefined knowledge base, by default None.

    Attributes
    ----------
    defined_filetypes : list
        List of recognized file types for the scraper.
    write_split : dict
        Dictionary specifying file storage locations based on type.
    link_dict : list
        List of links to be crawled.
    done_links : list
        List of links that have already been crawled.
    knowledge_base : dict
        Dictionary to store information about crawled pages.
    legalfile_iterator : int
        Counter for naming legal files uniquely.
    logger : logging.Logger
        Logger for the scraper operations.
    """

    def __init__(self,
                 predefined_filetypes: Optional[list] = None, 
                 predefined_filesplit: Optional[dict] = None,
                 predefined_links: Optional[dict] = None,
                 predefined_done_links: Optional[list] = None,
                 predefined_knowledge: Optional[dict] = None) -> None:
        self.logger = logging.getLogger('scraper')
        self.logger.info('scraper instantiated')
        
        if predefined_filetypes is not None:
            self.defined_filetypes = predefined_filetypes
            self.logger.info('Using custom filetypes')
        else:
            self.defined_filetypes = fedro_filetypes
        
        if predefined_filesplit is not None:
            self.write_split = predefined_filesplit
            self.logger.info('Using custom filesplit')
        else:
            self.write_split = fedro_filesplit

        if predefined_links is not None:
            self.link_dict = predefined_links
            self.todo_links = predefined_links
            self.logger.info('Using predefined set of links')

        else:
            self.link_dict = []

        if predefined_done_links is not None:
            self.done_links = predefined_done_links
            self.logger.info('Using predefined set of done links')
        else:
            self.done_links = []
        
        if predefined_knowledge is not None:
            self.knowledge_base = predefined_knowledge
            self.logger.info('Using predefined knowledge base')
        else:
            self.knowledge_base = {}

        self.legalfile_iterator = 0

    def crawl_page(self,
                   write_dir: str,
                   initial_url: Optional[str] = 'https://www.astra.admin.ch/astra/de/home.html',
                   domain_url: Optional[str] = 'https://www.astra.admin.ch',
                   write: Optional[bool] = False,
                   replicate_pagestruct: Optional[bool] = False,
                   verbose: Optional[bool] = True,
                   retries: Optional[int] = 1,
                   **kwargs) -> None:
        """
        Crawls the web page starting from the initial URL and processes the links found.

        Parameters
        ----------
        write_dir : str
            Directory to save the crawled pages.
        initial_url : str, optional
            Initial URL to start crawling from, by default 'https://www.astra.admin.ch/astra/de/home.html'.
        domain_url : str, optional
            Base domain to prepend to relative links, by default 'https://www.astra.admin.ch'.
        write : bool, optional
            Whether the crawled pages should be saved to disk, by default False.
        replicate_pagestruct : bool, optional
            Whether to replicate the page structure when saving documents, by default False.
        verbose : bool, optional
            If True, print progress information to the console, by default True.
        retries : int, optional
            Number of retries if HTTP requests fail, by default 1.
        kwargs : dict
            Additional keyword arguments for page processing.

        Returns
        -------
        None
        """
        self.write_dir = write_dir
        if write:
            self._verify_filestructure(write_dir)

        if len(self.link_dict) == 0:
            self._process_page(url=initial_url, 
                               write_status=write, 
                               verbose=verbose, 
                               **kwargs)
            
        while len(self.todo_links) > 0:
            current_try = 0
            current_url = next(iter(self.todo_links))
            # print(current_url)

            if self._verify_linkparent(current_url):

                if not domain_url in current_url and not 'classified-compilation' in current_url and not 'fedlex' in current_url:
                    pull_url = domain_url + current_url
                else:
                    pull_url = current_url

                try:
                    self._process_page(url=pull_url, 
                                    write_status=write, 
                                    verbose=verbose, 
                                    **kwargs)
                except:
                    current_try += 1
                    if current_try >= retries:
                        time.sleep(5)
                        self._process_page(url=pull_url, 
                                        write_status=write, 
                                        verbose=verbose, 
                                        **kwargs)
            self._pop_item(current_url)
            

    def _process_page(self, 
                      url: str, 
                      write_status: bool, 
                      verbose: bool, 
                      **kwargs) -> None:
        """
        Processes a single web page by fetching its content, identifying its type, 
        and storing the content appropriately.

        Parameters
        ----------
        url : str
            URL of the page to process.
        write_status : bool
            Whether the page content should be saved to disk.
        verbose : bool
            If True, print progress information to the console.
        kwargs : dict
            Additional keyword arguments for HTML processing.

        Returns
        -------
        None
        """
        as_pickle = False
        crawl_object = requests.get(url)
        file_type, file_name = self._get_filenames(url)

        if file_type in ['html']:
            as_pickle = True
            crawl_object, file_type, file_name, linked_docs = self._process_html(url=url, 
                                                                                 crawl_object=crawl_object,
                                                                                 file_name=file_name, 
                                                                                 **kwargs)
        else:
            linked_docs = []

        hash_value = self._hash_file(crawl_object)
        self._store_object(url=url, 
                           object=crawl_object, 
                           file_name=file_name, 
                           file_type=file_type,
                           hex_hash=hash_value, 
                           neighbour_list=linked_docs, 
                           write=write_status, 
                           as_pickle=as_pickle)

        if verbose:
            print(f'processed: {url}')


    def _gather_links(self,
                      soup_obj: BeautifulSoup,
                      filter_function: Optional[Callable] = None,
                      filter_string: Optional[str] = None) -> List[str]:
        """
        Gathers links from the BeautifulSoup object and filters them using the given function or string.

        Parameters
        ----------
        soup_obj : BeautifulSoup
            The BeautifulSoup object to gather links from.
        filter_function : Optional[Callable], optional
            A function to filter URLs, by default None.
        filter_string : Optional[str], optional
            A string to filter URLs, by default None.

        Returns
        -------
        List[str]
            A list of gathered links.
        """
        new_list = isolate_simple(soup_obj,
                                  filter_function=filter_function,
                                  search_string=filter_string)

        if self.link_dict:
            set_new = set(new_list)
            set_existing = set(self.link_dict)

            crawl_new = list(set_new - set_existing)
            self.todo_links = crawl_new + self.todo_links
            self.todo_links = list(set(self.todo_links) - set(self.done_links))

            self.link_dict = self.link_dict + crawl_new
        else:
            self.link_dict = new_list
            self.todo_links = new_list

        return new_list

    def _get_filenames(self, 
                       url: str) -> (str, str):
        """
        Extracts the file name and type from the URL.

        Parameters
        ----------
        url : str
            The URL to extract the file name and type from.

        Returns
        -------
        tuple
            A tuple containing the file type and file name.
        """
        extract_name = re.compile(r'([^\/]+$)')
        extract_type = re.compile(r'([^\.]+$)')

        decoded_string = urllib.parse.unquote(url)
        file_name = re.search(extract_name, decoded_string)[0]
        file_type = re.search(extract_type, file_name.lower())[0]

        if not file_type in self.defined_filetypes:
            for file_t in self.defined_filetypes:
                if file_t in file_type:
                    file_type = file_t
                    return file_type, file_name
            file_type = 'else'
            return file_type, file_name
        else:
            return file_type, file_name
        
    def _process_html(self,
                      url: str,
                      crawl_object: requests.Response,
                      file_name: str,
                      **kwargs) -> (BeautifulSoup, str, str, List[str]):
        """
        Processes an HTML page, identifies any JavaScript, and fetches linked documents.

        Parameters
        ----------
        url : str
            The URL of the page to process.
        crawl_object : requests.Response
            The response object containing the page content.
        file_name : str
            The name of the file to save.
        kwargs : dict
            Additional keyword arguments for link gathering.

        Returns
        -------
        tuple
            A tuple containing the parsed BeautifulSoup object, file type, file name, and a list of linked documents.
        """
        soup = BeautifulSoup(crawl_object.content, 'html.parser')
        is_javascript = detect_javascript(soup)
        current_uri = None
        
        if is_javascript:
            # print('is_java')
            try:
                new_page, legal_status, current_uri = isolate_legal_xml(url)
                crawl_object = requests.get(new_page)
                soup = BeautifulSoup(crawl_object.content, 'xml')
            except Exception as e:
                self.logger.error(f'Error with file {url}, {e}')
                legal_status = 'else'

            file_name = f'crawled_legaldoc_{self.legalfile_iterator}'
            self.legalfile_iterator += 1
            if current_uri is not None:
                linked_docs = current_uri
            else:
                linked_docs = []
            current_uri = None
            if legal_status == 'in_force':
                file_type = 'legal_xml'
            else:
                file_type = 'else'
        else:
            file_type = 'html'
            linked_docs = self._gather_links(soup, **kwargs)
        
        parsed_data = self._parse_site(soup, file_type)
        
        return parsed_data, file_type, file_name, linked_docs
    
    def _parse_site(self, 
                    soup_obj: BeautifulSoup, 
                    file_type: str) -> BeautifulSoup:
        """
        Parses a site and returns the BeautifulSoup object.

        Parameters
        ----------
        soup_obj : BeautifulSoup
            The BeautifulSoup object to parse.
        file_type : str
            The type of file to parse.

        Returns
        -------
        BeautifulSoup
            The parsed BeautifulSoup object.
        """
        return soup_obj
    

    def _hash_file(self, response_object) -> str:
        """
        Computes a hash value for the given response object.

        Parameters
        ----------
        response_object : requests.Response or BeautifulSoup
            The response object to hash.

        Returns
        -------
        str
            The MD5 hash value of the response object.
        """
        if isinstance(response_object, requests.models.Response):
            hash_object = hashlib.md5(response_object.content).hexdigest()
        elif isinstance(response_object, BeautifulSoup):
            hash_object = hashlib.md5(response_object.text.encode('utf-8')).hexdigest()
        else:
            print('issue found')
            hash_object = '__error__'
        return hash_object

    def _store_object(self,
                      url: str, 
                      object, 
                      file_name: str, 
                      file_type: str,
                      hex_hash: str,
                      neighbour_list: List[str],
                      write: bool = False,
                      as_pickle: bool = False) -> None:
        """
        Stores the object to the specified location on disk and updates the knowledge base.

        Parameters
        ----------
        url : str
            The URL of the page.
        object : requests.Response or BeautifulSoup
            The object to store.
        file_name : str
            The name of the file to save.
        file_type : str
            The type of the file.
        hex_hash : str
            The hash value of the file.
        neighbour_list : List[str]
            List of linked documents.
        write : bool, optional
            Whether to write the object to disk, by default False.
        as_pickle : bool, optional
            Whether to save the object as a pickle file, by default False.

        Returns
        -------
        None
        """
        write_end_split = self.write_split[file_type]
        write_path = os.path.join(self.write_dir, write_end_split, file_name)

        self.knowledge_base[url] = {
            'storage_location': write_path,
            'file_hash': hex_hash,
            'neighbour_list': neighbour_list
        }

        if write:
            if not as_pickle:
                with open(write_path, 'wb') as con:
                    con.write(object.content)
            else:
                if '.html' in write_path:
                    comp_name = re.compile(r'(\.html)')
                    write_path = re.sub(comp_name, '.pkl', write_path)
                else:
                    write_path += '.pkl'
                with open(write_path, 'wb') as con:
                    pickle.dump(object, con)

    def _verify_filestructure(self, write_dir: str) -> None:
        """
        Verifies and creates the necessary directory structure for storing files.

        Parameters
        ----------
        write_dir : str
            The base directory to verify and create subdirectories in.

        Returns
        -------
        None
        """
        if len(os.listdir(write_dir)) == 0:
            self.logger.info('creating filestructure')
            for file_type in list(set(self.write_split.values())):
                os.mkdir(os.path.join(write_dir, file_type))
            os.mkdir(os.path.join(write_dir, '_overview'))
        elif set(list(set(self.write_split.values()))) - set(os.listdir(write_dir)) == {}:
            self.logger.info('filestructure exists continue')
        else:
            self.logger.info('incomplete filestructure, adding necessary files')
            for file_type in list(set(self.write_split.values())):
                if not os.path.exists(os.path.join(write_dir, file_type)):
                    os.mkdir(os.path.join(write_dir, file_type))
            if not os.path.exists(os.path.join(write_dir, '_overview')):
                os.mkdir(os.path.join(write_dir, '_overview'))

    def _verify_linkparent(self, 
                           link: str, 
                           whitelist: Optional[List]=['classified-compilation',
                                                      'fedlex',
                                                      'astra/de']) -> bool:
        # check if it contains exeternal link
        pass_val = False

        for white_page in whitelist:
            if white_page in link:
                pass_val = True

        return pass_val
            

    def _pop_item(self, 
                  url: str,
                  writing_steps: Optional[int] = 400):
        """
        Pop the current item from the todo links.

        Parameters:
        url (str): The URL to pop.
        verbose (bool): If True, print a message (default is True).
        """
        self.done_links.append(url)
        self.todo_links = list(set(self.todo_links)  - set(self.done_links))
        self.link_dict = list(set(self.link_dict))
        
        if len(self.done_links) % writing_steps == 0:
            print(len(self.done_links))
            with open(os.path.join(self.write_dir, '_overview', 'knowledge_base.pkl'), 'wb') as con:
                pickle.dump(self.knowledge_base, con)


class FedlexScraper:
    """
    scraper for the full set of fedlex, isolates the content but also makes use
    of the sparql endpoint to isolate dependencies across legal articles
    """
    def __init__(self) -> None:
        # fet full set of uris
        self.full_set = fetch_full_fedlex()
        self.crawled_legal_knowledge = {}

    def _scrap_feldex(self, id_counter=0, reset_counter=0):
        for legal_entry in self.full_set:
            # Set up feature to restart crawling if there is an error
            # use the reset counter if necessary
            if id_counter <= reset_counter:
                id_counter += 1
                continue
            print(f"Crawling {legal_entry['titel']}")
            web_string = legal_entry['sr_uri']
            web_string = re.sub('fedlex.data.admin.ch',
                                'www.fedlex.admin.ch',
                                web_string)
            web_string = web_string + '/de'

            xml_url, in_force_status = isolate_legal_xml(web_string)

            crawl_object = requests.get(xml_url)
            soup = BeautifulSoup(crawl_object.content, 'xml')

            # add some meta
            try:
                articles_citing_current = fetch_citing_art(legal_entry['sr_uri'])
            except:
                articles_citing_current = {}
            try:
                articles_cited_in_current = fetch_cited_by_art(legal_entry['sr_uri'])
            except:
                articles_cited_in_current = {}

            legal_entry['citing_article'] = articles_citing_current

            legal_entry['cited_in_article'] = articles_cited_in_current

            # save as pickle
            with open(f'data/01_raw/01_all/legal/legal_doc_{id_counter}.pkl', 'wb') as con:
                pickle.dump(soup, con)
            
            # add entry to knowledge base
            self.crawled_legal_knowledge[f'legal_doc_{id_counter}.pkl'] = legal_entry

            id_counter += 1

class OverwriteError(Exception):
    """Exception raised when an attempt is made to overwrite existing data."""
    pass