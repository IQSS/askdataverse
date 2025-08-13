""" MIT License

Copyright (c) 2023-2024 Institute for Quantitative Social Science, Stefano M. Iacus

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
 """

# requirements.txt
# python=3.10
# Jinja2
# langchain
# langchain_openai
# openai
# shiny>=0.4
# pandas
### the following ones only for statistical analysis
# statsmodels
# seaborn
# matplotlib
# tabulate

# This code, my first python code, was created in a night. Be merciful.

# This script requires two arguments: `fileId` and `siteUrl`. 
# Note: The url arguments are case sensitive.
# The parameter `datasetPid` is collected but not yet used
# for Harvard Dataverse siteUrl always equals to https://dataverse.harvard.edu
# fileId is the internal identifier in the Dataverse database
# example of use:
# https://askdataverse.shinyapps.io/askthedata/?fileId=4862482&siteUrl=https://dataverse.harvard.edu
# or, if run locally
# http://localhost:64504/?fileId=4862482&siteUrl=https://dataverse.harvard.edu
# replace 64504 with your port

# AskTheData

from shiny import  App, reactive, render, ui
import asyncio
import re
from pathlib import Path
import pandas as pd
import requests   # for urls 
import io
import os
from htmltools import HTML, div
import string
import random
import csv, io

from urllib.request import urlopen
import json
import urllib.parse
from urllib.parse import urlparse, parse_qs

from langchain_openai import ChatOpenAI
from langchain_experimental.agents import create_pandas_dataframe_agent


mypath = "./"
os.chdir(mypath)

# put your OPENAI_API_KEY in the key.json file in the form
# {"OPENAI_API_KEY" :"xxxxx"}
# unfortunately it is not possible to pass environmental variables
# to shinyapss.io

tmp = json.load(open("key.json"))

OPENAI_API_KEY = tmp['OPENAI_API_KEY']

# We use OpenAI `text-davinci-003` but it can be changed with other models supported by LangChain
#myllm = llm=OpenAI(temperature=0,openai_api_key=OPENAI_API_KEY, model_name = "text-davinci-003")

# 2024-01-04: text-davinci-003 deprecated on Jan 4th, 2024, we now use gpt-3.5-turbo
# 2024-03-30: switched from SQL to pandas agents

#myllm = ChatOpenAI(temperature=0,openai_api_key=OPENAI_API_KEY,model_name="gpt-3.5-turbo") 
myllm = ChatOpenAI(temperature=0,openai_api_key=OPENAI_API_KEY,model_name="gpt-4o-mini") 

# these variables must remain global
apiStr = '/api/access/datafile/'
fileid = ""
dataset_pid = ""
dataurl = ""
siteUrl = ""

# we now support more tabular data... in principle
def _is_xlsx(raw: bytes) -> bool:
    # XLSX files are ZIPs
    return raw.startswith(b"PK\x03\x04")
def _is_xls(raw: bytes) -> bool:
    # Legacy Excel OLE header
    return raw.startswith(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1")
def _maybe_text(raw: bytes) -> str | None:
    for enc in ("utf-8", "latin1"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return None

def app_ui(request):
    global fileid
    global dataset_pid
    global dataurl
    global apiStr
    

    fileid = request.query_params.get('fileId')
    dataset_pid = request.query_params.get('datasetPid')
    siteUrl = request.query_params.get('siteUrl')
    if fileid is None:
        fileid = ''
    if siteUrl is None:
        siteUrl = ''
    dataurl = siteUrl + apiStr + fileid
    
    _ui = ui.page_fluid(
        ui.input_text_area("query", "Tell me what you want to know", placeholder="What is this data about?"),
        ui.input_action_button("think", "Answer please", class_="btn-primary"),
        ui.output_text("answer"),
        ui.output_data_frame("grid")
    )
    return _ui

# some variables need to leave within server() so they remain local to the user session
# otherwise two users may load different data that overlaps in the shiny session

def server(input, output, session):
    HaveData = reactive.Value(None)
    HaveQuery = reactive.Value(None)
    sqlDB = reactive.Value(None)
    mydf = reactive.Value(None)

    @reactive.Calc
    async def load_tabular_data():
        print("Loading data")
        HaveData.set(False)
        ui.notification_show("Loading data...", id="loadingID", duration=None, type="warning")
        resp = requests.get(dataurl, timeout=60)
        resp.raise_for_status()
        raw = resp.content
        ctype = (resp.headers.get("Content-Type") or "").lower()
        def done(df: pd.DataFrame):
            mydf.set(df)
            HaveData.set(True)
            ui.notification_remove("loadingID")
            return df
        try:
            # 1) Byte sniff for Excel regardless of extension/ctype
            if _is_xlsx(raw):
                df = pd.read_excel(io.BytesIO(raw))  # needs openpyxl
                return done(df)
            if _is_xls(raw): # needs xlrd (<2.0) installed; pandas will pick engine if available
                df = pd.read_excel(io.BytesIO(raw))
                return done(df)
            # 2) If content-type says Excel, still try read_excel
            if "excel" in ctype or "spreadsheetml" in ctype:
                df = pd.read_excel(io.BytesIO(raw))
                return done(df)
            # 3) Try text-based formats (JSON or CSV/TSV)
            text = _maybe_text(raw)
            if text is not None:
                stripped = text.lstrip()
                # JSON?
                if stripped.startswith("{") or stripped.startswith("[") or "json" in ctype:
                    df = pd.read_json(io.StringIO(text))
                    # If it’s a list of records, this yields a DataFrame; if it’s a dict, normalize:
                    if isinstance(df, pd.Series) or df.empty:
                        try:
                            j = json.loads(text)
                            df = pd.json_normalize(j) if not isinstance(j, list) else pd.DataFrame(j)
                        except Exception:
                            pass
                    return done(df)
                # CSV/TSV with multiple guesses
                for sep in (None, ",", "\t", ";", "|"):
                    try:
                        df = pd.read_csv(
                            io.StringIO(text),
                            sep=sep,             # None => sniff
                            engine="python",
                            on_bad_lines="skip",
                            quoting=csv.QUOTE_MINIMAL,
                        )
                        if not df.empty:
                            return done(df)
                    except Exception:
                        continue
            # 4) If we got here, we couldn’t parse
            ui.notification_remove("loadingID")
            raise ValueError("Unsupported or malformed file; could not parse as Excel/JSON/CSV.")
        except Exception as e:
            ui.notification_remove("loadingID")
            raise RuntimeError(f"Failed to load file: {e}")
   
    @output
    @render.data_frame
    async def grid():
        data = await load_tabular_data()
        return render.DataGrid(data,height=350,width="fit-content")

    @output
    @render.text
    async def answer():
        input.think()
        with reactive.isolate():
            if not HaveData.get():
                return "Waiting for data..."
            this_query = input.query() if HaveQuery.get() else "What is this data about?"
            HaveQuery.set(True)
            ui.notification_show("Thinking...", id='thinkingID', duration=None)
            agent_executor = create_pandas_dataframe_agent(
                myllm, mydf.get(),
                agent_type="openai-tools",
                verbose=True,
                allow_dangerous_code=True
            )
            # LangChain versions differ: sometimes returns str, sometimes {"output": ...}
            try:
                res = agent_executor.invoke({"input": this_query})
            except TypeError:
                # Older/newer API compatibility
                res = agent_executor.invoke(this_query)
            ui.notification_remove('thinkingID')
            if isinstance(res, dict):
                return str(res.get("output", res.get("final_answer", "")))
            return str(res)

    # async def answer():
    #     input.think()
    #     with reactive.isolate():
    #         ans = "Waiting for you..."
    #         if(HaveData.get()):
    #             if HaveQuery.get():
    #                 this_query = input.query()
    #             else:
    #                 this_query = 'What is this data about?' # default initial query
    #                 HaveQuery.set(True)    # we need this here
    #             ui.notification_show("Thinking...", id='thinkingID', duration=None)    
    #             agent_executor = create_pandas_dataframe_agent(myllm, mydf.get(), agent_type="openai-tools", 
    #                                                            verbose=True, allow_dangerous_code=True)
    #             ans = agent_executor.invoke(f"{this_query}")
    #             ui.notification_remove('thinkingID')    
    #     return f"{ans['output']}"    
        
app = App(app_ui, server)

