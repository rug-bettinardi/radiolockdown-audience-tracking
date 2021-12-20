import os
import pandas as pd
import matplotlib.pyplot as plt
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()

"""
plot audience boxplot: one boxplot per episode
plot median audience over time across episodes 

"""

xlsDir = r"P:\WORK\PYTHONPATH\RUG\projects\autoradiolockdown\ruggero-dev\audience\scrapedData\xls\puntatePassate"

for xlsFile in os.listdir(xlsDir):

    print(xlsFile)

    df = pd.read_excel(os.path.join(xlsDir, xlsFile))
    plt.plot(df["datetime"], df["current"])

