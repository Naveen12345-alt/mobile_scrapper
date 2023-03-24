import time
import logging
import argparse
import requests
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path
from stem import Signal
from stem.control import Controller
import re

logger = logging.getLogger("gsmarena-scraper")
temps_debut = time.time()


class tor_network:
    def __init__(self):
        self.session = requests.session()
        self.session.proxies = {
            "http": "socks5h://localhost:9050",
            "https": "socks5h://localhost:9050",
        }
        self.ntries = 0

    def get_soup(self, url):
        while True:
            try:
                self.ntries += 1
                soup = BeautifulSoup(
                    self.session.get(url).content, features="lxml"
                )
                if soup.find("title").text.lower() == "too many requests":
                    logger.info(f"Too many requests.")
                    self.request_new_ip()
                elif soup or self.ntries > 30:
                    self.ntries = 0
                    break
                logger.debug(
                    f"Try {self.ntries} : Problem with soup for {url}."
                )
            except Exception as e:
                logger.debug(f"Can't extract webpage {url}.")
                self.request_new_ip()
        return soup

    def request_new_ip(self):
        logger.info("Requesting new ip address.")
        with Controller.from_port(port=9051) as controller:
            controller.authenticate(password="my password")
            controller.signal(Signal.NEWNYM)
        self.session = requests.session()
        self.session.proxies = {
            "http": "socks5h://localhost:9050",
            "https": "socks5h://localhost:9050",
        }
        self.ntries = 0

def rematch(regex, string):
    try:
        matched = re.match(regex, string)
        return matched  
    except:
        print("No Match Found")
        return null


def main():
    args = parse_args()

    network = tor_network()

    all_brands_data = pd.read_csv("device_chipset_map.csv",delimiter=",",on_bad_lines='skip')
    url_index = "https://www.notebookcheck.net/Mobile-Processors-Benchmark-List.2436.0.html"
    soup_index = network.get_soup(url_index)
    processorsInfo = soup_index.find_all("tr",{"class",re.compile(r"smartphone_odd|smartphone_even")})
    soup_index.decompose()
    processors=[]
    chipset_data=[]
    not_found_error_data=[]
    for processor in processorsInfo:
        a_val=processor.find("a")
        if a_val:
            tup_a_val=tuple((a_val.text.lower(),a_val))
            processors.append(tup_a_val)

    for index, row in all_brands_data.iterrows():
        device_name=row["Name"]
        chipset=row["chipset"]
        try:
            chipset_found=False
            for item,a_val in processors:
                if isinstance(chipset,str) and ((item in str(chipset.lower())) or (str(chipset.lower()) in item) or rematch(".*".join(item.split()),chipset.lower()) or rematch(".*".join(chipset.lower().split()),item)):
                    chipset_found=True
                    chipset_soup=network.get_soup(a_val["href"])
                    processorData=chipset_soup.find("table",{"class","gputable"}).find_all("tr",re.compile(r"gpu-even|gpu-odd"))
                    for data in processorData:
                        try:
                            if data != None and data.find("td",{"class","caption"}) and data.find("td",{"class","caption"}).text == "Architecture":
                                Architecture_info=data.find_all("td")
                                Architecture_collection=[]
                                for info in Architecture_info:
                                    Architecture_collection.append(info.text)
                                Architecture_collection.append(chipset)
                                Architecture_collection.append(device_name)
                                print(Architecture_collection)
                                chipset_data.append(Architecture_collection)
                            if data != None and data.find("td",{"class","caption"}) and data.find("td",{"class","caption"}).text == "64 Bit":
                                Bit_info=data.find_all("td")
                                Bit_collection=[]
                                for info in  Bit_info:
                                    Bit_collection.append(info.text)
                                Bit_collection.append(chipset)
                                Bit_collection.append(device_name)
                                print(Bit_collection)
                                chipset_data.append(Bit_collection)
                        except:
                            print("Architecture Not Found",chipset)
                            not_found_error_data.append(["Architecture Not Found",chipset,device_name])
            if chipset_found==False:
                print("Chipset Not Found",chipset)
                not_found_error_data.append(["Chipset Not Found",chipset,device_name])
        except:
            print("An exception occurred")
            not_found_error_data.append(["An exception occurred",chipset,device_name])

        df = pd.DataFrame(chipset_data)
        df.to_csv('chipset.csv', sep=";", index=False)

        af=pd.DataFrame(not_found_error_data)
        af.to_csv('chipset_info_not_found.csv', sep=";", index=False)

    # global_list_smartphones = pd.DataFrame()
    # for brand in brands:
    #     brand_name = extract_brand_name(brand)
    #     brand_export_file = f"Exports/{brand_name}_export.csv"
    #     If file doesn't already exists, extract smartphone informations.
    #     if not Path(brand_export_file).is_file():
    #         brand_dict = pd.DataFrame.from_records(
    #             extract_brand_infos(network, brand)
    #         )
    #         brand_dict.to_csv(brand_export_file, sep=";", index=False)
    #         global_list_smartphones = pd.concat(
    #             [global_list_smartphones, brand_dict], sort=False
    #         )
    #     Otherwise, read the file.
    #     else:
    #         logger.warning(
    #             "Skipping %s, %s already exists. Its content will be added to the global export file.",
    #             brand_name,
    #             brand_export_file,
    #         )
    #         brand_dict = pd.read_csv(brand_export_file, sep=";")
    #         global_list_smartphones = pd.concat(
    #             [global_list_smartphones, brand_dict], sort=False
    #         )
    # all_export_file = "Exports/all_brands_export.csv"
    # logger.info("Exporting all smartphone to %s.", all_export_file)
    # global_list_smartphones.to_csv(all_export_file, sep=";", index=False)

    # logger.info("Runtime : %.2f seconds" % (time.time() - temps_debut))


def parse_args():
    parser = argparse.ArgumentParser(description="Scraper gsmarena.")
    parser.add_argument(
        "--debug",
        help="Display debugging information",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.INFO,
    )
    args = parser.parse_args()

    logger.setLevel(args.loglevel)
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)
    return args


if __name__ == "__main__":
    main()
