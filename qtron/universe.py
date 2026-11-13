"""Qtron universe: every instrument the app follows. Edit here to add or remove instruments.
Format of U rows: (ticker, name, asset_class, group). STOCKS: space-separated Yahoo symbols per (class, group);
"SYMBOL=Name" gives a display name. Anything Yahoo cannot serve is skipped automatically."""
import pandas as pd

U = [
    # ── Cash ────────────────────────────────────────────────────────────────
    ("BIL", "1-3M T-Bill", "Cash", "T-Bills"), ("SGOV", "0-3M Treasury", "Cash", "T-Bills"),
    ("SHV", "Short Treasury", "Cash", "T-Bills"),
    # ── Sovereign bonds ─────────────────────────────────────────────────────
    ("SHY", "UST 1-3Y", "Sovereign Bonds", "US Treasuries"), ("IEI", "UST 3-7Y", "Sovereign Bonds", "US Treasuries"),
    ("IEF", "UST 7-10Y", "Sovereign Bonds", "US Treasuries"), ("TLT", "UST 20Y+", "Sovereign Bonds", "US Treasuries"),
    ("TIP", "US TIPS", "Sovereign Bonds", "Inflation-Linked"), ("VTIP", "Short TIPS", "Sovereign Bonds", "Inflation-Linked"),
    ("BWX", "Intl Treasuries", "Sovereign Bonds", "Global Sovereign"), ("IGOV", "Intl Govt Bonds", "Sovereign Bonds", "Global Sovereign"),
    ("EMB", "EM USD Sovereign", "Sovereign Bonds", "EM Sovereign"), ("EMLC", "EM Local Sovereign", "Sovereign Bonds", "EM Sovereign"),
    # ── Credit ──────────────────────────────────────────────────────────────
    ("LQD", "IG Corporate", "Credit", "Investment Grade"), ("VCIT", "Interm. Corporate", "Credit", "Investment Grade"),
    ("VCSH", "Short Corporate", "Credit", "Investment Grade"),
    ("HYG", "High Yield", "Credit", "High Yield"), ("JNK", "High Yield (SPDR)", "Credit", "High Yield"),
    ("BKLN", "Senior Loans", "Credit", "High Yield"),
    ("MUB", "Municipals", "Credit", "Munis & MBS"), ("MBB", "Agency MBS", "Credit", "Munis & MBS"),
    # ── US equities: indices ────────────────────────────────────────────────
    ("SPY", "S&P 500", "US Equities", "US Indices"), ("QQQ", "Nasdaq 100", "US Equities", "US Indices"),
    ("IWM", "Russell 2000", "US Equities", "US Indices"), ("DIA", "Dow 30", "US Equities", "US Indices"),
    ("MDY", "S&P MidCap 400", "US Equities", "US Indices"), ("RSP", "S&P 500 Equal Wt", "US Equities", "US Indices"),
    # ── US equities: sectors (ETF + leading single stocks) ──────────────────
    ("XLK", "Technology", "US Equities", "Technology"), ("AAPL", "Apple", "US Equities", "Technology"),
    ("MSFT", "Microsoft", "US Equities", "Technology"), ("NVDA", "NVIDIA", "US Equities", "Technology"),
    ("AVGO", "Broadcom", "US Equities", "Technology"), ("SMH", "Semiconductors", "US Equities", "Technology"),
    ("XLC", "Communication", "US Equities", "Communication"), ("GOOGL", "Alphabet", "US Equities", "Communication"),
    ("META", "Meta", "US Equities", "Communication"), ("NFLX", "Netflix", "US Equities", "Communication"),
    ("XLY", "Cons. Discretionary", "US Equities", "Cons. Discretionary"), ("AMZN", "Amazon", "US Equities", "Cons. Discretionary"),
    ("TSLA", "Tesla", "US Equities", "Cons. Discretionary"), ("HD", "Home Depot", "US Equities", "Cons. Discretionary"),
    ("XLP", "Cons. Staples", "US Equities", "Cons. Staples"), ("PG", "Procter & Gamble", "US Equities", "Cons. Staples"),
    ("KO", "Coca-Cola", "US Equities", "Cons. Staples"), ("WMT", "Walmart", "US Equities", "Cons. Staples"),
    ("XLF", "Financials", "US Equities", "Financials"), ("JPM", "JPMorgan", "US Equities", "Financials"),
    ("BAC", "Bank of America", "US Equities", "Financials"), ("GS", "Goldman Sachs", "US Equities", "Financials"),
    ("KRE", "Regional Banks", "US Equities", "Financials"),
    ("XLV", "Health Care", "US Equities", "Health Care"), ("LLY", "Eli Lilly", "US Equities", "Health Care"),
    ("UNH", "UnitedHealth", "US Equities", "Health Care"), ("JNJ", "Johnson & Johnson", "US Equities", "Health Care"),
    ("XLE", "Energy", "US Equities", "Energy Equities"), ("XOM", "Exxon Mobil", "US Equities", "Energy Equities"),
    ("CVX", "Chevron", "US Equities", "Energy Equities"),
    ("XLI", "Industrials", "US Equities", "Industrials"), ("CAT", "Caterpillar", "US Equities", "Industrials"),
    ("GE", "GE Aerospace", "US Equities", "Industrials"), ("BA", "Boeing", "US Equities", "Industrials"),
    ("XLB", "Materials", "US Equities", "Materials"), ("LIN", "Linde", "US Equities", "Materials"),
    ("FCX", "Freeport-McMoRan", "US Equities", "Materials"),
    ("XLU", "Utilities", "US Equities", "Utilities"), ("NEE", "NextEra", "US Equities", "Utilities"),
    ("XLRE", "Real Estate", "US Equities", "Real Estate"), ("PLD", "Prologis", "US Equities", "Real Estate"),
    # ── Europe ──────────────────────────────────────────────────────────────
    ("VGK", "Europe Broad", "Europe Equities", "Europe"), ("EZU", "Eurozone", "Europe Equities", "Europe"),
    ("EWG", "Germany", "Europe Equities", "Europe"), ("EWU", "United Kingdom", "Europe Equities", "Europe"),
    ("EWQ", "France", "Europe Equities", "Europe"), ("EWI", "Italy", "Europe Equities", "Europe"),
    ("EWP", "Spain", "Europe Equities", "Europe"), ("EWL", "Switzerland", "Europe Equities", "Europe"),
    ("EWN", "Netherlands", "Europe Equities", "Europe"), ("EWD", "Sweden", "Europe Equities", "Europe"),
    # ── Asia-Pacific developed ──────────────────────────────────────────────
    ("EWJ", "Japan", "Asia-Pacific Equities", "Developed Asia"), ("EWA", "Australia", "Asia-Pacific Equities", "Developed Asia"),
    ("EWH", "Hong Kong", "Asia-Pacific Equities", "Developed Asia"), ("EWS", "Singapore", "Asia-Pacific Equities", "Developed Asia"),
    ("EWY", "South Korea", "Asia-Pacific Equities", "Developed Asia"), ("EWT", "Taiwan", "Asia-Pacific Equities", "Developed Asia"),
    # ── Emerging markets ────────────────────────────────────────────────────
    ("EEM", "EM Broad", "EM Equities", "Emerging Markets"), ("FXI", "China Large-Cap", "EM Equities", "Emerging Markets"),
    ("KWEB", "China Internet", "EM Equities", "Emerging Markets"), ("INDA", "India", "EM Equities", "Emerging Markets"),
    ("EWZ", "Brazil", "EM Equities", "Emerging Markets"), ("EWW", "Mexico", "EM Equities", "Emerging Markets"),
    ("EZA", "South Africa", "EM Equities", "Emerging Markets"), ("TUR", "Turkey", "EM Equities", "Emerging Markets"),
    ("EIDO", "Indonesia", "EM Equities", "Emerging Markets"), ("KSA", "Saudi Arabia", "EM Equities", "Emerging Markets"),
    # ── Commodities (ETF) ───────────────────────────────────────────────────
    ("GLD", "Gold", "Commodities", "Precious Metals"), ("SLV", "Silver", "Commodities", "Precious Metals"),
    ("PPLT", "Platinum", "Commodities", "Precious Metals"), ("GDX", "Gold Miners", "Commodities", "Precious Metals"),
    ("USO", "WTI Crude", "Commodities", "Energy"), ("BNO", "Brent Crude", "Commodities", "Energy"),
    ("UNG", "Natural Gas", "Commodities", "Energy"),
    ("CPER", "Copper", "Commodities", "Industrial Metals"), ("DBB", "Base Metals", "Commodities", "Industrial Metals"),
    ("DBA", "Agriculture", "Commodities", "Agriculture"), ("CORN", "Corn", "Commodities", "Agriculture"),
    ("WEAT", "Wheat", "Commodities", "Agriculture"), ("SOYB", "Soybeans", "Commodities", "Agriculture"),
    ("DBC", "Broad Commodities", "Commodities", "Broad Commodities"),
    # ── FX (ETF proxies carry volume; spot pairs are price-only) ────────────
    ("UUP", "US Dollar Index ETF", "FX", "US Dollar"), ("DX-Y.NYB", "DXY Index", "FX", "US Dollar"),
    ("FXE", "Euro ETF", "FX", "G10 FX"), ("FXY", "Yen ETF", "FX", "G10 FX"), ("FXB", "Sterling ETF", "FX", "G10 FX"),
    ("FXA", "Aussie ETF", "FX", "G10 FX"), ("FXC", "Loonie ETF", "FX", "G10 FX"), ("FXF", "Swiss Franc ETF", "FX", "G10 FX"),
    ("EURUSD=X", "EUR/USD", "FX", "Spot Pairs"), ("JPY=X", "USD/JPY", "FX", "Spot Pairs"),
    ("GBPUSD=X", "GBP/USD", "FX", "Spot Pairs"), ("AUDUSD=X", "AUD/USD", "FX", "Spot Pairs"),
    ("CAD=X", "USD/CAD", "FX", "Spot Pairs"), ("CHF=X", "USD/CHF", "FX", "Spot Pairs"),
    ("CNY=X", "USD/CNY", "FX", "Spot Pairs"), ("MXN=X", "USD/MXN", "FX", "Spot Pairs"),
    # ── Futures & derivative proxies ────────────────────────────────────────
    ("ES=F", "S&P 500 E-mini", "Futures & Vol", "Equity Futures"), ("NQ=F", "Nasdaq E-mini", "Futures & Vol", "Equity Futures"),
    ("RTY=F", "Russell E-mini", "Futures & Vol", "Equity Futures"),
    ("ZN=F", "10Y T-Note Fut", "Futures & Vol", "Rates Futures"), ("ZB=F", "30Y T-Bond Fut", "Futures & Vol", "Rates Futures"),
    ("ZT=F", "2Y T-Note Fut", "Futures & Vol", "Rates Futures"),
    ("CL=F", "WTI Crude Fut", "Futures & Vol", "Commodity Futures"), ("NG=F", "Nat Gas Fut", "Futures & Vol", "Commodity Futures"),
    ("GC=F", "Gold Fut", "Futures & Vol", "Commodity Futures"), ("SI=F", "Silver Fut", "Futures & Vol", "Commodity Futures"),
    ("HG=F", "Copper Fut", "Futures & Vol", "Commodity Futures"), ("ZC=F", "Corn Fut", "Futures & Vol", "Commodity Futures"),
    ("^VIX", "VIX Index", "Futures & Vol", "Volatility"), ("VIXY", "VIX Short-Term Fut", "Futures & Vol", "Volatility"),
    ("SVXY", "Short VIX", "Futures & Vol", "Volatility"),
    # ── Crypto ──────────────────────────────────────────────────────────────
    ("BTC-USD", "Bitcoin", "Crypto", "Crypto"), ("ETH-USD", "Ethereum", "Crypto", "Crypto"),
    ("SOL-USD", "Solana", "Crypto", "Crypto"), ("IBIT", "Bitcoin ETF", "Crypto", "Crypto"),
]

STOCKS = {
    ("US Stocks", "Technology"): "ORCL CRM ADBE AMD CSCO ACN IBM INTU QCOM TXN NOW AMAT MU LRCX KLAC ADI PANW SNPS CDNS CRWD ANET APH MSI FTNT "
        "ADSK ROP NXPI MCHP TEL ON HPQ DELL HPE GLW KEYS CDW FICO IT MPWR SMCI PLTR WDAY SNOW DDOG TEAM ZS NET MDB MRVL ARM INTC TER STX WDC "
        "NTAP GEN AKAM FSLR ENPH SHOP",
    ("US Stocks", "Communication"): "DIS CMCSA T VZ TMUS CHTR EA TTWO WBD OMC LYV SPOT PINS RBLX TTD MTCH FOXA NWSA",
    ("US Stocks", "Cons. Discretionary"): "MCD NKE LOW SBUX BKNG TJX ABNB MAR HLT GM F ORLY AZO ROST CMG YUM DHI LEN LULU EBAY RCL CCL DRI ULTA "
        "TSCO BBY EXPE LVS MGM APTV DPZ NVR PHM GRMN DECK MELI DASH",
    ("US Stocks", "Cons. Staples"): "PEP COST PM MO MDLZ CL TGT KMB GIS STZ KDP MNST HSY SYY KR ADM KHC EL CHD CLX DG DLTR TSN HRL CAG MKC BF-B",
    ("US Stocks", "Financials"): "BRK-B V MA WFC MS C AXP SCHW BLK SPGI CB PGR MMC ICE CME AON USB PNC TFC COF MCO AIG MET PRU TRV ALL AFL BK "
        "STT FITB MTB HBAN RF KEY CFG NTRS AMP MSCI NDAQ PYPL FIS GPN COIN HOOD KKR BX APO SYF",
    ("US Stocks", "Health Care"): "ABBV MRK PFE TMO ABT DHR AMGN BMY GILD CVS ELV CI ISRG MDT SYK VRTX REGN ZTS BSX BDX HCA MCK COR CAH HUM "
        "IDXX IQV A EW DXCM RMD MRNA BIIB ILMN MTD WST ZBH BAX GEHC CNC MOH ALGN",
    ("US Stocks", "Energy"): "COP EOG SLB MPC PSX VLO OXY WMB KMI OKE DVN FANG HAL BKR TRGP EQT CTRA APA",
    ("US Stocks", "Industrials"): "HON UNP UPS RTX LMT DE ADP ETN ITW EMR GD NOC WM CSX NSC FDX MMM PH TT CARR PCAR JCI CMI ROK ODFL FAST PAYX "
        "CTAS URI GWW AME OTIS VRSK RSG LHX TDG HWM DAL UAL LUV AAL IR XYL DOV WAB UBER GEV AXON",
    ("US Stocks", "Materials"): "SHW APD ECL NEM DOW DD NUE CTVA PPG VMC MLM IFF ALB STLD CF MOS BALL IP",
    ("US Stocks", "Utilities"): "SO DUK D AEP SRE EXC XEL PEG ED WEC ES AWK DTE ETR PPL CEG VST PCG",
    ("US Stocks", "Real Estate"): "AMT EQIX CCI PSA O SPG WELL DLR VICI AVB EQR SBAC WY ARE INVH EXR",
    ("Europe Stocks", "Netherlands"): "ASML.AS=ASML INGA.AS=ING AD.AS=Ahold_Delhaize PHIA.AS=Philips HEIA.AS=Heineken UNA.AS=Unilever PRX.AS=Prosus "
        "ADYEN.AS=Adyen WKL.AS=Wolters_Kluwer ASM.AS=ASM_International KPN.AS=KPN NN.AS=NN_Group AKZA.AS=Akzo_Nobel SHELL.AS=Shell "
        "MT.AS=ArcelorMittal RAND.AS=Randstad BESI.AS=BE_Semiconductor ABN.AS=ABN_AMRO AGN.AS=Aegon UMG.AS=Universal_Music EXO.AS=Exor IMCD.AS=IMCD",
    ("Europe Stocks", "Belgium"): "ABI.BR=AB_InBev KBC.BR=KBC UCB.BR=UCB ARGX.BR=argenx SOLB.BR=Solvay AGS.BR=Ageas GBLB.BR=GBL UMI.BR=Umicore "
        "ACKB.BR=Ackermans_vH COLR.BR=Colruyt PROX.BR=Proximus ELI.BR=Elia SOF.BR=Sofina DIE.BR=D'Ieteren MELE.BR=Melexis LOTB.BR=Lotus_Bakeries "
        "WDP.BR=WDP AED.BR=Aedifica COFB.BR=Cofinimmo SYENS.BR=Syensqo AZE.BR=Azelis",
    ("Europe Stocks", "Germany"): "SAP.DE=SAP SIE.DE=Siemens ALV.DE=Allianz DTE.DE=Deutsche_Telekom AIR.DE=Airbus MBG.DE=Mercedes-Benz BMW.DE=BMW "
        "VOW3.DE=Volkswagen BAS.DE=BASF BAYN.DE=Bayer MUV2.DE=Munich_Re IFX.DE=Infineon DHL.DE=DHL DB1.DE=Deutsche_Boerse DBK.DE=Deutsche_Bank "
        "RWE.DE=RWE EOAN.DE=E.ON ADS.DE=Adidas HEN3.DE=Henkel MRK.DE=Merck_KGaA RHM.DE=Rheinmetall SHL.DE=Siemens_Healthineers ENR.DE=Siemens_Energy "
        "CBK.DE=Commerzbank HEI.DE=Heidelberg_Materials FRE.DE=Fresenius BEI.DE=Beiersdorf CON.DE=Continental DTG.DE=Daimler_Truck MTX.DE=MTU_Aero "
        "P911.DE=Porsche VNA.DE=Vonovia ZAL.DE=Zalando SY1.DE=Symrise HNR1.DE=Hannover_Re QIA.DE=Qiagen BNR.DE=Brenntag",
    ("Europe Stocks", "France"): "MC.PA=LVMH OR.PA=L'Oreal RMS.PA=Hermes TTE.PA=TotalEnergies SAN.PA=Sanofi SU.PA=Schneider_Electric AI.PA=Air_Liquide "
        "BNP.PA=BNP_Paribas CS.PA=AXA EL.PA=EssilorLuxottica SAF.PA=Safran DG.PA=Vinci KER.PA=Kering BN.PA=Danone RI.PA=Pernod_Ricard CAP.PA=Capgemini "
        "ACA.PA=Credit_Agricole GLE.PA=Societe_Generale ENGI.PA=Engie ORA.PA=Orange SGO.PA=Saint-Gobain ML.PA=Michelin DSY.PA=Dassault_Systemes "
        "STLAP.PA=Stellantis HO.PA=Thales LR.PA=Legrand VIE.PA=Veolia PUB.PA=Publicis RNO.PA=Renault STMPA.PA=STMicroelectronics CA.PA=Carrefour",
    ("Europe Stocks", "United Kingdom"): "SHEL.L=Shell AZN.L=AstraZeneca HSBA.L=HSBC ULVR.L=Unilever BP.L=BP GSK.L=GSK RIO.L=Rio_Tinto DGE.L=Diageo "
        "REL.L=RELX BATS.L=British_American_Tobacco LSEG.L=LSE_Group NG.L=National_Grid BARC.L=Barclays LLOY.L=Lloyds RR.L=Rolls-Royce BA.L=BAE_Systems "
        "GLEN.L=Glencore CPG.L=Compass AAL.L=Anglo_American TSCO.L=Tesco VOD.L=Vodafone PRU.L=Prudential NWG.L=NatWest STAN.L=Standard_Chartered "
        "HLN.L=Haleon RKT.L=Reckitt III.L=3i EXPN.L=Experian AHT.L=Ashtead IMB.L=Imperial_Brands SSE.L=SSE BT-A.L=BT",
    ("Europe Stocks", "Switzerland"): "NESN.SW=Nestle ROG.SW=Roche NOVN.SW=Novartis UBSG.SW=UBS ZURN.SW=Zurich ABBN.SW=ABB CFR.SW=Richemont SIKA.SW=Sika "
        "LONN.SW=Lonza HOLN.SW=Holcim GIVN.SW=Givaudan SREN.SW=Swiss_Re ALC.SW=Alcon PGHN.SW=Partners_Group SLHN.SW=Swiss_Life GEBN.SW=Geberit",
    ("Europe Stocks", "Spain & Italy"): "ITX.MC=Inditex IBE.MC=Iberdrola SAN.MC=Santander BBVA.MC=BBVA CABK.MC=CaixaBank TEF.MC=Telefonica REP.MC=Repsol "
        "AMS.MC=Amadeus FER.MC=Ferrovial AENA.MC=Aena CLNX.MC=Cellnex ENEL.MI=Enel ISP.MI=Intesa_Sanpaolo UCG.MI=UniCredit ENI.MI=Eni RACE.MI=Ferrari "
        "G.MI=Generali PRY.MI=Prysmian LDO.MI=Leonardo MONC.MI=Moncler TRN.MI=Terna SRG.MI=Snam",
    ("Europe Stocks", "Nordics"): "NOVO-B.CO=Novo_Nordisk DSV.CO=DSV MAERSK-B.CO=Maersk VWS.CO=Vestas CARL-B.CO=Carlsberg ORSTED.CO=Orsted "
        "ATCO-A.ST=Atlas_Copco INVE-B.ST=Investor VOLV-B.ST=Volvo ERIC-B.ST=Ericsson SAND.ST=Sandvik HM-B.ST=H&M ASSA-B.ST=Assa_Abloy SEB-A.ST=SEB "
        "SWED-A.ST=Swedbank EQNR.OL=Equinor DNB.OL=DNB NOKIA.HE=Nokia NESTE.HE=Neste KNEBV.HE=Kone SAMPO.HE=Sampo NDA-FI.HE=Nordea",
    ("Asia Stocks", "Japan"): "7203.T=Toyota 6758.T=Sony 8306.T=MUFG 6861.T=Keyence 9984.T=SoftBank_Group 6098.T=Recruit 9432.T=NTT 8035.T=Tokyo_Electron "
        "4063.T=Shin-Etsu 6501.T=Hitachi 7974.T=Nintendo 9983.T=Fast_Retailing 8058.T=Mitsubishi_Corp 8001.T=Itochu 8031.T=Mitsui 4502.T=Takeda "
        "4568.T=Daiichi_Sankyo 6902.T=Denso 7267.T=Honda 8316.T=SMFG 8411.T=Mizuho 6367.T=Daikin 6954.T=Fanuc 7741.T=Hoya 6981.T=Murata 4519.T=Chugai "
        "9433.T=KDDI 6702.T=Fujitsu 7011.T=Mitsubishi_Heavy 6857.T=Advantest 8766.T=Tokio_Marine 6273.T=SMC 4661.T=Oriental_Land 6594.T=Nidec "
        "7751.T=Canon 6752.T=Panasonic 2914.T=Japan_Tobacco 3382.T=Seven_&_i 6146.T=Disco 6920.T=Lasertec",
    ("Asia Stocks", "China & Hong Kong"): "0700.HK=Tencent 9988.HK=Alibaba 3690.HK=Meituan 1299.HK=AIA 0005.HK=HSBC_HK 0939.HK=CCB 1398.HK=ICBC "
        "2318.HK=Ping_An 0941.HK=China_Mobile 1810.HK=Xiaomi 9618.HK=JD.com 1211.HK=BYD 0388.HK=HKEX 0883.HK=CNOOC 2020.HK=Anta 9999.HK=NetEase "
        "9888.HK=Baidu 0981.HK=SMIC 2269.HK=WuXi_Biologics 1024.HK=Kuaishou 0027.HK=Galaxy_Entertainment 0016.HK=SHK_Properties 0001.HK=CK_Hutchison "
        "3988.HK=Bank_of_China 0857.HK=PetroChina 0386.HK=Sinopec 2628.HK=China_Life 1109.HK=CR_Land 0175.HK=Geely 2015.HK=Li_Auto 9868.HK=XPeng "
        "600519.SS=Kweichow_Moutai 300750.SZ=CATL",
    ("Asia Stocks", "Korea & Taiwan"): "005930.KS=Samsung_Electronics 000660.KS=SK_Hynix 373220.KS=LG_Energy 207940.KS=Samsung_Biologics "
        "005380.KS=Hyundai_Motor 000270.KS=Kia 035420.KS=Naver 035720.KS=Kakao 051910.KS=LG_Chem 006400.KS=Samsung_SDI 105560.KS=KB_Financial "
        "055550.KS=Shinhan 012330.KS=Hyundai_Mobis 068270.KS=Celltrion 005490.KS=POSCO 2330.TW=TSMC 2317.TW=Hon_Hai 2454.TW=MediaTek 2308.TW=Delta "
        "2382.TW=Quanta 2881.TW=Fubon 2882.TW=Cathay 2412.TW=Chunghwa_Telecom 3711.TW=ASE 2303.TW=UMC 2891.TW=CTBC 1301.TW=Formosa_Plastics",
    ("Asia Stocks", "India"): "RELIANCE.NS=Reliance TCS.NS=TCS HDFCBANK.NS=HDFC_Bank INFY.NS=Infosys ICICIBANK.NS=ICICI_Bank HINDUNILVR.NS=Hindustan_Unilever "
        "ITC.NS=ITC SBIN.NS=State_Bank_of_India BHARTIARTL.NS=Bharti_Airtel LT.NS=Larsen_&_Toubro BAJFINANCE.NS=Bajaj_Finance KOTAKBANK.NS=Kotak_Bank "
        "AXISBANK.NS=Axis_Bank MARUTI.NS=Maruti_Suzuki SUNPHARMA.NS=Sun_Pharma TITAN.NS=Titan ASIANPAINT.NS=Asian_Paints HCLTECH.NS=HCL_Tech "
        "WIPRO.NS=Wipro M&M.NS=Mahindra NTPC.NS=NTPC ADANIENT.NS=Adani_Enterprises TATASTEEL.NS=Tata_Steel",
    ("Asia Stocks", "Australia & Singapore"): "BHP.AX=BHP CBA.AX=Commonwealth_Bank CSL.AX=CSL NAB.AX=NAB WBC.AX=Westpac ANZ.AX=ANZ MQG.AX=Macquarie "
        "WES.AX=Wesfarmers WOW.AX=Woolworths RIO.AX=Rio_Tinto_AU FMG.AX=Fortescue TLS.AX=Telstra WDS.AX=Woodside GMG.AX=Goodman TCL.AX=Transurban "
        "D05.SI=DBS O39.SI=OCBC U11.SI=UOB Z74.SI=Singtel",
}

# Stock-market indices themselves (not investable; shown for reference and used as benchmarks)
U += [(t, n, "Indices", g) for g, lst in {
    "Index VS": [("^GSPC", "S&P 500"), ("^NDX", "Nasdaq 100"), ("^IXIC", "Nasdaq Composite"), ("^DJI", "Dow Jones"), ("^RUT", "Russell 2000"), ("^SOX", "Semiconductor Index")],
    "Index Europa": [("^STOXX50E", "Euro Stoxx 50"), ("^STOXX", "Stoxx Europe 600"), ("^GDAXI", "DAX"), ("^FCHI", "CAC 40"), ("^FTSE", "FTSE 100"), ("^AEX", "AEX"),
                     ("^BFX", "BEL 20"), ("^SSMI", "SMI"), ("^IBEX", "IBEX 35"), ("FTSEMIB.MI", "FTSE MIB")],
    "Index Azië": [("^N225", "Nikkei 225"), ("^HSI", "Hang Seng"), ("000001.SS", "Shanghai Composite"), ("^KS11", "KOSPI"), ("^TWII", "Taiwan Weighted"),
                   ("^NSEI", "Nifty 50"), ("^AXJO", "ASX 200"), ("^STI", "Straits Times")]}.items() for t, n in lst]

_core = {u[0] for u in U}
_rows = []
for (_c, _g), _txt in STOCKS.items():
    for _tok in _txt.split():
        _t, _, _n = _tok.partition("=")
        if _t not in _core:
            _rows.append((_t, _n.replace("_", " ") or _t, _c, _g))
BASE_STOCKS = {r[0] for r in _rows}          # the hand-picked list the frozen patterns were defined on
try:                                        # data-driven extension: all large US listings (see build_universe.py)
    from pathlib import Path as _P
    for _f in ("universe_extra.tsv", "universe_world.tsv"):
        _fp = _P(__file__).with_name(_f)
        if _fp.exists():
            _x = pd.read_csv(_fp, sep="\t", dtype=str).dropna()
            _seen = _core | {r[0] for r in _rows}
            _rows += [tuple(r) for r in _x[["ticker", "name", "cls", "group"]].itertuples(index=False) if r[0] not in _seen]
except Exception:
    pass
META = pd.DataFrame(U + _rows, columns=["ticker", "name", "cls", "group"]).drop_duplicates("ticker").set_index("ticker")
META["core"] = META.index.isin(_core)
META["base"] = META.index.isin(BASE_STOCKS)      # core = cross-asset ETFs/futures/FX that drive pools, regime and the live view
STOCK_CLASSES = ["US Stocks", "Europe Stocks", "Asia Stocks"]
