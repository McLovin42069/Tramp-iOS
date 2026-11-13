import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research2"); import lib2
import numpy as np, pandas as pd
pd.set_option("display.width",250); pd.set_option("display.max_rows",500)
L = lib2.load_long()
C,O,V=L["C"],L["O"],L["V"]
on,day = lib2.session_returns(L)
