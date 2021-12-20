from bs4 import BeautifulSoup
from urllib.request import urlopen
import sys, os, pickle, sched, time, threading
from datetime import datetime

def scrapeAndSaveSoup(url, tgt):
    html = urlopen(url)
    soup = BeautifulSoup(html, "lxml")
    sys.setrecursionlimit(8000)
    currentTime = datetime.now().strftime("%Hh%M")
    soupFile = os.path.join(tgt, "soup_{}.pickle".format(currentTime))
    with open(soupFile, "wb") as f:
        pickle.dump(soup, f)


saveHere = r'P:\WORK\PYTHONPATH\RUG\projects\autoradiolockdown\ruggero-dev\scrapedData\audience\soups'
scrapeAndSaveSoup("http://radiolockdown.online:8000", saveHere)


## load a soup
src = r'P:\WORK\PYTHONPATH\RUG\projects\autoradiolockdown\ruggero-dev\scrapedData\audience\soups'
fName = os.path.join(src, "soup_21h30.pickle")
with open(fName, 'rb') as f:
    soup = pickle.load(f)

print(soup.prettify())

