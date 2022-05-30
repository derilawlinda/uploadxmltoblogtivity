#!/usr/bin/env python3

from numpy.core.fromnumeric import repeat
from numpy.core.numeric import NaN
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import pandas as pd
from bs4 import BeautifulSoup
import os
import argparse
import logging
import time
from multiprocessing import Pool, freeze_support
import requests.cookies
from tqdm.contrib.concurrent import process_map,thread_map
from itertools import product
import tqdm
from lxml import html

def strip_html(string):
    stripped = html.fromstring(string)
    return stripped.text_content().strip()

def get_blog_url(string):
    stripped = html.fromstring(string)
    return stripped.get('href')

class BlogtivityUploadBot :
    def __init__(self):
       
        parser = argparse.ArgumentParser(description='Bot untuk upload file xml ke Blogtivity')
        parser.add_argument("--topik", help="Topik yang dicari, pastikan ada folder dengan nama topik yang sama di folder xmls", default="")
        upass = open("username.txt").read()
        upass_split = upass.split("\n")
        userid = upass_split[0].split(":")[1].strip()
        pwd = upass_split[1].split(":")[1].strip()
        domain = upass_split[2].split(":")[1].strip()
        retry_in_minute = upass_split[3].split(":")[1].strip()
        self.__userid = userid
        self.__pwd = pwd
        self.__domain = domain
        self.__retry_in_minute = retry_in_minute
        args = parser.parse_args()
        cari = args.topik
        self.__cari = cari
        try:
            cookie_str = open("cookies.txt").read()
            self.__cookie = {"PHPSESSID": cookie_str}
            self.__get_new_data()
            self.upload(cari=args.topik)
        except IOError:
            self.__login()
            time.sleep(1)
        logging.basicConfig(filename='blogtivity.log', level=logging.INFO,format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S')

  
        
    def __get_new_data(self) : 
        print("Mengambil data terbaru..")
        try :
            with requests.Session() as s:
                # body = "draw=0&columns%5B0%5D%5Bdata%5D=no&columns%5B0%5D%5Bname%5D=&columns%5B0%5D%5Bsearchable%5D=true&columns%5B0%5D%5Borderable%5D=true&columns%5B0%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B0%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B1%5D%5Bdata%5D=account&columns%5B1%5D%5Bname%5D=&columns%5B1%5D%5Bsearchable%5D=true&columns%5B1%5D%5Borderable%5D=true&columns%5B1%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B1%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B2%5D%5Bdata%5D=blog&columns%5B2%5D%5Bname%5D=&columns%5B2%5D%5Bsearchable%5D=true&columns%5B2%5D%5Borderable%5D=true&columns%5B2%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B2%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B3%5D%5Bdata%5D=success&columns%5B3%5D%5Bname%5D=&columns%5B3%5D%5Bsearchable%5D=true&columns%5B3%5D%5Borderable%5D=true&columns%5B3%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B3%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B4%5D%5Bdata%5D=failed&columns%5B4%5D%5Bname%5D=&columns%5B4%5D%5Bsearchable%5D=true&columns%5B4%5D%5Borderable%5D=true&columns%5B4%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B4%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B5%5D%5Bdata%5D=schedule&columns%5B5%5D%5Bname%5D=&columns%5B5%5D%5Bsearchable%5D=true&columns%5B5%5D%5Borderable%5D=true&columns%5B5%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B5%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B6%5D%5Bdata%5D=create&columns%5B6%5D%5Bname%5D=&columns%5B6%5D%5Bsearchable%5D=true&columns%5B6%5D%5Borderable%5D=true&columns%5B6%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B6%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B7%5D%5Bdata%5D=remove&columns%5B7%5D%5Bname%5D=&columns%5B7%5D%5Bsearchable%5D=true&columns%5B7%5D%5Borderable%5D=true&columns%5B7%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B7%5D%5Bsearch%5D%5Bregex%5D=false&order%5B0%5D%5Bcolumn%5D=0&order%5B0%5D%5Bdir%5D=asc&start=0&length=10&search%5Bvalue%5D=&search%5Bregex%5D=false"
                
                
                body = """ draw=0
                &columns%5B0%5D%5Bdata%5D=url&columns%5B0%5D%5Bname%5D=url&columns%5B0%5D%5Bsearchable%5D=true&columns%5B0%5D%5Borderable%5D=true&columns%5B0%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B0%5D%5Bsearch%5D%5Bregex%5D=false
                &order%5B0%5D%5Bcolumn%5D=1&order%5B0%5D%5Bdir%5D=asc
                &start=0
                &length=10
                &search%5Bvalue%5D=&search%5Bregex%5D=false """
                blogs = s.post("https://"+self.__domain+"/fordata/blogdata/userid/1",data=body,cookies=self.__cookie,headers={
                    "Host": self.__domain,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7,af;q=0.6,ms;q=0.5",
                    "Cache-Control": "max-age=0",
                    "Content-Length": str(len(body)),
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "Origin": "https://"+self.__domain,
                    "Referer": "https://"+self.__domain+"/log/index/status/EhjT1YDERZ5gxbLl5pYoMwgQY2kEtwW4M1RBRWJ0SnlzQkRGT2JvRVMxSGJsQT09nw8WiR3yjLWv4UZ5iTJ7E1cDqQCYjUGG",
                    "Upgrade-Insecure-Requests": "1",
                    "User-Agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"
                })
                # print(blogs.text)
                # sys.exit()
                df = pd.read_json(blogs.text)
                df2 = pd.json_normalize(df['data'])
                df_new = pd.DataFrame()
                df_new["id"] = df2["no"]
                df_new["blog_title"] = df2["blog"].apply(strip_html)
                df_new["blog_url"] = df2["blog"].apply(get_blog_url)
                df_new["scheduled_post"] = df2["schedule"].apply(strip_html)
                df_new["xml"] = "-"
                df_new = df_new.astype({'id':'int','scheduled_post':'int'})
                df_new = df_new.sort_values(by=['scheduled_post'],ascending=True)
                df_new = df_new.set_index("id")
                if os.path.exists("blogs.csv") :
                    df_old = pd.read_csv("blogs.csv")
                    df_old = df_old.sort_values(by=['scheduled_post'],ascending=True)
                    df_old = df_old.set_index("id")
                    if not df_new.equals(df_old) :
                        df_diff = (len(df_new) - len(df_old))
                        print("Sinkronisasi data baru dan lama..")
                        if df_diff > 0:
                            print("Terdapat penambahan {df_diff} blog".format(df_diff = df_diff))
                        elif df_diff < 0:
                            print("Terdapat pengurangan {df_diff} blog".format(df_diff = df_diff))
                        df_old = df_old[df_old["xml"] != "-"][["xml"]]
                        for index, row in df_old.iterrows():
                            df_new.at[index,"xml"] = row["xml"]

                df_new.to_csv("blogs.csv",index=True)
        except Exception as e: 
            self.__login()
            time.sleep(1)
            
    
    def upload(self,cari) :
        logging.basicConfig(filename='blogtivity.log', level=logging.INFO,format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
        cari = self.__cari
        df_new = pd.read_csv("blogs.csv")
        if cari != "" :
            df_filtered = df_new[df_new['blog_title'].str.contains(cari,case=False)]
            df_filtered = df_filtered.set_index("id")
            self.__uploadToBlogtivity(cari,df_filtered=df_filtered,df_new = df_new,cookie=self.__cookie)
                
        # else :
        #     reply = self.__confirm_prompt("Akan mengupload semua file xml di dalam folder xmls ke seluruh blog ? ")
        #     if reply :
        #         df_filtered = df_new
        #         self.__uploadToBlogtivity(cari="",df_filtered = df_filtered,df_new = df_new,cookie=self.__cookie)
        #     else :
        #         cari = input('Ketik kategori : ')
        #         df_filtered = df_new[df_new['blog_title'].str.contains(cari,case=False)]
        #         self.__uploadToBlogtivity(cari,df_filtered=df_filtered,df_new = df_new,cookie=self.__cookie)
    
    
                    
    def __uploadToBlogtivity(self,cari,df_filtered,df_new,cookie) :
        
        if cari != "" :
            if not os.path.isdir("xmls/"+cari) :
                print("Tidak ada folder {0} di dalam folder xmls".format(cari))
                return False
        self.__cari = cari
        xml_in_dir = os.listdir("xmls/"+cari)
        xml_assigned = df_new[df_new.xml != "-"]["xml"].to_list()
        xml_available = [x for x in xml_in_dir if x not in xml_assigned]
        if len(xml_available) == 0 :
            print("XML sudah digunakan di semua blog")
            return False
        df_filtered = df_filtered.head(len(xml_available))
        if(len(df_filtered)> 0) :
            xml_counter = 0
            for index,row in df_filtered.iterrows() :
                df_filtered.at[index,'xml'] = xml_available[xml_counter]
                xml_counter += 1
            records = df_filtered[["blog_url","blog_title"]].to_records(index=True)
            df_filtered_tuples =  list(zip(df_filtered.index,df_filtered["blog_url"], df_filtered["blog_title"],df_filtered["xml"]))
            print("Run multiprocessing..")
            if __name__ == '__main__':
                freeze_support()  # for Windows support
                process_map(self.mpupload,df_filtered_tuples,chunksize=1)
                if os.path.exists("cookies.txt") :
                    os.remove("cookies.txt")
            #     # res = process_map(self.mpupload, df_filtered_tuples)
            print("ALL DONE")
        else :
            print("Topik tidak ditemukan")
            return False

    def mpupload(self,args) :
            s2success = False
            s3success = False
            blog_index = args[0]
            blog_url = args[1]
            blog_title = args[2]
            xml_file_name = args[3]
            print("Uploading {0} to {1}".format(xml_file_name,blog_title))
            cari = self.__cari
            blog_id = ''
            cookie = self.__cookie
            with requests.Session() as s2:
                while not s2success :
                    try:
                        get_id_req = s2.get(blog_url,cookies=cookie,timeout=120)
                        s2success = True
                    except Exception as e:
                        print("{xml_file} untuk {blog_title} : Retrying..".format(xml_file=xml_file_name,blog_title=blog_title))
                        wait = int(self.__retry_in_minute) * 60
                        time.sleep(wait)
            if get_id_req.status_code == 200 :
                blog_page_soup = BeautifulSoup(get_id_req.text, "html.parser")
                blog_id = blog_page_soup.find_all('form')[1].find('input')["value"]
                if blog_id != '':
                    
                    multipart_data = MultipartEncoder(
                        fields={
                                'fileisi' : (xml_file_name, open('xmls/'+cari+'/'+xml_file_name,'rb')),
                                'blogs[]': blog_id, 
                                'randomize': 'Y',
                                'parser' : 'xml_shuriken',
                                'status' : 'connect'
                        }
                    )
                    s3 = requests.Session()
                    upload_api = "https://"+self.__domain+"/posts/setimport"

                    while not s3success :
                        try:
                            s3.post(upload_api,data=multipart_data,cookies=cookie,timeout=120,headers={
                                "Host": self.__domain,
                                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                                "Accept-Encoding": "gzip, deflate, br",
                                "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7,af;q=0.6,ms;q=0.5",
                                "Cache-Control": "max-age=0",
                                "Content-Type": multipart_data.content_type,
                                "Origin": "https://"+self.__domain,
                                "Referer": blog_url,
                                "Upgrade-Insecure-Requests": "1",
                                "User-Agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"
                            })
                            logging.info("Upload {xml_file} untuk {blog_title}".format(xml_file=xml_file_name,blog_title=blog_title))
                            df_new = pd.read_csv('blogs.csv')
                            df_new = df_new.set_index("id")
                            df_new.at[blog_index, 'xml'] = xml_file_name
                            df_new.to_csv("blogs.csv",index=True)
                            s3success = True
                            print("Upload successfully : {xml_file} untuk {blog_title}".format(xml_file=xml_file_name,blog_title=blog_title))
                            return True
                        except Exception as e:
                            print("{xml_file} untuk {blog_title} : Retrying..".format(xml_file=xml_file_name,blog_title=blog_title))
                            wait = int(self.__retry_in_minute) * 60
                            time.sleep(wait)
            else :
                print("{xml_file} untuk {blog_title} : Gagal mendapatkan ID blog".format(xml_file=xml_file_name,blog_title=blog_title))
                return False
                
    

    def __login(self) :
            print("Pencarian blog dengan topik {0}".format(self.__cari))
            upass = open("username.txt").read()
            upass_split = upass.split("\n")
            userid = upass_split[0].split(":")[1].strip()
            pwd = upass_split[1].split(":")[1].strip()
            domain = upass_split[2].split(":")[1].strip()
            cookie = {}
            api = "https://"+domain+"/log/login"
            body = "username="+userid+"&password="+pwd
            s = requests.Session()
            print("Logging in to blogtivity..")
            req = s.get("https://"+domain+"/log/")
            cookie = {'PHPSESSID': req.cookies['PHPSESSID']}
            self.__cookie = cookie
            r = s.post(api, data=body, cookies=cookie,headers={
            "Host": domain,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7,af;q=0.6,ms;q=0.5",
            "Cache-Control": "max-age=0",
            "Content-Length": str(len(body)),
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://"+domain,
            "Referer": "https://"+domain+"/log/index/status/EhjT1YDERZ5gxbLl5pYoMwgQY2kEtwW4M1RBRWJ0SnlzQkRGT2JvRVMxSGJsQT09nw8WiR3yjLWv4UZ5iTJ7E1cDqQCYjUGG",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"
            })
            if "Blogtivity Admin | Dashboard" in r.text:
                print("Logged in")
                cookie_str = cookie['PHPSESSID']
                f = open("cookies.txt", 'w')
                f.write(cookie_str)
                f.close()
                return {"status" : True, 
                "cookie" : cookie}
            else :
                return {"status" : False, 
                "cookie" : cookie}
if __name__ == '__main__':
    BlogtivityUploadBot()

