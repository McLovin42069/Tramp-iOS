import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research3"); import lib3
import numpy as np, pandas as pd
pd.set_option("display.width",250); pd.set_option("display.max_columns",40); pd.set_option("display.max_rows",200)
L = lib3.us_calendar(lib3.load_long())
P = L["spdr_premium_pct"]; C = L["C"]; S = L["spdr"]
tr = [t for t in P.columns if t in C.columns]
