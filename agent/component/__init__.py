#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import importlib
from .begin import Begin, BeginParam
from .generate import Generate, GenerateParam
from .retrieval import Retrieval, RetrievalParam
from .answer import Answer, AnswerParam
from .categorize import Categorize, CategorizeParam
from .switch import Switch, SwitchParam
from .relevant import Relevant, RelevantParam
from .message import Message, MessageParam
from .rewrite import RewriteQuestion, RewriteQuestionParam
from .keyword import KeywordExtract, KeywordExtractParam
from .concentrator import Concentrator, ConcentratorParam
from .baidu import Baidu, BaiduParam
from .duckduckgo import DuckDuckGo, DuckDuckGoParam
# from .wikipedia import Wikipedia, WikipediaParam # Removed
# from .pubmed import PubMed, PubMedParam # Removed
# from .arxiv import ArXiv, ArXivParam # Removed
from .google import Google, GoogleParam
from .bing import Bing, BingParam
from .googlescholar import GoogleScholar, GoogleScholarParam
# from .deepl import DeepL, DeepLParam # Removed
# from .github import GitHub, GitHubParam # Removed
# from .baidufanyi import BaiduFanyi, BaiduFanyiParam # Removed
# from .qweather import QWeather, QWeatherParam # Removed
# from .exesql import ExeSQL, ExeSQLParam # Already Removed
# from .yahoofinance import YahooFinance, YahooFinanceParam # Removed
# from .wencai import WenCai, WenCaiParam # Removed
# from .jin10 import Jin10, Jin10Param # Removed
# from .tushare import TuShare, TuShareParam # Removed
# from .akshare import AkShare, AkShareParam # Removed
# from .crawler import Crawler, CrawlerParam # Removed
# from .invoke import Invoke, InvokeParam # Removed
from .template import Template, TemplateParam
# from .email import Email, EmailParam # Removed
from .iteration import Iteration, IterationParam
from .iterationitem import IterationItem, IterationItemParam
# from .code import Code, CodeParam # Removed


def component_class(class_name):
    m = importlib.import_module("agent.component")
    c = getattr(m, class_name)
    return c


__all__ = [
    "Begin",
    "BeginParam",
    "Generate",
    "GenerateParam",
    "Retrieval",
    "RetrievalParam",
    "Answer",
    "AnswerParam",
    "Categorize",
    "CategorizeParam",
    "Switch",
    "SwitchParam",
    "Relevant",
    "RelevantParam",
    "Message",
    "MessageParam",
    "RewriteQuestion",
    "RewriteQuestionParam",
    "KeywordExtract",
    "KeywordExtractParam",
    "Concentrator",
    "ConcentratorParam",
    "Baidu",
    "BaiduParam",
    "DuckDuckGo",
    "DuckDuckGoParam",
    # "Wikipedia", # Removed
    # "WikipediaParam", # Removed
    # "PubMed", # Removed
    # "PubMedParam", # Removed
    # "ArXiv", # Removed
    # "ArXivParam", # Removed
    "Google",
    "GoogleParam",
    "Bing",
    "BingParam",
    "GoogleScholar",
    "GoogleScholarParam",
    # "DeepL", # Removed
    # "DeepLParam", # Removed
    # "GitHub", # Removed
    # "GitHubParam", # Removed
    # "BaiduFanyi", # Removed
    # "BaiduFanyiParam", # Removed
    # "QWeather", # Removed
    # "QWeatherParam", # Removed
    # "YahooFinance", # Removed
    # "YahooFinanceParam", # Removed
    # "WenCai", # Removed
    # "WenCaiParam", # Removed
    # "Jin10", # Removed
    # "Jin10Param", # Removed
    # "TuShare", # Removed
    # "TuShareParam", # Removed
    # "AkShare", # Removed
    # "AkShareParam", # Removed
    # "Crawler", # Removed
    # "CrawlerParam", # Removed
    # "Invoke", # Removed
    # "InvokeParam", # Removed
    "Iteration",
    "IterationParam",
    "IterationItem",
    "IterationItemParam",
    "Template",
    "TemplateParam",
    # "Email", # Removed
    # "EmailParam", # Removed
    # "Code", # Removed
    # "CodeParam", # Removed
    "component_class"
]
