#!/usr/bin/env python3

from numpy.core.numeric import NaN
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import pandas as pd
from bs4 import BeautifulSoup
import os
import argparse
from halo import Halo
import logging

class BlogtivityUploadBot :
    def __init__(self,userid,pwd,domain):
        self.__userid = userid
        self.__pwd = pwd
        self.__domain = domain
        logging.basicConfig(filename='blogtivity.log', level=logging.INFO,format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S')

    def __confirm_prompt(self,question: str) -> bool:
        reply = None
        while reply not in ("", "y", "n"):
            reply = input(f"{question} (Y/n): ").lower()
        return (reply in ("", "y"))
    
    def upload(self,cari) :
        api = "https://"+self.__domain+"/log/login"
        body = "username="+self.__userid+"&password="+self.__pwd
        with requests.Session() as s:
            print("Logging in to blogtivity..")
            req = s.get("https://"+self.__domain+"/log/")
            cookie = {'PHPSESSID': req.cookies['PHPSESSID']}
            r = s.post(api, data=body, cookies=cookie,headers={
            "Host": self.__domain,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7,af;q=0.6,ms;q=0.5",
            "Cache-Control": "max-age=0",
            "Content-Length": str(len(body)),
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://"+self.__domain,
            "Referer": "https://"+self.__domain+"/log/index/status/EhjT1YDERZ5gxbLl5pYoMwgQY2kEtwW4M1RBRWJ0SnlzQkRGT2JvRVMxSGJsQT09nw8WiR3yjLWv4UZ5iTJ7E1cDqQCYjUGG",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"
            })
            if "Blogtivity Admin | Dashboard" in r.text:
                print("Logged in")
                print("Cek untuk data baru..")
                blogs = s.get("https://"+self.__domain+"/accounts/blog",cookies=cookie)
                soup = BeautifulSoup(blogs.text, "html.parser")
                rows = soup.find_all('table')[0].find_all("tr")
                df_new = pd.DataFrame()  
                for row in rows:
                    cells = row.find_all('td')
                    if(len(cells) > 0):
                        new_row = {
                            "id" : cells[0].text,
                            "blog_title" : cells[2].text,
                            "blog_url" : cells[2].find('a')['href'],
                            "scheduled_post" : int(cells[5].text)
                        }
                        df_new = df_new.append(new_row, ignore_index=True)
                
                df_new["xml"] = "-"
                df_new.sort_values(by=['scheduled_post'],ascending=True)
                df_new.set_index("id")

                if os.path.isfile("blogs.csv") :
                    df_old = pd.read_csv("blogs.csv")
                    if not df_new.equals(df_old) :
                        df_diff = (len(df_new) - len(df_old))
                        print("Sinkronisasi data baru dan lama..")
                        if df_diff > 0:
                            print("Terdapat penambahan {df_diff} blog".format(df_diff = df_diff))
                        elif df_diff < 0:
                            print("Terdapat pengurangan {df_diff} blog".format(df_diff = df_diff))
                        df_old = df_old[df_old["xml"] != "-"][["id","xml"]].set_index("id")
                        for index, row in df_old.iterrows():
                            df_new.at[index,"xml"] = row["xml"]
                else :
                    df_new.to_csv("blogs.csv",index=True)
                
                if cari != "" :
                    print("Pencarian blog dengan topik {0}".format(cari))
                    df_filtered = df_new[df_new['blog_title'].str.contains(cari,case=False)]
                    self.__uploadToBlogtivity(cari,df_filtered=df_filtered,df_new = df_new,s=s,cookie=cookie)
                        
                else :
                    
                    reply = self.__confirm_prompt("Akan mengupload semua file xml di dalam folder xmls ke seluruh blog ? ")
                    if reply :
                        df_filtered = df_new
                        self.__uploadToBlogtivity(cari="",df_filtered = df_filtered,df_new = df_new,s=s,cookie=cookie)
                    else :
                        cari = input('Ketik kategori : ')
                        df_filtered = df_new[df_new['blog_title'].str.contains(cari,case=False)]
                        self.__uploadToBlogtivity(cari,df_filtered=df_filtered,df_new = df_new,s=s,cookie=cookie)
    
    
                    
    def __uploadToBlogtivity(self,cari,df_filtered,df_new,s,cookie) :
        
        if cari != "" :
            if not os.path.isdir("xmls/"+cari) :
                print("Tidak ada folder {0} di dalam folder xmls".format(cari))
                return False
        xml_in_dir = os.listdir("xmls/"+cari)
        xml_assigned = df_new[df_new.xml != "-"]["xml"].to_list()
        xml_available = [x for x in xml_in_dir if x not in xml_assigned]
      
        if len(xml_available) == 0 :
            print("XML sudah digunakan di semua blog")
            return False

        counter = 0
        all_blog = len(df_filtered)
        if(len(df_filtered)> 0) :
            for index, row in df_filtered.iterrows():
                if 0 <= counter < len(xml_available):
                    xml_file_name = xml_available[counter]
                    spinner_upload = Halo(text="Upload {xml_file} untuk {blog_title}".format(xml_file=xml_file_name,blog_title=row["blog_title"]), spinner='dots')
                    blog_id = ''
                    with requests.Session() as s2:
                        get_id_req = s2.get(row["blog_url"],cookies=cookie)
                        blog_page_soup = BeautifulSoup(get_id_req.text, "html.parser")
                        blog_id = blog_page_soup.find_all('form')[1].find('input')["value"]
                    if blog_id != '':
                        spinner_upload.start()
                        multipart_data = MultipartEncoder(
                            fields={
                                    'fileisi' : (xml_file_name, open('xmls/'+cari+'/'+xml_file_name,'rb')),
                                    'blogs': blog_id, 
                                    'randomize': 'Y',
                                    'parser' : 'xml_shuriken',
                                    'status' : 'connect'
                            }
                        )
                        upload_api = "https://"+self.__domain+"/posts/setimport"
                        
                        with requests.Session() as s3:
                            
                            upload_xml_req = s3.post(upload_api,data=multipart_data,cookies=cookie,headers={
                                "Host": self.__domain,
                                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                                "Accept-Encoding": "gzip, deflate, br",
                                "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7,af;q=0.6,ms;q=0.5",
                                "Cache-Control": "max-age=0",
                                "Content-Type": multipart_data.content_type,
                                "Origin": "https://"+self.__domain,
                                "Referer": "https://"+self.__domain+"/accounts/blog",
                                "Upgrade-Insecure-Requests": "1",
                                "User-Agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"
                            })
                            if upload_xml_req.status_code == 200 :
                                spinner_upload.stop()
                                logging.info("Upload {xml_file} untuk {blog_title}".format(xml_file=xml_file_name,blog_title=row["blog_title"]))
                                df_new.at[index, 'xml'] = xml_file_name
                                counter += 1

                                if int(counter) != int(all_blog) :
                                    df_new.to_csv("blogs.csv",index=True)
                                    print("Upload berhasil {counter} / {all_blog} ".format(counter=counter,all_blog=all_blog))
                                else :
                                    print("ALL DONE")
                                    df_new.to_csv("blogs.csv",index=True)
                                    return True
                    else :
                        spinner_upload.stop()
                        print("Gagal mendapatkan ID blog")
                        pass
                else :
                    spinner_upload.stop()
                    print("XML yang tersedia tidak cukup untuk semua blog")
                    df_new.to_csv("blogs.csv",index=True)
                    return True
        else :
            print("Topik tidak ditemukan")
            return False

parser = argparse.ArgumentParser(description='Bot untuk upload file xml ke Blogtivity')
parser.add_argument("--topik", help="Topik yang dicari, pastikan ada folder dengan nama topik yang sama di folder xmls", default="")
upass = open("username.txt").read()
upass_split = upass.split("\n")
userid = upass_split[0].split(":")[1].strip()
pwd = upass_split[1].split(":")[1].strip()
domain = upass_split[2].split(":")[1].strip()
args = parser.parse_args()
a = BlogtivityUploadBot(userid,pwd,domain)
b = a.upload(cari=args.topik)