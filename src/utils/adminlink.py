"""
Web Scraping Utilities for HTML Content Extraction

This module provides utilities for detecting JavaScript requirements and 
isolating URLs from HTML content using BeautifulSoup. It includes functions 
to identify JavaScript-dependent web pages, isolate simple and named URLs, 
and filter URLs based on specific string patterns.

Functions:
----------
- detect_javascript(soup_obj, catch_phrase='nur mit einem Javascript-fähigen Browser')
    Detects if a specific catch phrase, indicating the need for JavaScript, 
    is present in the HTML content.

- isolate_simple(soup_object, filter_function=None, *args, **kwargs)
    Isolates simple URLs from a BeautifulSoup object. Allows optional filtering 
    using a custom filter function.

- isolate_named(soup_object, return_errors=True, filter_function=None, *args, **kwargs)
    Isolates named URLs (those with 'aria-label' attributes) from a BeautifulSoup 
    object. Returns a dictionary of URLs and optionally a list of errors for 
    missing attributes.

- string_filter(url, search_string)
    Filters URLs based on a specified string pattern. Returns True if the URL 
    matches the pattern.

Dependencies:
-------------
- re: For regular expression operations.
- BeautifulSoup: For parsing and navigating HTML content.

Usage:
------
Import the functions and pass BeautifulSoup objects or other necessary arguments 
to utilize the web scraping utilities:

    from your_module import detect_javascript, isolate_simple, isolate_named, string_filter

Examples:
---------
```python
from bs4 import BeautifulSoup

# Example usage for detect_javascript
html_content = "<html>...</html>"
soup = BeautifulSoup(html_content, 'html.parser')
requires_js = detect_javascript(soup)

# Example usage for isolate_simple
simple_links = isolate_simple(soup)

# Example usage for isolate_named
named_urls, errors = isolate_named(soup)

# Example usage for string_filter
filtered = string_filter("http://example.com/page", "example")
"""

import re

def detect_javascript(soup_obj, 
                        catch_phrase='nur mit einem Javascript-fähigen Browser'):
    """
    Detects if a given catch phrase is present in a url request content, 
    indicating the need for selenium to crawl JavaScript based webpages

    Parameters:
    soup_obj (BeautifulSoup): The BeautifulSoup object to search within.

    catch_phrase (str): The catch phrase indicating the need for JavaScript
        (default is 'nur mit einem Javascript-fähigen Browser').

    Returns:
    bool: True if the catch phrase is found, otherwise False.
    """
    try:
        search_string = re.sub('\n+', ' ', soup_obj.text.strip())
        bool_ret =  catch_phrase in search_string
    except IndexError:
        bool_ret = False
    return bool_ret


def isolate_simple(soup_object, 
                   filter_function=None, 
                   *args, 
                   **kwargs):
    link_list = []
    for link in soup_object.find_all('a', href=True):
        if filter_function is None:
            link_list.append(link['href'])
        else:
            if filter_function(link['href'], **kwargs):
                link_list.append(link['href'])
            else:
                pass
    return link_list


def isolate_named(soup_object,
                  return_errors=True,
                  filter_function=None,
                  *args,
                  **kwargs):
    """
    Isolate named URLs from a BeautifulSoup object.

    Parameters:
    soup_object (BeautifulSoup): The BeautifulSoup object to search within.
    return_errors (bool): If True, returns a tuple containing a dictionary of named URLs and a list of errors (default is True).
    filter_function (function): A function used to filter URLs (default is None).
    *args: Variable length argument list.
    **kwargs: Arbitrary keyword arguments.

    Returns:
    tuple or dict: A tuple containing a dictionary of named URLs and a list of errors if return_errors is True,
    otherwise just the dictionary of named URLs.
    """
    error_log_list = []
    urls_dict = {}
    for item in soup_object.find_all('a'):
        try:
            key_ret = item['aria-label']
            follow_url = item['href']
            
            if filter_function is None:
                urls_dict[key_ret] = follow_url
            else:
                if filter_function(follow_url, **kwargs):
                    urls_dict[key_ret] = follow_url
                else:
                    pass

        except KeyError:
            error_log_list.append(item)

    if return_errors:
        return urls_dict, error_log_list
    else:
        return urls_dict
    
def string_filter(url, search_string):
    """
    Returns True if the given URL matches the search string pattern, otherwise False.

    Parameters:
    url (str): The URL to filter.
    search_string (str): The search string pattern.

    Returns:
    bool: True if the URL matches the search string pattern, otherwise False.
    """
    return bool(re.search(search_string, url))
