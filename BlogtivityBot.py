#!/usr/bin/env python3

from numpy.core.numeric import NaN
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import pandas as pd
from bs4 import BeautifulSoup
from halo import Halo
import logging
from tenacity import retry, stop_after_attempt
import datetime
from datetime import date
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import multiprocessing as mp
from multiprocessing import Pool, RLock, cpu_count, freeze_support
from tqdm.auto import tqdm, trange
from functools import partial
from tqdm.contrib.concurrent import process_map,thread_map
from lxml import html

def strip_html(string):
    stripped = html.fromstring(string)
    return stripped.text_content().strip()

def get_blog_url(string):
    stripped = html.fromstring(string)
    return stripped.get('href')


class BlogtivityUploadBot :
    def __init__(self,userid,pwd,domain,retry_in_minute,logged_in):
        self.__userid = userid
        self.__pwd = pwd
        self.__domain = domain
        self.__retry_in_minute = retry_in_minute
        self.__logged_in = logged_in
        self.__blog_data = pd.DataFrame()
        logging.basicConfig(filename='delete_blog.log', level=logging.INFO,format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S')

    def __confirm_prompt(self,question: str) -> bool:
        reply = None
        while reply not in ("", "1", "2","3"):
            reply = input(f"{question} ").lower()
            if(reply == "") :
                reply = "1"
        return reply

    def __yesnoconfirm_prompt(self,question: str) -> bool:
        reply = None
        while reply not in ("", "y", "n"):
            reply = input(f"{question} (Y/n): ").lower()
        return (reply in ("", "y"))

    def __delete_how_many(self,question: str) -> bool:
        reply = None
        while reply not in ("", "1", "2"):
            reply = input(f"{question} ").lower()
            if(reply == "") :
                reply = "1"
        return reply

    def choose_bot(self) :
        question = """ Pilih bot yang akan digunakan :
        1. Bot Delete blog 
        2. Bot Data Blog
        3. Bot Data Indexing
        Pilih bot yang akan digunakan (default : 1) : """
        bot = self.__confirm_prompt(question)
        return bot

    def choose_delete_bot(self) :
        question = """ Pilih Delete Blog yang akan digunakan :
        1. Success Post = 0, Failed Post > 0
        2. Success Post = 0, Failed Post = 0
        3. Failed Post > Success Post
        Pilih delete bot yang akan digunakan (default : 1) : """
        bot = self.__confirm_prompt(question)
        return bot
    
    def choose_and_run_bot (self) :
        bot = self.choose_bot()
        if bot :
            if bot == '1':
                delete_bot = self.choose_delete_bot()
                if delete_bot == "1" :
                    print ("Menjalankan bot untuk menghapus blog dengan Success Post = 0, Failed Post > 0")
                elif delete_bot == "2" :
                    print ("Menjalankan bot untuk menghapus blog dengan Success Post = 0, Failed Post = 0")
                elif delete_bot == "3" :
                    print ("Menjalankan bot untuk menghapus blog dengan Failed Post > Success Post")
                self.__delete_blogs(delete_query = delete_bot)
            elif bot == "2" :
                if __name__ == '__main__':
                    self.__get_blogs_data()
            elif bot == "3" :
                self.__get_index_data()


    
    
    
    def __delete_blogs(self,delete_query) :
        
        if self.__logged_in["status"] :
            cookie = self.__logged_in["cookie"]
            print("Mengambil data terbaru..")
            with requests.Session() as s:
                blogs = s.get("https://"+self.__domain+"/accounts/blog",cookies=cookie)
                soup = BeautifulSoup(blogs.text, "html.parser")
                rows = soup.find_all('table')[0].find_all("tr")
                df_all = pd.DataFrame()  
                for row in rows:
                    cells = row.find_all('td')
                    if(len(cells) > 0):
                        date_added = cells[6].text
                        tbb_id = cells[7].find('a')["href"].split("_")[1]
                        new_row = {
                            "id" : (pd.to_datetime(date_added) - pd.Timestamp("1970-01-01")) // pd.Timedelta('1s'),
                            "blog_title" : cells[2].text,
                            "success_post" : int(cells[3].text),
                            "failed_post" : int(cells[4].text),
                            "tbb_id" : tbb_id
                        }
                        df_all = df_all.append(new_row, ignore_index=True)

                if delete_query == "1" :
                    df_delete_blog = df_all[(df_all["success_post"] == 0) & (df_all["failed_post"] > 0)]
                    df_delete_blog = df_delete_blog.sort_values(by=['failed_post'],ascending=False)
                elif delete_query == "2" :
                    df_delete_blog = df_all[(df_all["success_post"] == 0) & (df_all["failed_post"] == 0)]
                elif delete_query == "3" :
                    df_delete_blog = df_all[(df_all["failed_post"] > df_all["success_post"])]
                
                total_delete_blog = len(df_delete_blog)
                if total_delete_blog > 0 :

                    confirm_delete = self.__delete_how_many("""Akan menghapus {0} blogs, lanjutkan ? 
                    1.  Hapus Semua
                    2.  Hapus Jumlah Tertentu
                    Pilih mode penghapusan blog : """.format(len(df_delete_blog)))
                    jumlah_delete = 0
                    if confirm_delete == "2" :
                        jumlah_delete = input('Berapa yang akan dihapus ?  ')
                        jumlah_delete = int(jumlah_delete)
                        while jumlah_delete > total_delete_blog :
                            jumlah_delete = input("Jumlah yang dihapus harus lebih sedikit dari {0}, masukan angka lain : ".format(total_delete_blog))
                            jumlah_delete = int(jumlah_delete)
                        df_delete_blog = df_delete_blog.head(jumlah_delete)

                    if confirm_delete :
                        counter = 0
                        deletion_progress = Halo(text="Mulai menghapus..", spinner='dots')
                        deletion_progress.start()
                        for index, row in df_delete_blog.iterrows():
                        
                            delete_id = row["tbb_id"]
                            delete_req_code = self.__delete_a_blog(delete_id,s,cookie)
                            if delete_req_code == 200 :
                                logging.info("Deleted {blog_title}".format(blog_title=row["blog_title"]))
                                counter += 1

                                if confirm_delete == "2" :
                                    if counter == len(df_delete_blog) :
                                        deletion_progress.stop()
                                        sisa = total_delete_blog - len(df_delete_blog)
                                        print("Deleted {0} blog, sisa {1}".format(jumlah_delete,sisa))
                                        logging.info("Deleted {0} blog, sisa {1}".format(jumlah_delete,sisa))
                                    else :
                                        total_delete_blog_partial = len(df_delete_blog)
                                        deletion_progress.text = "Deleted {0} (  {1} / {2} deleted )".format(row["blog_title"],counter,total_delete_blog_partial )
                                else :
                                    if counter == total_delete_blog :
                                        deletion_progress.stop()
                                        print("Blog sudah terhapus")
                                    else :
                                        deletion_progress.text = "Deleted {0} (  {1} / {2} deleted )".format(row["blog_title"],counter,total_delete_blog )
                            else :
                                raise Exception('Request tidak berhasil')
                                    
                                
                    else :
                        self.choose_and_run_bot()
                else :
                    print("Tidak ada data yang bisa dihapus")
                    back_to_main_menu = self.__yesnoconfirm_prompt("Kembali ke menu awal ? ")
                    if back_to_main_menu :
                        self.choose_and_run_bot()
                    else :
                        return True

    @retry
    def __delete_a_blog(self,delete_id,s,cookie) :
        coba_ulang_spinner = Halo(text="Request gagal, mencoba ulang..")
        body = "tbb_id="+delete_id
        delete_api = "https://"+self.__domain+"/accounts/deleteblogs"
        with requests.Session() as s2:
            delete_req = s2.post(delete_api,data = {'tbb_id':delete_id},cookies=cookie,headers={
                "Host": self.__domain,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7,af;q=0.6,ms;q=0.5",
                "Cache-Control": "max-age=0",
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": str(len(body)),
                "Origin": "https://"+self.__domain,
                "Referer": "https://"+self.__domain+"/accounts/blog",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"
            })
            if delete_req.status_code != 200 :
                delete_req.raise_for_status()
                coba_ulang_spinner.start()
                raise Exception('Request tidak berhasil')
            else :
                coba_ulang_spinner.stop()
                return delete_req.status_code
        
    def __get_blogs_data(self) :
        cookie = self.__logged_in["cookie"]
        today_date = date.today().strftime("%Y%m%d")
        print("Memulai pengambilan data blog...")
        with requests.Session() as s:
            retries = Retry(total=5,
                        backoff_factor=0.3,
                        status_forcelist=[ 500, 502, 503, 504 ])

            s.mount('https://', HTTPAdapter(max_retries=retries))
            blogs = s.get("https://"+self.__domain+"/accounts/blog",cookies=cookie)
            soup = BeautifulSoup(blogs.text, "html.parser")
            rows = soup.find_all('table')[0].find_all("tr")
            # option_rows = soup.find_all("form")[0].find('select').find_all('option')
            # df_table = pd.DataFrame()
            # df_option = pd.DataFrame()
            # url_is_null_list = []

            # for row in rows:
            #     cells = row.find_all('td')
            #     if(len(cells) > 0):
            #         blog_data_url = cells[2].find('a')['href']
            #         date_added = cells[6].text
            #         id = (pd.to_datetime(date_added) - pd.Timestamp("1970-01-01")) // pd.Timedelta('1s')
            #         new_row = {
            #             "blog_name" : cells[2].text,
            #             "success_post" : int(cells[3].text),
            #             "failed_post" : int(cells[4].text),
            #             "scheduled_post" : int(cells[5].text),
            #             "blog_data_url" : blog_data_url
            #         }
            #         df_table = df_table.append(new_row, ignore_index=True)

            body = "draw=0&columns%5B0%5D%5Bdata%5D=no&columns%5B0%5D%5Bname%5D=&columns%5B0%5D%5Bsearchable%5D=true&columns%5B0%5D%5Borderable%5D=true&columns%5B0%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B0%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B1%5D%5Bdata%5D=account&columns%5B1%5D%5Bname%5D=&columns%5B1%5D%5Bsearchable%5D=true&columns%5B1%5D%5Borderable%5D=true&columns%5B1%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B1%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B2%5D%5Bdata%5D=blog&columns%5B2%5D%5Bname%5D=&columns%5B2%5D%5Bsearchable%5D=true&columns%5B2%5D%5Borderable%5D=true&columns%5B2%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B2%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B3%5D%5Bdata%5D=success&columns%5B3%5D%5Bname%5D=&columns%5B3%5D%5Bsearchable%5D=true&columns%5B3%5D%5Borderable%5D=true&columns%5B3%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B3%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B4%5D%5Bdata%5D=failed&columns%5B4%5D%5Bname%5D=&columns%5B4%5D%5Bsearchable%5D=true&columns%5B4%5D%5Borderable%5D=true&columns%5B4%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B4%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B5%5D%5Bdata%5D=schedule&columns%5B5%5D%5Bname%5D=&columns%5B5%5D%5Bsearchable%5D=true&columns%5B5%5D%5Borderable%5D=true&columns%5B5%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B5%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B6%5D%5Bdata%5D=create&columns%5B6%5D%5Bname%5D=&columns%5B6%5D%5Bsearchable%5D=true&columns%5B6%5D%5Borderable%5D=true&columns%5B6%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B6%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B7%5D%5Bdata%5D=remove&columns%5B7%5D%5Bname%5D=&columns%5B7%5D%5Bsearchable%5D=true&columns%5B7%5D%5Borderable%5D=true&columns%5B7%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B7%5D%5Bsearch%5D%5Bregex%5D=false&order%5B0%5D%5Bcolumn%5D=0&order%5B0%5D%5Bdir%5D=asc&start=0&length=999999&search%5Bvalue%5D=&search%5Bregex%5D=false"
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
                df_new = df_new.set_index("id")"
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
            for option_row in option_rows :
                if option_row["value"] != "" :
                    option_blog_name = option_row.text.split(" - ")[0].strip()
                    option_blog_url = option_row.text.split(" - ")[1].split("(")[0].strip()
                    new_option_row = {
                        "blog_name" : option_blog_name,
                        "blog_url" : option_blog_url
                    }
                    df_option = df_option.append(new_option_row, ignore_index=True)

            print("Mengisi data yang kosong..")
            for index,row in df_table.iterrows() :
                query = df_option[df_option["blog_name"] == row["blog_name"]]
                if len(query) :
                    option_index = df_option[df_option["blog_name"] == row["blog_name"]].head(1).index[0]
                    blog_url = df_option.loc[option_index]["blog_url"]
                    df_table.loc[index,"blog_url"] = blog_url
                else :
                    df_table.loc[index,"blog_url"] = "-"
                    d = {
                        "index" : index,
                        "blog_data_url" : row["blog_data_url"]
                    }
                    url_is_null_list.append(d)
            if len(url_is_null_list) > 0 :
                if __name__ == "__main__":
                    freeze_support()  # for Windows support
                    results = process_map(self.get_blogs_data_by_row, url_is_null_list,chunksize=1)
                    if len(results) > 0 :
                        for r in results :
                            df_table.loc[r["index"],"blog_url"] = str(r["blog_url"])
                    df_table = df_table.drop(['blog_data_url'], axis=1)
            df_table.to_excel(today_date+"blogs.xlsx",index=False)
            print("ALL DONE, cek file : "+today_date+"blogs.xlsx")

    def get_blogs_data_by_row(self,rows) :

        cookie = self.__logged_in["cookie"]
        index = rows["index"]
        with requests.Session() as s:
                retries = Retry(total=5,
                            backoff_factor=0.3,
                            status_forcelist=[ 500, 502, 503, 504 ])

                s.mount('https://', HTTPAdapter(max_retries=retries))
                blog_page = s.get(rows["blog_data_url"],cookies=cookie)
                if blog_page.status_code == 200 :
                    blog_page_soup = BeautifulSoup(blog_page.text, "html.parser")
                    row_class = blog_page_soup.find_all("div", {"class": "row"})
                    blog_url = row_class[0].find('h6').text
                    return {"index" : index, "blog_url" : blog_url}

                    
    def __get_index_data(self) :
        indexing_spinner = Halo(text="Akan memakan waktu cukup lama, nikmati secangkir kopi..")
        indexing_spinner.start()
        cookie = self.__logged_in["cookie"]
        today_date = date.today().strftime("%Y%m%d")
        with requests.Session() as s:
            retry_in_sec = int(self.__retry_in_minute)*60
            retries = Retry(total=5,
                        backoff_factor=retry_in_sec,
                        status_forcelist=[ 500, 502, 503, 504 ])

            s.mount('https://', HTTPAdapter(max_retries=retries))
            body = 'draw=1&columns%5B0%5D%5Bdata%5D=no&columns%5B0%5D%5Bname%5D=&columns%5B0%5D%5Bsearchable%5D=true&columns%5B0%5D%5Borderable%5D=true&columns%5B0%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B0%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B1%5D%5Bdata%5D=blog&columns%5B1%5D%5Bname%5D=&columns%5B1%5D%5Bsearchable%5D=true&columns%5B1%5D%5Borderable%5D=true&columns%5B1%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B1%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B2%5D%5Bdata%5D=url&columns%5B2%5D%5Bname%5D=&columns%5B2%5D%5Bsearchable%5D=true&columns%5B2%5D%5Borderable%5D=true&columns%5B2%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B2%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B3%5D%5Bdata%5D=status&columns%5B3%5D%5Bname%5D=&columns%5B3%5D%5Bsearchable%5D=true&columns%5B3%5D%5Borderable%5D=true&columns%5B3%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B3%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B4%5D%5Bdata%5D=method&columns%5B4%5D%5Bname%5D=&columns%5B4%5D%5Bsearchable%5D=true&columns%5B4%5D%5Borderable%5D=true&columns%5B4%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B4%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B5%5D%5Bdata%5D=date&columns%5B5%5D%5Bname%5D=&columns%5B5%5D%5Bsearchable%5D=true&columns%5B5%5D%5Borderable%5D=true&columns%5B5%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B5%5D%5Bsearch%5D%5Bregex%5D=false&order%5B0%5D%5Bcolumn%5D=0&order%5B0%5D%5Bdir%5D=asc&start=0&length=999999&search%5Bvalue%5D=&search%5Bregex%5D=false'
            # indexes = s.get("https://"+self.__domain+"/indexing/google",cookies=cookie)
            indexes = s.post("https://"+self.__domain+"/fordata/indexing/userid/1",data=body,cookies=cookie,headers={
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

            df = pd.read_json(indexes.text)
            df2 = pd.json_normalize(df['data'])
            if(df2.shape[0] == 0) :
                print("Tidak ada data indexing")
                return False
            df_all = pd.DataFrame()
             
            df_all["id"] = df2["date"].apply(lambda x: (pd.to_datetime(x) - pd.Timestamp("1970-01-01")).total_seconds())
            df_all["blog_title"] = df2["blog"].apply(strip_html)
            df_all["blog_url"] = df2["blog"].apply(get_blog_url)
            df_all["status"] = df2["status"]
            df_all["date"] = df2["date"]
            
            df_status_failed = df_all[df_all["status"] == "Failed"]
            if len(df_status_failed) > 0 :
                last_week_date = (pd.to_datetime((datetime.date.today() - datetime.timedelta(days=7))) - pd.Timestamp("1970-01-01")).total_seconds()
                df_export = df_status_failed[df_status_failed["id"] > last_week_date]
                df_export.to_excel(today_date+"google_indexing.xlsx",index=False)
                indexing_spinner.stop()
                print("Silahkan cek file : "+today_date+"google_indexing.xlsx")
                return True
            else :
                print("Tidak ada indexing yang Failed")
                return True

    

def login() :
        upass = open("username.txt").read()
        upass_split = upass.split("\n")
        userid = upass_split[0].split(":")[1].strip()
        pwd = upass_split[1].split(":")[1].strip()
        domain = upass_split[2].split(":")[1].strip()
        cookie = {}
        api = "https://"+domain+"/log/login"
        body = "username="+userid+"&password="+pwd
        with requests.Session() as s:
            print("Logging in to blogtivity..")
            req = s.get("https://"+domain+"/log/")
            cookie = {'PHPSESSID': req.cookies['PHPSESSID']}
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
                cookie_str = cookie['PHPSESSID']
                f = open("cookies.txt", 'w')
                f.write(cookie_str)
                f.close()
                return {"status" : True, 
                "cookie" : cookie}
            else :
                 return {"status" : False, 
                "cookie" : cookie}
    



if __name__ == "__main__":  
    upass = open("username.txt").read()
    upass_split = upass.split("\n")
    userid = upass_split[0].split(":")[1].strip()
    pwd = upass_split[1].split(":")[1].strip()
    domain = upass_split[2].split(":")[1].strip()
    retry_in_minute = upass_split[3].split(":")[1].strip()
    logged_in = login()
    if logged_in["status"]:
        print("Logged in")
        cookie = logged_in["cookie"]
        a = BlogtivityUploadBot(userid,pwd,domain,retry_in_minute,logged_in)
        b = a.choose_and_run_bot()
    else :
        print("Gagal log in, coba kembali")
        pass
