"""
https://ratings.fide.com/profile/
"""

import requests
import re

from bs4 import BeautifulSoup


def get_fide_rating(username:int):
    url = f"https://ratings.fide.com/profile/{username}"
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        rating_element = soup.find('div', class_='rating')
        if rating_element:
            rating = rating_element.text.strip()
            return rating
    return None

rating = get_fide_rating(10297677)
print(rating)
