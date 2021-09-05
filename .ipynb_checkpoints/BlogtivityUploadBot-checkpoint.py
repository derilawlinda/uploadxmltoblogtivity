#!/usr/bin/env python3

import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import pandas as pd
from bs4 import BeautifulSoup
import os
import argparse

class BlogtivityUploadBot :
    def __init__(self,userid,pwd):
        self.__userid = userid
        self.__pwd = pwd

    def __confirm_prompt(self,question: str) -> bool:
        reply = None
        while reply not in ("", "y", "n"):
            reply = input(f"{question} (Y/n): ").lower()
        return (reply in ("", "y"))
    
    def upload(self,cari) :
        api = "https://daryna.blogtivity.id/log/login"
        body = "username="+self.__userid+"&password="+self.__pwd
        with requests.Session() as s:
            print("Logging in to blogtivitiy..")
            req = s.get("https://daryna.blogtivity.id/log/")
            cookie = {'PHPSESSID': req.cookies['PHPSESSID']}
            r = s.post(api, data=body, cookies=cookie,headers={
            "Host": "daryna.blogtivity.id",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7,af;q=0.6,ms;q=0.5",
            "Cache-Control": "max-age=0",
            "Content-Length": str(len(body)),
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://daryna.blogtivity.id",
            "Referer": "https://daryna.blogtivity.id/log/index/status/EhjT1YDERZ5gxbLl5pYoMwgQY2kEtwW4M1RBRWJ0SnlzQkRGT2JvRVMxSGJsQT09nw8WiR3yjLWv4UZ5iTJ7E1cDqQCYjUGG",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"
            })
            if "Blogtivity Admin | Dashboard" in r.text:
                print("Logged in")
                print("Cek untuk data baru..")
                blogs = s.get("https://daryna.blogtivity.id/accounts/blog",cookies=cookie)
                soup = BeautifulSoup(blogs.text, "html.parser")
                rows = soup.find_all('form')[0].find("select").find_all("option")
                df_new = pd.DataFrame()  
                for row in rows:
                    if row["value"] != ""  :
                        new_row = {
                            "id" : row["value"],
                            "blog_title" : row.text.split("-")[0].strip(),
                            "blog_url" : row.text.split("-")[1].split("(")[0].strip(),
                            "xml" : None
                        }
                        df_new = df_new.append(new_row, ignore_index=True)
                if os.path.isfile("blogs.csv") :
                    df_old = pd.read_csv("blogs.csv")
                    if not df_new.equals(df_old) :
                        df_diff = (len(df_new) - len(df_old))
                        if df_diff > 0:
                            print("Penambahan {df_diff} blog".format(df_diff = df_diff))
                        elif df_diff < 0:
                            print("Pengurangan {df_diff} blog".format(df_diff))
                        else :
                            print("Sinkronisasi data baru dan lama..")
                        df_new = df_new.combine_first(df_old)
                df_new.to_csv("blogs.csv",index=False)
                        
                if cari != "" :
                    df_filtered = df_new[df_new['blog_title'].str.contains(cari,case=False)]
                    df_filtered = df_filtered[df_filtered.xml.notnull()]
                    df_filtered.sort_values(by=['blog_title'])
                    self.__uploadToBlogtivity(cari,df_filtered=df_filtered,df_new = df_new,s=s,cookie=cookie)
                        
                else :
                    
                    reply = self.__confirm_prompt("Akan mengupload semua file xml di dalam folder xmls ke seluruh blog ? ")
                    if reply :
                        df_filtered = df_new
                        df_filtered = df_filtered[df_filtered.xml.notnull()]
                        df_filtered.sort_values(by=['blog_title'])
                        self.__uploadToBlogtivity(cari="",df_filtered = df_filtered,df_new = df_new,s=s,cookie=cookie)
                    else :
                        cari = input('Ketik kategori : ')
                        df_filtered = df_new[df_new['blog_title'].str.contains(cari,case=False)]
                        df_filtered = df_filtered[df_filtered.xml.notnull()]
                        df_filtered.sort_values(by=['blog_title'])
                        self.__uploadToBlogtivity(cari="",df_filtered=df_filtered,df_new = df_new,s=s,cookie=cookie)
    
    
                    
    def __uploadToBlogtivity(self,cari,df_filtered,df_new,s,cookie) :
        
        df_filtered = df_filtered
        
        if cari != "" :
            if not os.path.isdir("xmls/"+cari) :
                print("Tidak ada folder {0} di dalam folder xmls".format(cari))
                return False
        
        xml_in_dir = os.listdir("xmls/"+cari)
        xml_assigned = df_new[df_new.xml.notnull()]["xml"].to_list()
       
        print(xml_assigned)
#         for xml in xml_in_dir:
#             for i in range(len(cleaned_xml_assigned)):
#                 if xml in cleaned_xml_assigned[i]:
#                     available_xmls.append(xml)
#                 else: pass
#         print(available_xmls)
        # counter = 0
        # all_blog = len(df_filtered)
        # for index, row in df_filtered.iterrows():
        #     if 0 <= counter < len(available):
        #         xml_file_name = available[counter]
        #         print("Upload {xml_file} untuk {blog_title}".format(xml_file=xml_file_name,blog_title=row["blog_name"]))
        #         multipart_data = MultipartEncoder(
        #             fields={
        #                     'fileisi' : (xml_file_name, open('xmls/'+xml_file_name,'rb')),
        #                     'blogs': row["id"], 
        #                     'randomize': 'Y',
        #                     'parser' : 'xml_shuriken',
        #                     'status' : 'connect'
        #             }
        #         )
        #         upload_api = "https://daryna.blogtivity.id/posts/setimport"
        #         upload_xml_req = s.post(upload_api,data=multipart_data,cookies=cookie,headers={
        #             "Host": "daryna.blogtivity.id",
        #             "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        #             "Accept-Encoding": "gzip, deflate, br",
        #             "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7,af;q=0.6,ms;q=0.5",
        #             "Cache-Control": "max-age=0",
        #             "Content-Type": multipart_data.content_type,
        #             "Origin": "https://daryna.blogtivity.id",
        #             "Referer": "https://daryna.blogtivity.id/accounts/blog",
        #             "Upgrade-Insecure-Requests": "1",
        #             "User-Agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"
        #             })
        #         if upload_xml_req.status_code == 200 :
        #             sing_res = df_new.loc[df_new['id'] == row["id"]]
        #             index = sing_res.index[0]
        #             df_new.at[index, 'xml'] = xml_file_name
        #             df_new.to_csv("blogs.csv")
        #             if counter != all_blog :
        #                 counter += 1
        #                 print("Upload berhasil {counter} / {all_blog} ".format(counter=counter,all_blog=all_blog))
        #             else :
        #                 print("ALL DONE")
        #                 return True
        #     else :
        #         print("XML yang tersedia tidak cukup untuk semua blog")
        #         return True
                    
                
               
                
parser = argparse.ArgumentParser(description='Bot untuk upload file xml ke Blogtivity')
parser.add_argument("--topik", help="Topik yang dicari, pastikan ada folder dengan nama topik yang sama di folder xmls", default="")
upass = open("username.txt").read()
upass_split = upass.split("\n")
userid = upass_split[0].split(":")[1].strip()
pwd = upass_split[1].split(":")[1].strip()
args = parser.parse_args()
a = BlogtivityUploadBot(userid,pwd)
b = a.upload(cari=args.topik)  


    
    
        
    