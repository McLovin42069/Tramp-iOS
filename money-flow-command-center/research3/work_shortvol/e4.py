from base import *
r1=ratio(1); m250=r1.rolling(250,min_periods=120).mean()
ev(out(-(ratio(20)-m250)),10,"neg_r20_m250")
ev(out(-(ratio(60)-m250)),5,"neg_r60_m250")
ev(out(-(ratio(60)-m250)),20,"neg_r60_m250")
ev(out(-(ratio(10)-m250)),5,"neg_r10_m250")
ev(out(-(ratio(20)-r1.rolling(120,min_periods=60).mean())),5,"neg_r20_m120")
ev(out(-lib3.residual(ratio(20)-m250,D)),5,"neg_r20_m250_secneutral")
