import logging
import csv

# Lists of what you have for a region or time range can be downloaded from your eBird account by going to https://ebird.org/lifelist/, using the dropdown menus
# near the top of the page to select the region and time range of your list, then downloading the list through
# the “Download (csv)” link near the upper-right corner of the page.


def get_have_list(name : str) -> list:
    """ Reads a csv of birds that are had already """
    result=[]
    with open(name, encoding ='utf-8', mode= 'rt') as f:
        reader = csv.reader(f)
        header=next(reader, None)
        if header[1] != 'Taxon Order' or header[3] != 'Common Name':
            logging.error('Expecting have list to be a csv with a header row as follows [Row #,Taxon Order,Category,Common Name,Scientific Name,Count,Location,S/P,Date,LocID,SubID,Exotic,Countable]')
        for species in reader:
            entry={}
            entry['name']=species[3]
            entry['taxonOrder']=int(species[1])
            result.append(entry)
    result=  sorted(result, key=lambda x: x['taxonOrder'])
    return result
