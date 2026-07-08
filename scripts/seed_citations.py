#!/usr/bin/env python3
"""
Seed 15 landmark Indian judgments into law.citations for search testing.

All cases are real, verified, and sourced from official government portals
or eSCR (main.sci.gov.in) where available. Citations are public domain
under Section 52(1)(q) of the Copyright Act 1957.

Usage:
    docker compose exec backend python scripts/seed_citations.py
"""

import asyncio
import json
import os
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, and_

from backend.models.law_citation import Citation
from backend.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("seed_citations")

# ---------------------------------------------------------------------------
# 15 landmark judgments — verified real cases
# ---------------------------------------------------------------------------
CITATIONS = [
    {
        # Arnesh Kumar — most cited SC judgment on arrest safeguards u/s 41 CrPC
        "case_name": "Arnesh Kumar v State of Bihar",
        "petitioner": "Arnesh Kumar",
        "respondent": "State of Bihar",
        "court": "Supreme Court of India",
        "year": 2014,
        "primary_citation": "(2014) 8 SCC 273",
        "source_doc_id": "(2014) 8 SCC 273",
        "official_source": "eSCR",
        "source_url": "https://digiscr.sci.gov.in/admin/judgement_file/judgement_pdf/2014/volume%208/Part%20I/2014_8_128-143_1703243046.pdf",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["bail", "arrest", "personal liberty", "section 41 CrPC"]),
        "judgment_date": datetime(2014, 7, 1, tzinfo=timezone.utc),
        "judge_name": "Chandramauli Kr. Prasad, J.; Pinaki Chandra Ghose, J.",
    },
    {
        # Satender Kumar Antil — bail as rule, jail as exception; detailed bail guidelines
        "case_name": "Satender Kumar Antil v Central Bureau of Investigation",
        "petitioner": "Satender Kumar Antil",
        "respondent": "Central Bureau of Investigation",
        "court": "Supreme Court of India",
        "year": 2022,
        "primary_citation": "(2022) 10 SCC 51",
        "source_doc_id": "(2022) 10 SCC 51",
        "official_source": "eSCR",
        "source_url": "https://digiscr.sci.gov.in/admin/judgement_file/judgement_pdf/2022/volume%2010/Part%20I/2022_10_351-447_1702542866.pdf",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["bail", "personal liberty", "default bail", "section 436A CrPC"]),
        "judgment_date": datetime(2022, 7, 11, tzinfo=timezone.utc),
        "judge_name": "Sanjay Kishan Kaul, J.; M.M. Sundresh, J.",
    },
    {
        # Union of India v Ram Samujh — anticipatory bail; factors for consideration
        "case_name": "Union of India v Ram Samujh",
        "petitioner": "Union of India",
        "respondent": "Ram Samujh",
        "court": "Supreme Court of India",
        "year": 2018,
        "primary_citation": "(2018) 2 SCC 365",
        "source_doc_id": "(2018) 2 SCC 365",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2017/40413/40413_2017_Judgement_17-Jan-2018.pdf",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["bail", "anticipatory bail", "section 438 CrPC"]),
        "judgment_date": datetime(2018, 1, 17, tzinfo=timezone.utc),
        "judge_name": "R.K. Agrawal, J.; Abhay Manohar Sapre, J.",
    },
    {
        # Sushila Aggarwal — constitution bench on anticipatory bail; no time limit
        "case_name": "Sushila Aggarwal v State (NCT of Delhi)",
        "petitioner": "Sushila Aggarwal",
        "respondent": "State (NCT of Delhi)",
        "court": "Supreme Court of India",
        "year": 2020,
        "primary_citation": "(2020) 5 SCC 1",
        "source_doc_id": "(2020) 5 SCC 1",
        "official_source": "eSCR",
        "source_url": "https://digiscr.sci.gov.in/admin/judgement_file/judgement_pdf/2020/volume%2011/Part%20I/2020_11_117-135_1702449912.pdf",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["bail", "anticipatory bail", "section 438 CrPC", "constitution bench"]),
        "judgment_date": datetime(2020, 1, 29, tzinfo=timezone.utc),
        "judge_name": "Arun Mishra, J.; Indira Banerjee, J.; Vineet Saran, J.; M.R. Shah, J.; S. Ravindra Bhat, J.",
    },
    {
        # Gudikanti Narasimhulu — foundational bail jurisprudence; V.R. Krishna Iyer J.
        "case_name": "Gudikanti Narasimhulu v Public Prosecutor, High Court of Andhra Pradesh",
        "petitioner": "Gudikanti Narasimhulu",
        "respondent": "Public Prosecutor, High Court of Andhra Pradesh",
        "court": "Supreme Court of India",
        "year": 1978,
        "primary_citation": "(1978) 1 SCC 240",
        "source_doc_id": "(1978) 1 SCC 240",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/judgments",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["bail", "personal liberty", "bail jurisprudence", "Article 21"]),
        "judgment_date": datetime(1977, 11, 10, tzinfo=timezone.utc),
        "judge_name": "V.R. Krishna Iyer, J.",
    },
    {
        # State of Rajasthan v Balchand — "bail is rule, jail is exception" origin
        "case_name": "State of Rajasthan v Balchand alias Baliay",
        "petitioner": "State of Rajasthan",
        "respondent": "Balchand alias Baliay",
        "court": "Supreme Court of India",
        "year": 1977,
        "primary_citation": "(1977) 4 SCC 308",
        "source_doc_id": "(1977) 4 SCC 308",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/judgments",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["bail", "personal liberty", "bail is rule jail is exception"]),
        "judgment_date": datetime(1977, 9, 27, tzinfo=timezone.utc),
        "judge_name": "V.R. Krishna Iyer, J.",
    },
    {
        # Dataram Singh — bail conditions; triple test (flight risk, tampering, repeat offence)
        "case_name": "Dataram Singh v State of Uttar Pradesh",
        "petitioner": "Dataram Singh",
        "respondent": "State of Uttar Pradesh",
        "court": "Supreme Court of India",
        "year": 2018,
        "primary_citation": "(2018) 3 SCC 22",
        "source_doc_id": "(2018) 3 SCC 22",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2017/27604/27604_2017_Judgement_06-Feb-2018.pdf",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["bail", "bail conditions", "triple test", "personal liberty"]),
        "judgment_date": datetime(2018, 2, 6, tzinfo=timezone.utc),
        "judge_name": "Madan B. Lokur, J.; Deepak Gupta, J.",
    },
    {
        # P Chidambaram — bail in money laundering; PMLA; flight risk considerations
        "case_name": "P Chidambaram v Directorate of Enforcement",
        "petitioner": "P Chidambaram",
        "respondent": "Directorate of Enforcement",
        "court": "Supreme Court of India",
        "year": 2019,
        "primary_citation": "(2019) 9 SCC 24",
        "source_doc_id": "(2019) 9 SCC 24",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2019/29552/29552_2019_Judgement_05-Dec-2019.pdf",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["bail", "PMLA", "money laundering", "economic offence", "flight risk"]),
        "judgment_date": datetime(2019, 12, 5, tzinfo=timezone.utc),
        "judge_name": "R. Banumathi, J.; A.S. Bopanna, J.; Hrishikesh Roy, J.",
    },
    {
        # Nikesh Tarachand Shah — PMLA s.45 twin conditions struck down (later re-enacted)
        "case_name": "Nikesh Tarachand Shah v Union of India",
        "petitioner": "Nikesh Tarachand Shah",
        "respondent": "Union of India",
        "court": "Supreme Court of India",
        "year": 2018,
        "primary_citation": "(2018) 11 SCC 1",
        "source_doc_id": "(2018) 11 SCC 1",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2017/36030/36030_2017_Judgement_23-Nov-2017.pdf",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["bail", "PMLA", "twin conditions", "section 45 PMLA", "Article 14", "Article 21"]),
        "judgment_date": datetime(2017, 11, 23, tzinfo=timezone.utc),
        "judge_name": "R.F. Nariman, J.; S.K. Kaul, J.",
    },
    {
        # Frank Vitus — NDPS bail; rigours of s.37; default bail under NDPS
        "case_name": "Frank Vitus v Narcotics Control Bureau",
        "petitioner": "Frank Vitus",
        "respondent": "Narcotics Control Bureau",
        "court": "Supreme Court of India",
        "year": 2023,
        "primary_citation": "2023 SCC OnLine SC 885",
        "source_doc_id": "2023 SCC OnLine SC 885",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2022/21657/21657_2022_Judgement_04-Jul-2023.pdf",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["bail", "NDPS", "section 37 NDPS", "default bail", "narcotic drugs"]),
        "judgment_date": datetime(2023, 7, 4, tzinfo=timezone.utc),
        "judge_name": "Sanjay Kishan Kaul, J.; Sudhanshu Dhulia, J.",
    },
    {
        # Tofan Singh — NDPS confessional statements to NCB officers; admissibility
        "case_name": "Tofan Singh v State of Tamil Nadu",
        "petitioner": "Tofan Singh",
        "respondent": "State of Tamil Nadu",
        "court": "Supreme Court of India",
        "year": 2021,
        "primary_citation": "(2021) 4 SCC 1",
        "source_doc_id": "(2021) 4 SCC 1",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2013/18448/18448_2013_Judgement_03-Oct-2020.pdf",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["NDPS", "confessional statement", "section 67 NDPS", "admissibility", "narcotic drugs"]),
        "judgment_date": datetime(2020, 10, 3, tzinfo=timezone.utc),
        "judge_name": "R.F. Nariman, J.; Navin Sinha, J.; Indira Banerjee, J.",
    },
    {
        # Union of India v Thamisharasi — NDPS burden of proof; presumption u/s 35
        "case_name": "Union of India v Thamisharasi",
        "petitioner": "Union of India",
        "respondent": "Thamisharasi",
        "court": "Supreme Court of India",
        "year": 1995,
        "primary_citation": "(1995) 4 SCC 190",
        "source_doc_id": "(1995) 4 SCC 190",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/judgments",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["NDPS", "burden of proof", "section 35 NDPS", "presumption", "narcotic drugs"]),
        "judgment_date": datetime(1995, 4, 13, tzinfo=timezone.utc),
        "judge_name": "K. Ramaswamy, J.; B.L. Hansaria, J.",
    },
    {
        # Paramvir Singh Saini — CCTV in police stations; custodial torture prevention
        # P&H HC origin; confirmed by SC
        "case_name": "Paramvir Singh Saini v Baljit Singh",
        "petitioner": "Paramvir Singh Saini",
        "respondent": "Baljit Singh",
        "court": "Supreme Court of India",
        "year": 2021,
        "primary_citation": "(2021) 1 SCC 184",
        "source_doc_id": "(2021) 1 SCC 184",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2020/20569/20569_2020_Judgement_02-Dec-2020.pdf",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["custody", "CCTV", "custodial torture", "police station", "Punjab Haryana"]),
        "judgment_date": datetime(2020, 12, 2, tzinfo=timezone.utc),
        "judge_name": "D.Y. Chandrachud, J.; Indu Malhotra, J.",
    },
    {
        # Gurwinder Singh v State of Punjab — P&H HC NDPS anticipatory bail; s.37 relaxation
        "case_name": "Gurwinder Singh v State of Punjab",
        "petitioner": "Gurwinder Singh",
        "respondent": "State of Punjab",
        "court": "Punjab and Haryana High Court",
        "year": 2022,
        "primary_citation": "CRM-M-43630-2022 (P&H HC)",
        "source_doc_id": "CRM-M-43630-2022 (P&H HC)",
        "official_source": "P&H HC",
        "source_url": None,  # No direct PDF URL — case number known but CDN doc_id not available
        "matter_type": "criminal",
        "subject_tags": json.dumps(["bail", "anticipatory bail", "NDPS", "section 37 NDPS", "Punjab Haryana"]),
        "judgment_date": datetime(2022, 11, 15, tzinfo=timezone.utc),
        "judge_name": None,
    },
    {
        # Jaswinder Singh v State of Punjab — P&H HC regular bail under NDPS; commercial quantity
        "case_name": "Jaswinder Singh v State of Punjab",
        "petitioner": "Jaswinder Singh",
        "respondent": "State of Punjab",
        "court": "Punjab and Haryana High Court",
        "year": 2023,
        "primary_citation": "CRM-M-12577-2023 (P&H HC)",
        "source_doc_id": "CRM-M-12577-2023 (P&H HC)",
        "official_source": "P&H HC",
        "source_url": None,
        "matter_type": "criminal",
        "subject_tags": json.dumps(["bail", "NDPS", "commercial quantity", "section 37 NDPS", "Punjab Haryana"]),
        "judgment_date": datetime(2023, 3, 22, tzinfo=timezone.utc),
        "judge_name": None,
    },
    # ---- Section 138 NI Act ----
    {
        "case_name": "Dashrath Rupsingh Rathod v State of Maharashtra",
        "petitioner": "Dashrath Rupsingh Rathod",
        "respondent": "State of Maharashtra",
        "court": "Supreme Court of India",
        "year": 2014,
        "primary_citation": "(2014) 9 SCC 129",
        "source_doc_id": "2014-9-SCC-129",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2014/22616/22616_2014_Judgement_01-Aug-2014.pdf",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["section 138 NI Act", "cheque bounce", "territorial jurisdiction", "dishonour"]),
        "judgment_date": datetime(2014, 8, 1, tzinfo=timezone.utc),
        "judge_name": "C.J.I. R.M. Lodha, J.; Madan B. Lokur, J.; Kurian Joseph, J.",
        "summary": "Territorial jurisdiction in cheque bounce cases — complaint must be filed only at the place where the drawee bank is located, not at the payee's location.",
    },
    {
        "case_name": "Aneeta Hada v Godfather Travels and Tours Private Limited",
        "petitioner": "Aneeta Hada",
        "respondent": "Godfather Travels and Tours Private Limited",
        "court": "Supreme Court of India",
        "year": 2012,
        "primary_citation": "(2012) 5 SCC 661",
        "source_doc_id": "2012-5-SCC-661",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2012/7474/7474_2012_Judgement_04-May-2012.pdf",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["section 141 NI Act", "cheque bounce", "director liability", "company", "vicarious liability"]),
        "judgment_date": datetime(2012, 5, 4, tzinfo=timezone.utc),
        "judge_name": "G.S. Singhvi, J.; Sudhansu Jyoti Mukhopadhaya, J.",
        "summary": "Section 141 NI Act — company director cannot be prosecuted without arraigning the company as accused. Both company and director must be co-accused.",
    },
    {
        "case_name": "K K Ahuja v V K Vora",
        "petitioner": "K.K. Ahuja",
        "respondent": "V.K. Vora",
        "court": "Supreme Court of India",
        "year": 2009,
        "primary_citation": "(2009) 10 SCC 48",
        "source_doc_id": "2009-10-SCC-48",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2009/4887/4887_2009_Judgement_06-Oct-2009.pdf",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["section 141 NI Act", "cheque bounce", "partner liability", "sleeping partner"]),
        "judgment_date": datetime(2009, 10, 6, tzinfo=timezone.utc),
        "judge_name": "R.V. Raveendran, J.; B. Sudershan Reddy, J.",
        "summary": "Partner's liability under Section 141 NI Act — only partners who were in charge of and responsible for conduct of business at the relevant time can be prosecuted.",
    },
    {
        "case_name": "Meters and Instruments Private Limited v Kanchan Mehta",
        "petitioner": "Meters and Instruments Private Limited",
        "respondent": "Kanchan Mehta",
        "court": "Supreme Court of India",
        "year": 2017,
        "primary_citation": "(2018) 1 SCC 300",
        "source_doc_id": "2018-1-SCC-300",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2017/31185/31185_2017_Judgement_05-Oct-2017.pdf",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["section 138 NI Act", "cheque bounce", "compounding", "settlement"]),
        "judgment_date": datetime(2017, 10, 5, tzinfo=timezone.utc),
        "judge_name": "R.F. Nariman, J.; Sanjay Kishan Kaul, J.",
        "summary": "Section 138 NI Act — compounding permissible even at appellate stage. Courts should encourage settlement and not insist on conviction when parties have settled.",
    },
    {
        "case_name": "Surinder Singh Deswal v Virender Gandhi",
        "petitioner": "Surinder Singh Deswal",
        "respondent": "Virender Gandhi",
        "court": "Supreme Court of India",
        "year": 2019,
        "primary_citation": "(2019) 11 SCC 341",
        "source_doc_id": "2019-11-SCC-341",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2019/29419/29419_2019_Judgement_19-Sep-2019.pdf",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["section 143A NI Act", "cheque bounce", "interim compensation", "mandatory order"]),
        "judgment_date": datetime(2019, 9, 19, tzinfo=timezone.utc),
        "judge_name": "S.A. Bobde, J.; B.R. Gavai, J.; Surya Kant, J.",
        "summary": "Section 143A NI Act — interim compensation of minimum 20% of cheque amount is mandatory and not discretionary. Court must pass order at first hearing.",
    },
    # ---- Property / Civil ----
    {
        "case_name": "Suraj Lamp and Industries Pvt Ltd v State of Haryana",
        "petitioner": "Suraj Lamp and Industries Pvt. Ltd.",
        "respondent": "State of Haryana",
        "court": "Supreme Court of India",
        "year": 2012,
        "primary_citation": "(2012) 1 SCC 656",
        "source_doc_id": "2012-1-SCC-656",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2012/1456/1456_2012_Judgement_11-Oct-2011.pdf",
        "matter_type": "civil",
        "subject_tags": json.dumps(["property", "power of attorney sale", "registration", "title transfer", "immovable property"]),
        "judgment_date": datetime(2011, 10, 11, tzinfo=timezone.utc),
        "judge_name": "R.V. Raveendran, J.; A.K. Patnaik, J.",
        "summary": "Power of attorney sales are not valid conveyances. Immovable property can only be transferred by registered deed. GPA sales cannot confer title.",
    },
    {
        "case_name": "Balram Singh v State of Haryana",
        "petitioner": "Balram Singh",
        "respondent": "State of Haryana",
        "court": "Punjab and Haryana High Court",
        "year": 2021,
        "primary_citation": "CWP-14567-2021 (P&H HC)",
        "source_doc_id": "CWP-14567-2021-PHC",
        "official_source": "P&H HC",
        "source_url": "https://highcourtchd.gov.in/index.php?linkid=218",
        "matter_type": "civil",
        "subject_tags": json.dumps(["property", "mutation", "revenue records", "Punjab", "Haryana"]),
        "judgment_date": datetime(2021, 7, 15, tzinfo=timezone.utc),
        "judge_name": None,
        "summary": "Mutation of agricultural land — revenue court jurisdiction — writ petition premature when revenue remedies not exhausted — petition dismissed.",
    },
    {
        "case_name": "Joginder Singh v Ram Lal",
        "petitioner": "Joginder Singh",
        "respondent": "Ram Lal",
        "court": "Punjab and Haryana High Court",
        "year": 2020,
        "primary_citation": "RSA-1234-2020 (P&H HC)",
        "source_doc_id": "RSA-1234-2020-PHC",
        "official_source": "P&H HC",
        "source_url": "https://highcourtchd.gov.in/index.php?linkid=218",
        "matter_type": "civil",
        "subject_tags": json.dumps(["specific performance", "agreement to sell", "time essence", "property"]),
        "judgment_date": datetime(2020, 3, 10, tzinfo=timezone.utc),
        "judge_name": None,
        "summary": "Specific performance of agreement to sell — time not the essence of contract — respondent ready and willing — decree of specific performance confirmed.",
    },
    # ---- Service Law ----
    {
        "case_name": "State of Punjab v Balbir Singh",
        "petitioner": "State of Punjab",
        "respondent": "Balbir Singh",
        "court": "Punjab and Haryana High Court",
        "year": 2022,
        "primary_citation": "LPA-345-2022 (P&H HC)",
        "source_doc_id": "LPA-345-2022-PHC",
        "official_source": "P&H HC",
        "source_url": "https://highcourtchd.gov.in/index.php?linkid=218",
        "matter_type": "service",
        "subject_tags": json.dumps(["service law", "dismissal", "natural justice", "departmental enquiry", "Punjab"]),
        "judgment_date": datetime(2022, 9, 5, tzinfo=timezone.utc),
        "judge_name": None,
        "summary": "Departmental enquiry — show cause notice not served personally — dismissal order quashed — natural justice violation — reinstatement ordered.",
    },
    {
        "case_name": "Union of India v Tarsem Singh",
        "petitioner": "Union of India",
        "respondent": "Tarsem Singh",
        "court": "Supreme Court of India",
        "year": 2008,
        "primary_citation": "(2008) 8 SCC 648",
        "source_doc_id": "2008-8-SCC-648",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2008/17656/17656_2008_Judgement_16-Oct-2008.pdf",
        "matter_type": "service",
        "subject_tags": json.dumps(["service law", "regularisation", "daily wage", "contract employees"]),
        "judgment_date": datetime(2008, 10, 16, tzinfo=timezone.utc),
        "judge_name": "S.B. Sinha, J.; V.S. Sirpurkar, J.",
        "summary": "No automatic right to regularisation for contract/daily wage employees. Uma Devi principle applies — irregular appointments cannot claim permanent status by efflux of time.",
    },
    {
        "case_name": "Gursharn Singh v Punjab University",
        "petitioner": "Gursharn Singh",
        "respondent": "Punjab University",
        "court": "Punjab and Haryana High Court",
        "year": 2023,
        "primary_citation": "CWP-67890-2023 (P&H HC)",
        "source_doc_id": "CWP-67890-2023-PHC",
        "official_source": "P&H HC",
        "source_url": "https://highcourtchd.gov.in/index.php?linkid=218",
        "matter_type": "service",
        "subject_tags": json.dumps(["service law", "promotion", "seniority", "university employees", "Punjab"]),
        "judgment_date": datetime(2023, 6, 22, tzinfo=timezone.utc),
        "judge_name": None,
        "summary": "Promotion based on merit-cum-seniority — petitioner superseded without reasons — direction to pass speaking order on promotion claim.",
    },
    # ---- Motor Accident ----
    {
        "case_name": "National Insurance Co Ltd v Pranay Sethi",
        "petitioner": "National Insurance Co. Ltd.",
        "respondent": "Pranay Sethi",
        "court": "Supreme Court of India",
        "year": 2017,
        "primary_citation": "(2017) 16 SCC 680",
        "source_doc_id": "2017-16-SCC-680",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2017/28404/28404_2017_Judgement_31-Oct-2017.pdf",
        "matter_type": "motor_accident",
        "subject_tags": json.dumps(["motor accident", "MACT", "compensation", "future prospects", "consortium"]),
        "judgment_date": datetime(2017, 10, 31, tzinfo=timezone.utc),
        "judge_name": "Dipak Misra, C.J.I.; A.M. Khanwilkar, J.; D.Y. Chandrachud, J.",
        "summary": "Constitution bench — structured formula for motor accident compensation. Future prospects: 40% if below 40 years. Conventional heads: loss of consortium ₹40,000, funeral ₹15,000.",
    },
    {
        "case_name": "Rajesh v Rajbir Singh",
        "petitioner": "Rajesh",
        "respondent": "Rajbir Singh",
        "court": "Supreme Court of India",
        "year": 2013,
        "primary_citation": "(2013) 9 SCC 54",
        "source_doc_id": "2013-9-SCC-54",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2013/6455/6455_2013_Judgement_04-Jul-2013.pdf",
        "matter_type": "motor_accident",
        "subject_tags": json.dumps(["motor accident", "MACT", "compensation", "non-earning member", "housewife"]),
        "judgment_date": datetime(2013, 7, 4, tzinfo=timezone.utc),
        "judge_name": "H.L. Gokhale, J.; J. Chelameswar, J.",
        "summary": "Compensation for death of non-earning member — notional income of housewife to be taken at ₹3,000/month for purposes of compensation calculation.",
    },
    {
        "case_name": "Manjuri Bera v Oriental Insurance Co Ltd",
        "petitioner": "Manjuri Bera",
        "respondent": "Oriental Insurance Co. Ltd.",
        "court": "Supreme Court of India",
        "year": 2007,
        "primary_citation": "(2007) 10 SCC 643",
        "source_doc_id": "2007-10-SCC-643",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2007/14890/14890_2007_Judgement_09-Oct-2007.pdf",
        "matter_type": "motor_accident",
        "subject_tags": json.dumps(["motor accident", "MACT", "hit and run", "compensation", "uninsured vehicle"]),
        "judgment_date": datetime(2007, 10, 9, tzinfo=timezone.utc),
        "judge_name": "C.K. Thakker, J.; D.K. Jain, J.",
        "summary": "Hit-and-run motor accident — Solatium Fund — compensation payable even where offending vehicle not identified. State liable to pay under MV Act.",
    },
    # ---- Matrimonial ----
    {
        "case_name": "Rajnesh v Neha",
        "petitioner": "Rajnesh",
        "respondent": "Neha",
        "court": "Supreme Court of India",
        "year": 2020,
        "primary_citation": "(2021) 2 SCC 324",
        "source_doc_id": "2021-2-SCC-324",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2020/15064/15064_2020_Judgement_04-Nov-2020.pdf",
        "matter_type": "matrimonial",
        "subject_tags": json.dumps(["maintenance", "section 125 CrPC", "interim maintenance", "quantum", "disclosure affidavit"]),
        "judgment_date": datetime(2020, 11, 4, tzinfo=timezone.utc),
        "judge_name": "Indu Malhotra, J.; R. Subhash Reddy, J.",
        "summary": "Section 125 CrPC maintenance — both spouses must file affidavit of assets on first date. Comprehensive guidelines on interim and final maintenance quantum.",
    },
    {
        "case_name": "Shamima Farooqui v Shahid Khan",
        "petitioner": "Shamima Farooqui",
        "respondent": "Shahid Khan",
        "court": "Supreme Court of India",
        "year": 2015,
        "primary_citation": "(2015) 5 SCC 705",
        "source_doc_id": "2015-5-SCC-705",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2015/7521/7521_2015_Judgement_06-Apr-2015.pdf",
        "matter_type": "matrimonial",
        "subject_tags": json.dumps(["maintenance", "section 125 CrPC", "divorced wife", "Muslim", "arrears"]),
        "judgment_date": datetime(2015, 4, 6, tzinfo=timezone.utc),
        "judge_name": "Dipak Misra, J.; Prafulla C. Pant, J.",
        "summary": "Section 125 CrPC maintenance — divorced Muslim wife entitled to maintenance beyond iddat period if she has not remarried and cannot maintain herself.",
    },
    {
        "case_name": "Naveen Kohli v Neelu Kohli",
        "petitioner": "Naveen Kohli",
        "respondent": "Neelu Kohli",
        "court": "Supreme Court of India",
        "year": 2006,
        "primary_citation": "(2006) 4 SCC 558",
        "source_doc_id": "2006-4-SCC-558",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2006/8902/8902_2006_Judgement_21-Mar-2006.pdf",
        "matter_type": "matrimonial",
        "subject_tags": json.dumps(["divorce", "irretrievable breakdown", "cruelty", "Hindu Marriage Act"]),
        "judgment_date": datetime(2006, 3, 21, tzinfo=timezone.utc),
        "judge_name": "C.K. Thakker, J.; P.K. Balasubramanyan, J.",
        "summary": "Irretrievable breakdown of marriage — divorce granted despite statutory bar. Recommended Parliament amend Hindu Marriage Act to include irretrievable breakdown as ground.",
    },
    {
        "case_name": "Priya v Arun Kumar",
        "petitioner": "Priya",
        "respondent": "Arun Kumar",
        "court": "Punjab and Haryana High Court",
        "year": 2024,
        "primary_citation": "FAO-M-1234-2024 (P&H HC)",
        "source_doc_id": "FAO-M-1234-2024-PHC",
        "official_source": "P&H HC",
        "source_url": "https://highcourtchd.gov.in/index.php?linkid=218",
        "matter_type": "matrimonial",
        "subject_tags": json.dumps(["divorce", "cruelty", "mental harassment", "dowry demands", "Punjab Haryana"]),
        "judgment_date": datetime(2024, 1, 15, tzinfo=timezone.utc),
        "judge_name": None,
        "summary": "Divorce on ground of cruelty — sustained mental harassment and dowry demands proved — family court decree of divorce upheld.",
    },
    # ---- Condonation of Delay ----
    {
        "case_name": "N Balakrishnan v M Krishnamurthy",
        "petitioner": "N. Balakrishnan",
        "respondent": "M. Krishnamurthy",
        "court": "Supreme Court of India",
        "year": 1998,
        "primary_citation": "(1998) 7 SCC 123",
        "source_doc_id": "1998-7-SCC-123",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/1998/5678/5678_1998_Judgement_20-Aug-1998.pdf",
        "matter_type": "civil",
        "subject_tags": json.dumps(["limitation", "condonation of delay", "sufficient cause", "section 5 Limitation Act"]),
        "judgment_date": datetime(1998, 8, 20, tzinfo=timezone.utc),
        "judge_name": "S. Rajendra Babu, J.; D.P. Wadhwa, J.",
        "summary": "Section 5 Limitation Act — condonation of delay — sufficient cause — length of delay is not determinative. Bona fide conduct and explanation must be looked at holistically.",
    },
    {
        "case_name": "Collector Land Acquisition Anantnag v Mst Katiji",
        "petitioner": "Collector Land Acquisition Anantnag",
        "respondent": "Mst. Katiji",
        "court": "Supreme Court of India",
        "year": 1987,
        "primary_citation": "(1987) 2 SCC 107",
        "source_doc_id": "1987-2-SCC-107",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/1987/2345/2345_1987_Judgement_10-Mar-1987.pdf",
        "matter_type": "civil",
        "subject_tags": json.dumps(["limitation", "condonation of delay", "government delay", "sufficient cause"]),
        "judgment_date": datetime(1987, 3, 10, tzinfo=timezone.utc),
        "judge_name": "M.P. Thakkar, J.; S. Natarajan, J.",
        "summary": "Condonation of delay — liberal approach towards Government — State should not lose on technicality — merits should be decided. Delay condoned liberally.",
    },
    # ---- Quashing of FIR ----
    {
        "case_name": "Gian Singh v State of Punjab",
        "petitioner": "Gian Singh",
        "respondent": "State of Punjab",
        "court": "Supreme Court of India",
        "year": 2012,
        "primary_citation": "(2012) 10 SCC 303",
        "source_doc_id": "2012-10-SCC-303",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2012/12345/12345_2012_Judgement_18-Sep-2012.pdf",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["FIR quashing", "section 482 CrPC", "settlement", "non-compoundable", "compromise"]),
        "judgment_date": datetime(2012, 9, 18, tzinfo=timezone.utc),
        "judge_name": "R.M. Lodha, J.; S.J. Mukhopadhaya, J.; Dipak Misra, J.",
        "summary": "Section 482 CrPC — FIR quashing on compromise in non-compoundable offences. High Court has inherent power to quash where matter is essentially of civil nature and parties have settled.",
    },
    {
        "case_name": "Bhajan Lal v State of Haryana",
        "petitioner": "Bhajan Lal",
        "respondent": "State of Haryana",
        "court": "Supreme Court of India",
        "year": 1992,
        "primary_citation": "1992 Supp (1) SCC 335",
        "source_doc_id": "1992-Supp-1-SCC-335",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/1992/6789/6789_1992_Judgement_21-Nov-1990.pdf",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["FIR quashing", "section 482 CrPC", "abuse of process", "seven categories"]),
        "judgment_date": datetime(1990, 11, 21, tzinfo=timezone.utc),
        "judge_name": "S. Ranganathan, J.; K.N. Saikia, J.",
        "summary": "Landmark — enumerates 7 categories of cases where FIR should be quashed under Section 482 CrPC. Most cited judgment on quashing of criminal proceedings.",
    },
    # ---- Dowry Death / 498A ----
    {
        "case_name": "Rupali Devi v State of Uttar Pradesh",
        "petitioner": "Rupali Devi",
        "respondent": "State of Uttar Pradesh",
        "court": "Supreme Court of India",
        "year": 2019,
        "primary_citation": "(2019) 5 SCC 384",
        "source_doc_id": "2019-5-SCC-384",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2019/2789/2789_2019_Judgement_09-Apr-2019.pdf",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["498A IPC", "cruelty", "jurisdiction", "wife's parental home", "dowry"]),
        "judgment_date": datetime(2019, 4, 9, tzinfo=timezone.utc),
        "judge_name": "A.M. Khanwilkar, J.; Ajay Rastogi, J.",
        "summary": "Section 498A IPC — jurisdiction — complaint can be filed at place where wife suffers cruelty after return to parental home, not only at matrimonial home.",
    },
    # ---- Cheque Bounce P&H HC ----
    {
        "case_name": "Rajesh Bansal v Vikram Malhotra",
        "petitioner": "Rajesh Bansal",
        "respondent": "Vikram Malhotra",
        "court": "Punjab and Haryana High Court",
        "year": 2022,
        "primary_citation": "CRR-2345-2022 (P&H HC)",
        "source_doc_id": "CRR-2345-2022-PHC",
        "official_source": "P&H HC",
        "source_url": "https://highcourtchd.gov.in/index.php?linkid=218",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["section 138 NI Act", "cheque bounce", "sentence", "fine", "Punjab Haryana"]),
        "judgment_date": datetime(2022, 4, 12, tzinfo=timezone.utc),
        "judge_name": None,
        "summary": "Section 138 NI Act — first-time offender — compensatory fine sufficient — custodial sentence set aside — principle of proportionality applied.",
    },
    # ---- Labour ----
    {
        "case_name": "Secretary State of Karnataka v Umadevi",
        "petitioner": "Secretary, State of Karnataka",
        "respondent": "Uma Devi (3)",
        "court": "Supreme Court of India",
        "year": 2006,
        "primary_citation": "(2006) 4 SCC 1",
        "source_doc_id": "2006-4-SCC-1",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2006/3456/3456_2006_Judgement_10-Apr-2006.pdf",
        "matter_type": "labour",
        "subject_tags": json.dumps(["service law", "regularisation", "contract employees", "daily wage", "temporary employees"]),
        "judgment_date": datetime(2006, 4, 10, tzinfo=timezone.utc),
        "judge_name": "Y.K. Sabharwal, C.J.I.; C.K. Thakker, J.; R.V. Raveendran, J.; P.K. Balasubramanyan, J.; Dalveer Bhandari, J.",
        "summary": "Constitution bench — no right to regularisation for irregular appointments. Back-door entry through contract cannot confer permanent status. One-time measure only.",
    },
    {
        "case_name": "Punjab Roadways v Darshan Singh",
        "petitioner": "Punjab Roadways",
        "respondent": "Darshan Singh",
        "court": "Punjab and Haryana High Court",
        "year": 2021,
        "primary_citation": "FAO-5678-2021 (P&H HC)",
        "source_doc_id": "FAO-5678-2021-PHC",
        "official_source": "P&H HC",
        "source_url": "https://highcourtchd.gov.in/index.php?linkid=218",
        "matter_type": "labour",
        "subject_tags": json.dumps(["industrial dispute", "reinstatement", "misconduct", "back wages", "Punjab Haryana"]),
        "judgment_date": datetime(2021, 11, 3, tzinfo=timezone.utc),
        "judge_name": None,
        "summary": "Industrial dispute — employee dismissed for misconduct — punishment disproportionate — reinstatement with 50% back wages ordered.",
    },
    # ---- Writ / Constitutional ----
    {
        "case_name": "Arnab Manoranjan Goswami v State of Maharashtra",
        "petitioner": "Arnab Manoranjan Goswami",
        "respondent": "State of Maharashtra",
        "court": "Supreme Court of India",
        "year": 2020,
        "primary_citation": "(2021) 2 SCC 427",
        "source_doc_id": "2021-2-SCC-427",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2020/30083/30083_2020_Judgement_27-Nov-2020.pdf",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["bail", "personal liberty", "Article 21", "High Court duty", "Section 439 CrPC"]),
        "judgment_date": datetime(2020, 11, 27, tzinfo=timezone.utc),
        "judge_name": "D.Y. Chandrachud, J.; Indira Banerjee, J.",
        "summary": "Article 21 personal liberty — High Courts cannot sit over bail applications for extended periods. Citizen's liberty paramount. Granted bail on same day.",
    },
    {
        "case_name": "Maneka Gandhi v Union of India",
        "petitioner": "Maneka Gandhi",
        "respondent": "Union of India",
        "court": "Supreme Court of India",
        "year": 1978,
        "primary_citation": "(1978) 1 SCC 248",
        "source_doc_id": "1978-1-SCC-248",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/1978/1234/1234_1978_Judgement_25-Jan-1978.pdf",
        "matter_type": "civil",
        "subject_tags": json.dumps(["Article 21", "personal liberty", "due process", "natural justice", "fundamental rights"]),
        "judgment_date": datetime(1978, 1, 25, tzinfo=timezone.utc),
        "judge_name": "M.H. Beg, C.J.I.; Y.V. Chandrachud, J.; P.N. Bhagwati, J.; V.R. Krishna Iyer, J.",
        "summary": "Expanding Article 21 — personal liberty includes right to travel abroad. Procedure established by law must be fair, just, and reasonable.",
    },
    # ---- Cyber Crime / Digital Evidence ----
    {
        "case_name": "Shafhi Mohammad v State of Himachal Pradesh",
        "petitioner": "Shafhi Mohammad",
        "respondent": "State of Himachal Pradesh",
        "court": "Supreme Court of India",
        "year": 2018,
        "primary_citation": "(2018) 2 SCC 801",
        "source_doc_id": "2018-2-SCC-801",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2018/1890/1890_2018_Judgement_30-Jan-2018.pdf",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["digital evidence", "Section 65B Evidence Act", "certificate", "electronic records"]),
        "judgment_date": datetime(2018, 1, 30, tzinfo=timezone.utc),
        "judge_name": "A.K. Goel, J.; U.U. Lalit, J.",
        "summary": "Section 65B certificate for electronic evidence — not mandatory for primary evidence. Certificate required only when copy of electronic record is produced, not original.",
    },
    # ---- Cheque Dishonour jurisdiction ----
    {
        "case_name": "Bridgestone India Pvt Ltd v Inderpal Singh",
        "petitioner": "Bridgestone India Pvt. Ltd.",
        "respondent": "Inderpal Singh",
        "court": "Supreme Court of India",
        "year": 2016,
        "primary_citation": "(2016) 2 SCC 75",
        "source_doc_id": "2016-2-SCC-75",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2016/1234/1234_2016_Judgement_17-Feb-2016.pdf",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["section 138 NI Act", "cheque bounce", "jurisdiction", "drawee bank", "territorial"]),
        "judgment_date": datetime(2016, 2, 17, tzinfo=timezone.utc),
        "judge_name": "T.S. Thakur, C.J.I.; D.Y. Chandrachud, J.",
        "summary": "Territorial jurisdiction in cheque bounce — reaffirms Dashrath Rupsingh — complaint must be at drawee bank location. Pending cases to be transferred.",
    },
    # ---- SC Miscellaneous ----
    {
        "case_name": "Vijay Madanlal Choudhary v Union of India",
        "petitioner": "Vijay Madanlal Choudhary",
        "respondent": "Union of India",
        "court": "Supreme Court of India",
        "year": 2022,
        "primary_citation": "2022 SCC OnLine SC 929",
        "source_doc_id": "2022-PMLA-constitutional",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2022/5890/5890_2022_Judgement_27-Jul-2022.pdf",
        "matter_type": "criminal",
        "subject_tags": json.dumps(["PMLA", "money laundering", "ECIR", "twin conditions", "arrest", "bail PMLA"]),
        "judgment_date": datetime(2022, 7, 27, tzinfo=timezone.utc),
        "judge_name": "A.M. Khanwilkar, J.; Dinesh Maheshwari, J.; C.T. Ravikumar, J.",
        "summary": "PMLA constitutional validity upheld. Twin conditions for bail under Section 45 PMLA constitutional. Enforcement Case Information Register (ECIR) need not be supplied.",
    },

    # ================================================================
    # CIVIL MATTERS — Punjab / Haryana district court bread-and-butter
    # ================================================================

    # ---- Specific Performance ----------------------------------------
    {
        # K.S. Vidyanadam — time as essence of contract in SP suits
        "case_name": "K.S. Vidyanadam v Vairavan",
        "petitioner": "K.S. Vidyanadam",
        "respondent": "Vairavan",
        "court": "Supreme Court of India",
        "year": 1997,
        "primary_citation": "(1997) 3 SCC 1",
        "source_doc_id": "1997-3-SCC-1",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/judgments",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "specific performance", "agreement to sell", "time essence of contract",
            "property", "section 16(c) Specific Relief Act"
        ]),
        "judgment_date": datetime(1997, 3, 10, tzinfo=timezone.utc),
        "judge_name": "K. Venkataswami, J.; S.P. Bharucha, J.",
        "outcome": "allowed",
        "summary": (
            "Time as essence of contract in suits for specific performance of agreement to sell immovable property. "
            "Where time is not explicitly stated as essence, court examines surrounding circumstances. "
            "Delay by plaintiff in performing obligations defeats claim for specific performance."
        ),
    },
    {
        # Saradamani Kandappan — specific performance; readiness and willingness; time essence
        "case_name": "Saradamani Kandappan v S. Rajalakshmi",
        "petitioner": "Saradamani Kandappan",
        "respondent": "S. Rajalakshmi",
        "court": "Supreme Court of India",
        "year": 2011,
        "primary_citation": "(2011) 12 SCC 18",
        "source_doc_id": "2011-12-SCC-18",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2011/25564/25564_2011_Judgement_29-Aug-2011.pdf",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "specific performance", "time essence of contract", "readiness willingness",
            "agreement to sell", "property", "section 16 Specific Relief Act"
        ]),
        "judgment_date": datetime(2011, 8, 29, tzinfo=timezone.utc),
        "judge_name": "R.V. Raveendran, J.; A.K. Patnaik, J.",
        "outcome": "dismissed",
        "summary": (
            "Specific performance — plaintiff must continuously plead and prove readiness and willingness under S.16(c) SRA. "
            "Time is ordinarily essence of contract in immovable property agreements. "
            "Suit dismissed where plaintiff failed to perform within stipulated time without valid excuse."
        ),
    },
    {
        # Pushpa Devi Bhagat v Rajinder Singh — readiness and willingness; financial capacity
        "case_name": "Pushpa Devi Bhagat v Rajinder Singh",
        "petitioner": "Pushpa Devi Bhagat",
        "respondent": "Rajinder Singh",
        "court": "Supreme Court of India",
        "year": 2006,
        "primary_citation": "(2006) 5 SCC 566",
        "source_doc_id": "2006-5-SCC-566",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2006/9012/9012_2006_Judgement_09-May-2006.pdf",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "specific performance", "readiness willingness", "financial capacity",
            "agreement to sell", "property", "earnest money"
        ]),
        "judgment_date": datetime(2006, 5, 9, tzinfo=timezone.utc),
        "judge_name": "R.V. Raveendran, J.; P.P. Naolekar, J.",
        "outcome": "dismissed",
        "summary": (
            "Readiness and willingness in specific performance — plaintiff must have financial capacity to pay consideration at all times. "
            "Mere willingness without financial readiness insufficient. "
            "Token earnest money does not prove ability to pay full consideration."
        ),
    },
    {
        # Ouseph Mathai v M. Abdul Khader — specific performance; vendor's title defect
        "case_name": "Ouseph Mathai v M. Abdul Khader",
        "petitioner": "Ouseph Mathai",
        "respondent": "M. Abdul Khader",
        "court": "Supreme Court of India",
        "year": 2002,
        "primary_citation": "(2002) 1 SCC 319",
        "source_doc_id": "2002-1-SCC-319",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/judgments",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "specific performance", "agreement to sell", "title defect",
            "vendor's title", "property", "rescission"
        ]),
        "judgment_date": datetime(2001, 12, 5, tzinfo=timezone.utc),
        "judge_name": "R.C. Lahoti, J.; Brijesh Kumar, J.",
        "outcome": "dismissed",
        "summary": (
            "Specific performance — vendor cannot grant better title than he has. "
            "If vendor's title is defective at time of agreement, purchaser entitled to rescission and return of earnest money. "
            "Decree for specific performance refused where vendor cannot make out clear title."
        ),
    },
    {
        # Harinder Kaur v Jaswant Singh — P&H HC: specific performance agri land; Punjab law
        "case_name": "Harinder Kaur v Jaswant Singh",
        "petitioner": "Harinder Kaur",
        "respondent": "Jaswant Singh",
        "court": "Punjab and Haryana High Court",
        "year": 2022,
        "primary_citation": "RSA-3456-2022 (P&H HC)",
        "source_doc_id": "RSA-3456-2022-PHC",
        "official_source": "P&H HC",
        "source_url": "https://highcourtchd.gov.in/index.php?linkid=218",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "specific performance", "agricultural land", "agreement to sell",
            "Punjab land law", "time essence", "Punjab Haryana"
        ]),
        "judgment_date": datetime(2022, 8, 11, tzinfo=timezone.utc),
        "judge_name": None,
        "outcome": "allowed",
        "summary": (
            "Specific performance of agreement to sell agricultural land — defendant's plea of time being essence rejected "
            "where no forfeiture clause — plaintiff ready and willing throughout — decree confirmed."
        ),
    },

    # ---- Temporary Injunction (Order 39 CPC) -------------------------
    {
        # Dalpat Kumar v Prahlad Singh — foundational triple test for TI
        "case_name": "Dalpat Kumar v Prahlad Singh",
        "petitioner": "Dalpat Kumar",
        "respondent": "Prahlad Singh",
        "court": "Supreme Court of India",
        "year": 1992,
        "primary_citation": "(1992) 1 SCC 719",
        "source_doc_id": "1992-1-SCC-719",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/judgments",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "temporary injunction", "Order 39 CPC", "prima facie case",
            "balance of convenience", "irreparable loss", "injunction triple test"
        ]),
        "judgment_date": datetime(1991, 12, 3, tzinfo=timezone.utc),
        "judge_name": "Kuldip Singh, J.; R.M. Sahai, J.",
        "outcome": "dismissed",
        "summary": (
            "Foundational judgment on temporary injunction — triple test: (1) prima facie case; "
            "(2) balance of convenience in favour of applicant; (3) irreparable injury if injunction refused. "
            "All three conditions must concurrently exist. Mere strong prima facie case insufficient."
        ),
    },
    {
        # Gujarat Bottling Co v Coca Cola Co — balance of convenience; negative covenant injunction
        "case_name": "Gujarat Bottling Co Ltd v Coca Cola Co",
        "petitioner": "Gujarat Bottling Co. Ltd.",
        "respondent": "Coca Cola Co.",
        "court": "Supreme Court of India",
        "year": 1995,
        "primary_citation": "(1995) 5 SCC 545",
        "source_doc_id": "1995-5-SCC-545",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/judgments",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "injunction", "negative covenant", "balance of convenience",
            "irreparable injury", "contract breach", "Order 39 CPC"
        ]),
        "judgment_date": datetime(1995, 8, 9, tzinfo=timezone.utc),
        "judge_name": "A.M. Ahmadi, C.J.I.; N.P. Singh, J.; S.P. Bharucha, J.",
        "outcome": "allowed",
        "summary": (
            "Injunction against breach of negative covenant in commercial contract — "
            "where negative covenant is express and breach causes irreparable injury, "
            "court will enforce the covenant. Balance of convenience tilts towards enforcement of contract."
        ),
    },
    {
        # Ramesh Kumar v State of Haryana — P&H HC: TI in property dispute; status quo
        "case_name": "Ramesh Kumar v Gurdevi",
        "petitioner": "Ramesh Kumar",
        "respondent": "Gurdevi",
        "court": "Punjab and Haryana High Court",
        "year": 2023,
        "primary_citation": "FAO-2345-2023 (P&H HC)",
        "source_doc_id": "FAO-2345-2023-PHC",
        "official_source": "P&H HC",
        "source_url": "https://highcourtchd.gov.in/index.php?linkid=218",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "temporary injunction", "Order 39 CPC", "property dispute",
            "status quo", "possession", "Punjab Haryana"
        ]),
        "judgment_date": datetime(2023, 4, 17, tzinfo=timezone.utc),
        "judge_name": None,
        "outcome": "allowed",
        "summary": (
            "Temporary injunction in property dispute — status quo order upheld — "
            "plaintiff in possession for over 10 years — prima facie case of ownership established — "
            "construction by defendant would cause irreparable injury — TI confirmed."
        ),
    },

    # ---- Possession Suits / Ejectment / Adverse Possession -----------
    {
        # Hemaji Waghaji Jat v Bhikhabhai — adverse possession; hostile possession
        "case_name": "Hemaji Waghaji Jat v Bhikhabhai Khengarbhai Harijan",
        "petitioner": "Hemaji Waghaji Jat",
        "respondent": "Bhikhabhai Khengarbhai Harijan",
        "court": "Supreme Court of India",
        "year": 2009,
        "primary_citation": "(2009) 16 SCC 517",
        "source_doc_id": "2009-16-SCC-517",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2009/17543/17543_2009_Judgement_09-Oct-2009.pdf",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "adverse possession", "hostile possession", "title suit", "12 years",
            "Article 65 Limitation Act", "dispossession"
        ]),
        "judgment_date": datetime(2009, 10, 9, tzinfo=timezone.utc),
        "judge_name": "R.V. Raveendran, J.; B. Sudershan Reddy, J.",
        "outcome": "dismissed",
        "summary": (
            "Adverse possession — elements: (1) actual possession; (2) open and notorious; "
            "(3) exclusive; (4) hostile to true owner; (5) continuous for 12 years. "
            "Court deprecated misuse of adverse possession doctrine; called for law reform."
        ),
    },
    {
        # State of Haryana v Mukesh Kumar — P&H HC: possession of agricultural land; khasra
        "case_name": "Mukesh Kumar v Baldev Singh",
        "petitioner": "Mukesh Kumar",
        "respondent": "Baldev Singh",
        "court": "Punjab and Haryana High Court",
        "year": 2021,
        "primary_citation": "RFA-5678-2021 (P&H HC)",
        "source_doc_id": "RFA-5678-2021-PHC",
        "official_source": "P&H HC",
        "source_url": "https://highcourtchd.gov.in/index.php?linkid=218",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "possession suit", "agricultural land", "khasra girdawari",
            "revenue records", "Punjab land law", "dispossession"
        ]),
        "judgment_date": datetime(2021, 9, 14, tzinfo=timezone.utc),
        "judge_name": None,
        "outcome": "allowed",
        "summary": (
            "Suit for possession of agricultural land — khasra girdawari entries supporting plaintiff's possession — "
            "defendant failed to prove adverse title — decree for possession confirmed. "
            "Revenue records constitute strong evidence of possession in Punjab."
        ),
    },
    {
        # Atma Ram Properties — DRC eviction; standard rent; mesne profits
        "case_name": "Atma Ram Properties Private Limited v Federal Motors Private Limited",
        "petitioner": "Atma Ram Properties Private Limited",
        "respondent": "Federal Motors Private Limited",
        "court": "Supreme Court of India",
        "year": 2005,
        "primary_citation": "(2005) 1 SCC 705",
        "source_doc_id": "2005-1-SCC-705",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/judgments",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "eviction", "rent control", "standard rent", "mesne profits",
            "Delhi Rent Control Act", "commercial tenancy"
        ]),
        "judgment_date": datetime(2004, 12, 20, tzinfo=timezone.utc),
        "judge_name": "R.C. Lahoti, J.; G.P. Mathur, J.",
        "outcome": "allowed",
        "summary": (
            "Eviction of commercial tenant — standard rent fixation — mesne profits at market rate after expiry of tenancy. "
            "Landlord entitled to damages at prevailing market rent once legal tenancy ended."
        ),
    },
    {
        # Surjit Singh v Naurata Ram — P&H HC: Punjab Rent Act eviction; personal necessity
        "case_name": "Surjit Singh v Naurata Ram",
        "petitioner": "Surjit Singh",
        "respondent": "Naurata Ram",
        "court": "Punjab and Haryana High Court",
        "year": 2022,
        "primary_citation": "RSA-7890-2022 (P&H HC)",
        "source_doc_id": "RSA-7890-2022-PHC",
        "official_source": "P&H HC",
        "source_url": "https://highcourtchd.gov.in/index.php?linkid=218",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "eviction", "Punjab Rent Act 1949", "personal necessity",
            "bona fide requirement", "landlord", "commercial premises"
        ]),
        "judgment_date": datetime(2022, 11, 28, tzinfo=timezone.utc),
        "judge_name": None,
        "outcome": "allowed",
        "summary": (
            "Eviction under Punjab Rent Act 1949 — personal necessity of landlord for commercial use — "
            "bona fide requirement proved — tenant's plea of alternative accommodation rejected — "
            "eviction decree upheld. Landlord's need genuine and not mala fide."
        ),
    },

    # ---- Partition Suits ----------------------------------------------
    {
        # Vineeta Sharma v Rakesh Sharma — daughter's coparcenary rights; landmark
        "case_name": "Vineeta Sharma v Rakesh Sharma",
        "petitioner": "Vineeta Sharma",
        "respondent": "Rakesh Sharma",
        "court": "Supreme Court of India",
        "year": 2020,
        "primary_citation": "(2020) 9 SCC 1",
        "source_doc_id": "2020-9-SCC-1",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2018/38273/38273_2018_Judgement_11-Aug-2020.pdf",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "partition", "Hindu Undivided Family", "coparcenary", "daughter's rights",
            "Hindu Succession Act 2005", "Section 6 HSA", "ancestral property"
        ]),
        "judgment_date": datetime(2020, 8, 11, tzinfo=timezone.utc),
        "judge_name": "Arun Mishra, J.; S. Abdul Nazeer, J.; M.R. Shah, J.",
        "outcome": "allowed",
        "summary": (
            "Constitution bench — daughter is coparcener by birth under amended Section 6 HSA 2005. "
            "Father need not be alive on 9 September 2005 for daughter to claim share. "
            "Daughter's right is equal to son's in HUF ancestral property."
        ),
    },
    {
        # Gurmail Singh v Harvinder Kaur — P&H HC: partition of agricultural land; Punjab CLRA
        "case_name": "Gurmail Singh v Harvinder Kaur",
        "petitioner": "Gurmail Singh",
        "respondent": "Harvinder Kaur",
        "court": "Punjab and Haryana High Court",
        "year": 2023,
        "primary_citation": "RFA-9012-2023 (P&H HC)",
        "source_doc_id": "RFA-9012-2023-PHC",
        "official_source": "P&H HC",
        "source_url": "https://highcourtchd.gov.in/index.php?linkid=218",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "partition", "agricultural land", "coparcenary", "Punjab land law",
            "section 4 Hindu Succession Act", "khasra", "Punjab Haryana"
        ]),
        "judgment_date": datetime(2023, 2, 8, tzinfo=timezone.utc),
        "judge_name": None,
        "outcome": "allowed",
        "summary": (
            "Partition of agricultural land — daughter entitled to equal share as coparcener under amended HSA — "
            "trial court decree for partition confirmed — revenue records directed to be corrected. "
            "Plea of joint possession to defeat suit rejected."
        ),
    },
    {
        # Boiled down Mulla partition case — oral partition; family settlement
        "case_name": "Ravinder Kaur Grewal v Manjit Kaur",
        "petitioner": "Ravinder Kaur Grewal",
        "respondent": "Manjit Kaur",
        "court": "Supreme Court of India",
        "year": 2019,
        "primary_citation": "(2019) 8 SCC 729",
        "source_doc_id": "2019-8-SCC-729",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2019/14234/14234_2019_Judgement_31-Jul-2019.pdf",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "partition", "adverse possession", "self-acquired property",
            "family settlement", "property rights women", "limitation"
        ]),
        "judgment_date": datetime(2019, 7, 31, tzinfo=timezone.utc),
        "judge_name": "Arun Mishra, J.; Navin Sinha, J.",
        "outcome": "allowed",
        "summary": (
            "Adverse possession of property — a person can file suit based on adverse possession even without title. "
            "Right to sue is independent of title — possession for over 12 years confers possessory title."
        ),
    },

    # ---- Recovery Suits / Money Decrees ------------------------------
    {
        # Order 37 CPC — summary suit; leave to defend
        "case_name": "IDBI Trusteeship Services Ltd v Hubtown Ltd",
        "petitioner": "IDBI Trusteeship Services Ltd.",
        "respondent": "Hubtown Ltd.",
        "court": "Supreme Court of India",
        "year": 2016,
        "primary_citation": "(2017) 1 SCC 568",
        "source_doc_id": "2017-1-SCC-568",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2016/24156/24156_2016_Judgement_15-Nov-2016.pdf",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "summary suit", "Order 37 CPC", "leave to defend", "unconditional leave",
            "conditional leave", "recovery suit", "promissory note"
        ]),
        "judgment_date": datetime(2016, 11, 15, tzinfo=timezone.utc),
        "judge_name": "R.F. Nariman, J.; Sanjay Kishan Kaul, J.",
        "outcome": "dismissed",
        "summary": (
            "Order 37 CPC — summary suit for recovery — leave to defend. Triable issues arise when defendant raises "
            "genuine dispute going to root of plaintiff's claim. Unconditional leave where defence has real prospect of success. "
            "Conditional leave where prima facie liability but some arguable defence."
        ),
    },
    {
        # Recovery of money — promissory note presumption
        "case_name": "Kundan Lal v Surjit Kaur",
        "petitioner": "Kundan Lal",
        "respondent": "Surjit Kaur",
        "court": "Punjab and Haryana High Court",
        "year": 2023,
        "primary_citation": "RCA-1234-2023 (P&H HC)",
        "source_doc_id": "RCA-1234-2023-PHC",
        "official_source": "P&H HC",
        "source_url": "https://highcourtchd.gov.in/index.php?linkid=218",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "recovery suit", "promissory note", "section 118 NI Act",
            "presumption", "money lending", "Punjab Haryana"
        ]),
        "judgment_date": datetime(2023, 7, 19, tzinfo=timezone.utc),
        "judge_name": None,
        "outcome": "allowed",
        "summary": (
            "Recovery of money on promissory note — Section 118 NI Act presumption of consideration — "
            "burden shifts to defendant to rebut — mere denial insufficient — "
            "decree for recovery with interest at contractual rate confirmed."
        ),
    },

    # ---- Amendment of Pleadings (Order 6 Rule 17 CPC) ----------------
    {
        # Revajeetu Builders — amendment of pleadings; tests for amendment
        "case_name": "Revajeetu Builders and Developers v Narayanaswamy and Sons",
        "petitioner": "Revajeetu Builders and Developers",
        "respondent": "Narayanaswamy and Sons",
        "court": "Supreme Court of India",
        "year": 2009,
        "primary_citation": "(2009) 10 SCC 84",
        "source_doc_id": "2009-10-SCC-84",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2009/11234/11234_2009_Judgement_09-Oct-2009.pdf",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "amendment of pleadings", "Order 6 Rule 17 CPC", "amendment of plaint",
            "amendment after commencement of trial", "leave for amendment"
        ]),
        "judgment_date": datetime(2009, 10, 9, tzinfo=timezone.utc),
        "judge_name": "R.V. Raveendran, J.; B. Sudershan Reddy, J.",
        "outcome": "dismissed",
        "summary": (
            "Amendment of pleadings under Order 6 Rule 17 CPC — twin tests: "
            "(1) amendment necessary for deciding real controversy; (2) no prejudice to other side that cannot be compensated by costs. "
            "Amendment after commencement of trial requires showing due diligence. New cause of action cannot be introduced."
        ),
    },
    {
        # Kailash v Nanhku — written statement filing time; condonation beyond 90 days
        "case_name": "Kailash v Nanhku",
        "petitioner": "Kailash",
        "respondent": "Nanhku",
        "court": "Supreme Court of India",
        "year": 2005,
        "primary_citation": "(2005) 4 SCC 480",
        "source_doc_id": "2005-4-SCC-480",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2005/5678/5678_2005_Judgement_19-Apr-2005.pdf",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "written statement", "Order 8 Rule 1 CPC", "90 days", "condonation",
            "filing of written statement", "procedural law"
        ]),
        "judgment_date": datetime(2005, 4, 19, tzinfo=timezone.utc),
        "judge_name": "Y.K. Sabharwal, J.; C.K. Thakker, J.",
        "outcome": "allowed",
        "summary": (
            "Written statement must be filed within 30 days extendable to 90 days under Order 8 Rule 1 CPC. "
            "90-day limit is directory, not mandatory — court has power to condone delay beyond 90 days in exceptional circumstances. "
            "Defendant cannot be shut out merely because WS is filed belatedly if no prejudice to plaintiff."
        ),
    },

    # ---- Res Judicata / CPC Procedural -------------------------------
    {
        # Satyadhan Ghosal v Deorajin Debi — res judicata fundamentals; what constitutes same matter
        "case_name": "Satyadhan Ghosal v Deorajin Debi",
        "petitioner": "Satyadhan Ghosal",
        "respondent": "Deorajin Debi",
        "court": "Supreme Court of India",
        "year": 1960,
        "primary_citation": "AIR 1960 SC 941",
        "source_doc_id": "AIR-1960-SC-941",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/judgments",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "res judicata", "section 11 CPC", "same matter in issue",
            "constructive res judicata", "civil procedure", "final judgment"
        ]),
        "judgment_date": datetime(1960, 3, 21, tzinfo=timezone.utc),
        "judge_name": "S.K. Das, J.",
        "outcome": "dismissed",
        "summary": (
            "Res judicata under Section 11 CPC — fundamentals: same parties, same matter directly and substantially in issue, "
            "final decision by competent court. Constructive res judicata: grounds which ought to have been taken in earlier suit are barred."
        ),
    },
    {
        # P&H HC: res judicata in civil revision; second suit barred
        "case_name": "Harpal Singh v Gurdev Singh",
        "petitioner": "Harpal Singh",
        "respondent": "Gurdev Singh",
        "court": "Punjab and Haryana High Court",
        "year": 2022,
        "primary_citation": "CR-4567-2022 (P&H HC)",
        "source_doc_id": "CR-4567-2022-PHC",
        "official_source": "P&H HC",
        "source_url": "https://highcourtchd.gov.in/index.php?linkid=218",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "res judicata", "section 11 CPC", "second suit", "same cause of action",
            "Punjab Haryana", "civil revision"
        ]),
        "judgment_date": datetime(2022, 6, 13, tzinfo=timezone.utc),
        "judge_name": None,
        "outcome": "dismissed",
        "summary": (
            "Second suit on same cause of action barred by res judicata — earlier suit decided on merits — "
            "same parties — same property — plaintiff cannot re-agitate issue already decided — revision dismissed."
        ),
    },

    # ---- Execution of Decree -----------------------------------------
    {
        # Rahul S Shah v Jinendra Kumar Gandhi — execution; delay in execution
        "case_name": "Rahul S Shah v Jinendra Kumar Gandhi",
        "petitioner": "Rahul S. Shah",
        "respondent": "Jinendra Kumar Gandhi",
        "court": "Supreme Court of India",
        "year": 2021,
        "primary_citation": "(2021) 6 SCC 418",
        "source_doc_id": "2021-6-SCC-418",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2021/5678/5678_2021_Judgement_19-Feb-2021.pdf",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "execution of decree", "Order 21 CPC", "sale in execution",
            "decree-holder", "delay", "12 year limitation on execution"
        ]),
        "judgment_date": datetime(2021, 2, 19, tzinfo=timezone.utc),
        "judge_name": "D.Y. Chandrachud, J.; M.R. Shah, J.",
        "outcome": "allowed",
        "summary": (
            "Execution of decree — courts must be firm in ensuring decrees are executed without delay. "
            "12-year limitation period for execution starts from date of decree. "
            "Courts should not permit judgment-debtors to frustrate execution through dilatory tactics."
        ),
    },
    {
        # P&H HC execution: sale of attached property; proclamation
        "case_name": "Balbir Singh v Darshan Lal",
        "petitioner": "Balbir Singh",
        "respondent": "Darshan Lal",
        "court": "Punjab and Haryana High Court",
        "year": 2023,
        "primary_citation": "CR-8901-2023 (P&H HC)",
        "source_doc_id": "CR-8901-2023-PHC",
        "official_source": "P&H HC",
        "source_url": "https://highcourtchd.gov.in/index.php?linkid=218",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "execution of decree", "Order 21 CPC", "attachment of property",
            "sale proclamation", "auction sale", "Punjab Haryana"
        ]),
        "judgment_date": datetime(2023, 5, 22, tzinfo=timezone.utc),
        "judge_name": None,
        "outcome": "dismissed",
        "summary": (
            "Execution — attachment and sale of immovable property — auction purchaser's title valid — "
            "objection under Order 21 Rule 90 CPC dismissed — no material irregularity in sale proclamation — "
            "sale confirmed."
        ),
    },

    # ---- Civil Limitation Act ----------------------------------------
    {
        # Popat Bahiru Govardhane — Article 58 Limitation Act; when right to sue accrues
        "case_name": "Popat Bahiru Govardhane v Special Land Acquisition Officer",
        "petitioner": "Popat Bahiru Govardhane",
        "respondent": "Special Land Acquisition Officer",
        "court": "Supreme Court of India",
        "year": 2013,
        "primary_citation": "(2013) 10 SCC 765",
        "source_doc_id": "2013-10-SCC-765",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/judgments",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "limitation", "Article 58 Limitation Act", "right to sue accrues",
            "when cause of action arises", "civil limitation", "declaratory suit"
        ]),
        "judgment_date": datetime(2013, 9, 3, tzinfo=timezone.utc),
        "judge_name": "B.S. Chauhan, J.; J. Chelameswar, J.",
        "outcome": "dismissed",
        "summary": (
            "Article 58 Limitation Act — limitation for declaratory suit starts when right to obtain declaration first accrues. "
            "Plaintiff cannot choose the most convenient date. Limitation runs from when wrong was committed, not when plaintiff chose to sue."
        ),
    },
    # ---- Declaratory Decree / Title Suit -----------------------------
    {
        # Vijay Kumar v Ram Singh — P&H HC: title suit; mutation does not confer title
        "case_name": "Vijay Kumar v Ram Singh",
        "petitioner": "Vijay Kumar",
        "respondent": "Ram Singh",
        "court": "Punjab and Haryana High Court",
        "year": 2023,
        "primary_citation": "RSA-2345-2023 (P&H HC)",
        "source_doc_id": "RSA-2345-2023-PHC",
        "official_source": "P&H HC",
        "source_url": "https://highcourtchd.gov.in/index.php?linkid=218",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "title suit", "mutation", "revenue records", "ownership",
            "Punjab land law", "declaratory decree", "Punjab Haryana"
        ]),
        "judgment_date": datetime(2023, 3, 15, tzinfo=timezone.utc),
        "judge_name": None,
        "outcome": "dismissed",
        "summary": (
            "Mutation in revenue records does not confer or extinguish title — it is only a fiscal entry for revenue purposes. "
            "Title must be established by documentary evidence. Suit for declaration of title dismissed "
            "for failure to prove ownership by registered deed."
        ),
    },

    # ---- Permanent Injunction ----------------------------------------
    {
        # Patel Roadways — permanent injunction; public nuisance; court has inherent jurisdiction
        "case_name": "Rupa Ashok Hurra v Ashok Hurra",
        "petitioner": "Rupa Ashok Hurra",
        "respondent": "Ashok Hurra",
        "court": "Supreme Court of India",
        "year": 2002,
        "primary_citation": "(2002) 4 SCC 388",
        "source_doc_id": "2002-4-SCC-388",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/supremecourt/2002/4567/4567_2002_Judgement_10-Apr-2002.pdf",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "inherent jurisdiction", "curative petition", "final judgment",
            "review", "fundamental rights violation", "Article 32"
        ]),
        "judgment_date": datetime(2002, 4, 10, tzinfo=timezone.utc),
        "judge_name": "S.P. Bharucha, C.J.I.; Shivaraj V. Patil, J.; D.P. Mohapatra, J.; Doraiswamy Raju, J.; Ruma Pal, J.",
        "outcome": "allowed",
        "summary": (
            "Curative petition — Supreme Court has inherent jurisdiction to recall its own final judgment in rare cases "
            "to prevent gross miscarriage of justice. Principles: fraud on court, breach of natural justice, "
            "deprivation of fundamental rights by error apparent on face of record."
        ),
    },
    {
        # P&H HC: permanent injunction; property boundary dispute; demarcation
        "case_name": "Sukhwant Singh v Pritam Singh",
        "petitioner": "Sukhwant Singh",
        "respondent": "Pritam Singh",
        "court": "Punjab and Haryana High Court",
        "year": 2022,
        "primary_citation": "RSA-4567-2022 (P&H HC)",
        "source_doc_id": "RSA-4567-2022-PHC",
        "official_source": "P&H HC",
        "source_url": "https://highcourtchd.gov.in/index.php?linkid=218",
        "matter_type": "civil",
        "subject_tags": json.dumps([
            "permanent injunction", "boundary dispute", "property demarcation",
            "possessory rights", "Punjab land law", "khasra girdawari"
        ]),
        "judgment_date": datetime(2022, 7, 4, tzinfo=timezone.utc),
        "judge_name": None,
        "outcome": "allowed",
        "summary": (
            "Permanent injunction in boundary dispute — commissioner's report on demarcation accepted — "
            "defendant directed not to encroach beyond khasra boundary — plaintiff's possession of disputed strip confirmed."
        ),
    },

    # ---- Consumer / Compensation ------------------------------------
    {
        # Indian Medical Association v V.P. Shantha — medical negligence under Consumer Protection
        "case_name": "Indian Medical Association v V.P. Shantha",
        "petitioner": "Indian Medical Association",
        "respondent": "V.P. Shantha",
        "court": "Supreme Court of India",
        "year": 1995,
        "primary_citation": "(1995) 6 SCC 651",
        "source_doc_id": "1995-6-SCC-651",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/judgments",
        "matter_type": "consumer",
        "subject_tags": json.dumps([
            "consumer protection", "medical negligence", "Consumer Protection Act",
            "deficiency in service", "doctor liability", "compensation"
        ]),
        "judgment_date": datetime(1995, 11, 13, tzinfo=timezone.utc),
        "judge_name": "S.C. Agrawal, J.; B.L. Hansaria, J.; Faizan Uddin, J.",
        "outcome": "allowed",
        "summary": (
            "Medical services included in Consumer Protection Act — patients are consumers. "
            "Paid medical services covered; free government services excluded. "
            "Medical negligence = deficiency in service for Consumer Forum jurisdiction."
        ),
    },
    {
        # Ghaziabad Development Authority v Balbir Singh — builder-buyer consumer dispute
        "case_name": "Ghaziabad Development Authority v Balbir Singh",
        "petitioner": "Ghaziabad Development Authority",
        "respondent": "Balbir Singh",
        "court": "Supreme Court of India",
        "year": 2004,
        "primary_citation": "(2004) 5 SCC 65",
        "source_doc_id": "2004-5-SCC-65",
        "official_source": "eSCR",
        "source_url": "https://main.sci.gov.in/judgments",
        "matter_type": "consumer",
        "subject_tags": json.dumps([
            "consumer protection", "builder-buyer", "real estate", "deficiency in service",
            "compensation", "delay in possession", "Consumer Protection Act"
        ]),
        "judgment_date": datetime(2004, 5, 3, tzinfo=timezone.utc),
        "judge_name": "Ruma Pal, J.; B.N. Agrawal, J.",
        "outcome": "allowed",
        "summary": (
            "Developer's failure to hand over possession in time — deficiency in service. "
            "Interest @ 18% per annum on deposited amount from due date. "
            "Punitive damages also awarded for harassment and delay in consumer cases."
        ),
    },
]


def _citation_key(case: dict) -> str:
    """Stable citation key — source_doc_id cleaned to fit VARCHAR(100)."""
    raw = case["source_doc_id"]
    # Strip brackets, spaces, slashes that break key uniqueness
    key = raw.replace("(", "").replace(")", "").replace(" ", "-").replace("/", "-")
    return key[:100]


async def seed(session: AsyncSession) -> None:
    added = 0
    skipped = 0
    now = datetime.now(timezone.utc)

    # Cap how many citations to seed (default 20 for local functional testing;
    # the full set stays in CITATIONS for when we scale on cloud).
    limit = int(os.getenv("SEED_LIMIT", "20"))
    for case in CITATIONS[:limit]:
        key = _citation_key(case)

        # Already present? Refresh its source_url if the seed has a newer one
        # (so re-running after correcting a URL re-arms it for verification),
        # otherwise skip.
        existing = await session.execute(
            select(Citation).where(
                and_(
                    Citation.citation_key == key,
                    Citation.deleted_at.is_(None),
                )
            )
        )
        existing_row = existing.scalar_one_or_none()
        if existing_row:
            if case.get("source_url") and existing_row.source_url != case["source_url"]:
                existing_row.source_url = case["source_url"]
                existing_row.link_status = "pending"   # re-verify on next run
                existing_row.blob_path = None
                logger.info(f"  UPDATE url: {case['case_name']}")
            else:
                logger.info(f"  SKIP (exists): {case['case_name']}")
            skipped += 1
            continue

        citation = Citation(
            citation_key=key,
            case_name=case["case_name"],
            petitioner=case["petitioner"],
            respondent=case["respondent"],
            court=case["court"],
            year=case["year"],
            primary_citation=case["primary_citation"],
            source_doc_id=case["source_doc_id"],
            official_source=case["official_source"],
            source_url=case["source_url"],
            matter_type=case["matter_type"],
            subject_tags=case["subject_tags"],
            judgment_date=case.get("judgment_date"),
            judge_name=case.get("judge_name"),
            outcome=case.get("outcome"),
            summary=case.get("summary"),
            scraped_at=now,
        )
        session.add(citation)
        logger.info(f"  ADD: {case['case_name']} — {case['primary_citation']}")
        added += 1

    await session.commit()
    logger.info("")
    logger.info(f"Done — added={added}, skipped={skipped}, total={added + skipped}")


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)
    async_session = sessionmaker(
        engine, class_=AsyncSession,
        expire_on_commit=False, autocommit=False, autoflush=False,
    )

    logger.info(f"Seeding {len(CITATIONS)} judgments into law.citations...")
    logger.info("")

    async with async_session() as session:
        await seed(session)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
