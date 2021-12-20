import pandas as pd, numpy as np
import matplotlib.pyplot as plt
import os

# paths:
srcXls = r'P:\WORK\PYTHONPATH\RUG\projects\autoradiolockdown\ruggero-dev\audience\scrapedData\xls'
first = os.path.join(srcXls, r'Thu-12-Nov-2020__20h58m15s.xls')
second = os.path.join(srcXls, r'Thu-12-Nov-2020__22h32m06s.xls')

# load and merge:
df1 = pd.read_excel(first)
df2 = pd.read_excel(second)
df = df1.append(df2, ignore_index=True)

sessionDate = df['datetime'][0].strftime("%a-%d-%b-%Y")

# save merged df:
df.to_excel(os.path.join(srcXls, 'older', sessionDate + '.xls'), index=False)

# plot:
plt.figure()
plt.fill_between(df['datetime'], df['current'], color="cornflowerblue", alpha=0.3)
plt.plot(df['datetime'], df['current'], color="cornflowerblue")
plt.ylabel('Ascoltatori', fontsize=12)
plt.grid(axis='y', ls=':')
plt.title('Radio Lockdown: {}'.format(sessionDate), fontweight='bold')