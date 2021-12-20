import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd, numpy as np
import os, sys, math, time, smtplib
import matplotlib.pyplot as plt
import warnings
import logging
from pandas.plotting import register_matplotlib_converters

register_matplotlib_converters()
logger = logging.getLogger(__name__)


def createDb(parentDir):
    fields = ["datetime", "current", "peak", "onAir"]
    df = pd.DataFrame(columns=fields)
    dbName = datetime.now().strftime("%a-%d-%b-%Y__%Hh%Mm%Ss")
    xlsFile = os.path.join(parentDir, dbName + ".xlsx")
    df.to_excel(xlsFile, index=False)

    return xlsFile


def scrape(url):
    page = requests.get(url)
    soup = BeautifulSoup(page.text, "html.parser")
    sys.setrecursionlimit(8000)
    currentTime = datetime.now()
    audienceDict = dict()
    lstStreamData = soup.find_all(class_="streamstats")

    if len(lstStreamData) > 0:
        audienceDict["datetime"] = currentTime
        audienceDict["current"] = int(lstStreamData[2].get_text())
        audienceDict["peak"] = int(lstStreamData[3].get_text())
        audienceDict["onAir"] = True
        audienceDict["connectionError"] = False
    else:
        audienceDict["datetime"] = currentTime
        audienceDict["current"] = math.nan
        audienceDict["peak"] = math.nan
        audienceDict["onAir"] = False
        audienceDict["connectionError"] = False

    return audienceDict


def errorSolver():
    audienceDict = dict()
    audienceDict["datetime"] = datetime.now()
    audienceDict["current"] = math.nan
    audienceDict["peak"] = math.nan
    audienceDict["onAir"] = False
    audienceDict["connectionError"] = True

    return audienceDict


def updateDb(audienceDict, xlsx):
    df = pd.read_excel(xlsx)
    df = df.append(audienceDict, ignore_index=True)
    df.to_excel(xlsx, index=False)


def getDownTimeCount(audienceDict, downTimeCount):
    onAir = audienceDict["onAir"]
    connectionError = audienceDict["connectionError"]
    return downTimeCount + 1 if (onAir is False) or (connectionError is True) else 0


def printScrapeState(downTimeCount, maxDownTimeCount):
    print(
        "{} |--> downTimeCount = {} [maxDownTimeCount: {}]".format(
            datetime.now().strftime("%H:%M:%S"), downTimeCount, maxDownTimeCount
        )
    )


def plot(xlsx, smoothOverMins=None, saveFigure=False):
    """
    Args:
        xlsx: full path of the xlsx storing the scraped data
        smoothOverMins: (int) number of minutes over which to smooth the audience estimate (default=None)
        saveFigure: (bool)

    """

    df = pd.read_excel(xlsx)
    sessionDate = df["datetime"][0].strftime("%a-%d-%b-%Y")

    fig = plt.figure(figsize=(19.0, 10.0))
    plt.fill_between(df["datetime"], df["current"], color="cornflowerblue", alpha=0.2)

    if smoothOverMins:
        scrapeEverySecs = np.median(np.diff(df["datetime"]) / np.timedelta64(1, "s"))
        scrapesPerMin = int(60 / scrapeEverySecs)
        winLength = smoothOverMins * scrapesPerMin
        smoothed = df["current"].rolling(window=winLength, center=True).median()
        plt.plot(df["datetime"], smoothed, color="orange")

    else:
        plt.plot(df["datetime"], df["current"], color="cornflowerblue")

    plt.ylabel("Ascoltatori", fontsize=12)
    plt.grid(axis="y", ls=":"), plt.ylim([0, np.nanmax(df["current"]) + 5])
    plt.title("Radio Lockdown: {}".format(sessionDate), fontweight="bold")

    if saveFigure:
        path, file = os.path.split(xlsx)
        figName = "audience-" + file.split(".")[0] + ".png"
        fig.canvas.start_event_loop(sys.float_info.min)
        plt.savefig(os.path.join(path, figName), bbox_inches="tight")


def getCurrentAudience(xlsx):
    df = pd.read_excel(xlsx)
    current = df["current"].iloc[-1]
    peak = df["peak"].iloc[-1]

    return current, peak


def evaluatePerformance(xlsx, evalNminutes, numScrapesInOneMin):
    def _pctChange(last, current):
        if math.isnan(last) or math.isnan(current) or last == 0:
            return math.nan
        else:
            return 100 * ((current - last) / last)

    samplesPerChunk = numScrapesInOneMin * evalNminutes
    df = pd.read_excel(xlsx)
    currentChunk = df["current"].iloc[-samplesPerChunk:]
    lastChunk = df["current"].iloc[-samplesPerChunk * 2 : -samplesPerChunk]
    perfMetrics = dict()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        perfMetrics["meanLastMins"] = currentChunk.mean()
        perfMetrics["medianLastMins"] = currentChunk.median()
        perfMetrics["pctChange"] = _pctChange(lastChunk.median(), currentChunk.median())

    return perfMetrics


def sendUpdate(receivers, txt, subject=None, loginFile=None):
    def _send(receiver, txt, subject, loginFile):

        with open(loginFile, "r") as f:
            fileTxt = f.read()

        # IMPORTANT: fileTxt must be a one-line str organized as 'senderAddress_pwd'
        senderAddress = fileTxt.split("_")[0]
        pwd = fileTxt.split("_")[1]

        header = (
            "To:"
            + receiver
            + "\n"
            + "From: "
            + senderAddress
            + "\n"
            + "Subject: "
            + subject
            + " \n"
        )
        msg = header + "\n" + "\n" + txt + "\n\n"

        smtpserver = smtplib.SMTP("smtp.gmail.com", 587)
        smtpserver.ehlo()
        smtpserver.starttls()
        smtpserver.ehlo()
        smtpserver.login(senderAddress, pwd)
        smtpserver.sendmail(senderAddress, receiver, msg)
        smtpserver.close()
        print("Email sent to: " + receiver)

    try:

        if loginFile:
            subject = subject if subject else "RadioLockDown: Periodic Update"

            # if only one receiver:
            if isinstance(receivers, str):
                receiver = receivers
                _send(receiver, txt, subject, loginFile)

            # if multiple receivers:
            elif isinstance(receivers, list):
                for receiver in receivers:
                    _send(receiver, txt, subject, loginFile)

            else:
                print("NO Email sent: error in receivers' format")

        else:
            print("NO Email sent: loginFile not provided")

    except:
        print(
            "NO Email sent: check if correct loginfile or receivers address were provided"
        )


def run(parameters=None):
    """
    run audience scraping, update database, plot once finished.

    Args:
        parameters: (dict) with the following key:value fields

             "xlsPath": (str) path where to store the excel with the scraped data
             "scrape_every_n_seconds": (int) scrape audience every ... seconds
             "max_downtime_minutes": (int) number of consecutive minutes with server:down to stop scraping
             "update_every_n_minutes": (int) send periodic update every ... minutes
             "perf_eval_every_n_minutes": (int) interval to use to evaluate performance
             "min_listeners_percent_variation": (int) min value to send notification
             "send_update_to": (str or list of str) with the email address
             "send_perf_eval_to": (str or list of str) with the email address
             "mail_login_file": (str) path of the txt file storing the gmail credentials of the sender address (*)

             (*) txt file with only one line with text formatted as: gmailadress_pwd

    """

    defaultParams = {
        "xlsPath": r"P:\WORK\PYTHONPATH\RUG\projects\autoradiolockdown\ruggero-dev\audience\scrapedData\xls",
        "scrape_every_n_seconds": 30,
        "max_downtime_minutes": 10,
        "update_every_n_minutes": 10,
        "perf_eval_every_n_minutes": 5,
        "min_listeners_percent_variation": 10,
        "send_update_to": "rug.bettinardi@gmail.com",
        "send_perf_eval_to": [
            "rug.bettinardi@gmail.com",
            "radiolockdownparis@gmail.com",
        ],
        "mail_login_file": None,
    }

    # check / update input parameters:
    if parameters:
        params = dict()
        for dp in defaultParams:
            if dp not in parameters:
                params[dp] = defaultParams[dp]
            else:
                params[dp] = parameters[dp]
    else:
        params = defaultParams

    # define variables:
    scrape_every_n_seconds = params["scrape_every_n_seconds"]
    max_downtime_minutes = params["max_downtime_minutes"]
    update_every_n_minutes = params["update_every_n_minutes"]
    perf_eval_every_n_minutes = params["perf_eval_every_n_minutes"]
    min_listeners_percent_variation = params["min_listeners_percent_variation"]
    send_update_to = params["send_update_to"]
    send_perf_eval_to = params["send_perf_eval_to"]
    mail_login_file = params["mail_login_file"]

    # create database:
    dbDir = params["xlsPath"]
    xlsFile = createDb(parentDir=dbDir)

    # setting iteration parameters:
    maxDownTimeCount = int((max_downtime_minutes * 60) / scrape_every_n_seconds)
    scrapesInOneMinute = int(60 / scrape_every_n_seconds)
    downTimeCount = 0
    cumulativeCount = 0
    perfFlag = 0

    # run scraping routine:
    while downTimeCount <= maxDownTimeCount:

        printScrapeState(downTimeCount, maxDownTimeCount)

        try:
            currentAudienceDict = scrape("http://radiolockdown.club:8000/")
            downTimeCount = getDownTimeCount(currentAudienceDict, downTimeCount)

            # update audience database:
            try:
                updateDb(currentAudienceDict, xlsFile)

            # or create new one if requested database is unreachable:
            except:
                xlsFile = createDb(dbDir)
                updateDb(currentAudienceDict, xlsFile)

            # send periodic update Email every N minutes:
            if cumulativeCount % (scrapesInOneMinute * update_every_n_minutes) == 0:
                current, peak = getCurrentAudience(xlsFile)
                txt = "current listeners: {},\n" "peak listeners: {}\n".format(
                    current, peak
                )

                # add performance metrics if possible:
                if (
                    cumulativeCount
                    >= scrapesInOneMinute * perf_eval_every_n_minutes * 2
                ):
                    perfMetrics = evaluatePerformance(
                        xlsFile, perf_eval_every_n_minutes, scrapesInOneMinute
                    )
                    txt = (
                        txt + "median over last {} min: {},\n"
                        "percent change over last {} min: {}%\n"
                        "".format(
                            perf_eval_every_n_minutes,
                            perfMetrics["medianLastMins"],
                            perf_eval_every_n_minutes,
                            int(perfMetrics["pctChange"]),
                        )
                    )

                sendUpdate(send_update_to, txt, loginFile=mail_login_file)

            # performance evaluation every N minutes:
            if (
                cumulativeCount > scrapesInOneMinute * (perf_eval_every_n_minutes * 2)
                and cumulativeCount > perfFlag
            ):
                perfFlag = cumulativeCount + (
                    scrapesInOneMinute * perf_eval_every_n_minutes
                )
                perfMetrics = evaluatePerformance(
                    xlsFile, perf_eval_every_n_minutes, scrapesInOneMinute
                )

                # send update only if variation is over defined threshold:
                if abs(perfMetrics["pctChange"]) >= min_listeners_percent_variation:
                    current, peak = getCurrentAudience(xlsFile)
                    txt = (
                        "median number of listeners over last {} min: {},\n"
                        "percent change over last {} min: {}%\n\n"
                        "current listeners: {},\n"
                        "peak listeners so far: {}\n"
                        "".format(
                            perf_eval_every_n_minutes,
                            perfMetrics["medianLastMins"],
                            perf_eval_every_n_minutes,
                            int(perfMetrics["pctChange"]),
                            current,
                            peak,
                        )
                    )

                    mailSubject = "RadioLockDown: {}% variation in listeners!".format(
                        int(perfMetrics["pctChange"])
                    )
                    sendUpdate(
                        send_perf_eval_to,
                        txt,
                        subject=mailSubject,
                        loginFile=mail_login_file,
                    )

        except:
            currentAudienceDict = errorSolver()
            downTimeCount = getDownTimeCount(currentAudienceDict, downTimeCount)

        time.sleep(scrape_every_n_seconds)
        cumulativeCount += 1

    # plot results when finished
    plot(xlsx=xlsFile, smoothOverMins=10, saveFigure=True)

    print("audience scraping: finished")


if __name__ == "__main__":

    mails = ["rug.bettinardi@gmail.com"]
    paramsDict = {
        "xlsPath": r"P:\WORK\PYTHONPATH\RUG\projects\autoradiolockdown\ruggero-dev\audience\scrapedData\xls",
        "scrape_every_n_seconds": 15,
        "max_downtime_minutes": 4,
        "update_every_n_minutes": 5,
        "perf_eval_every_n_minutes": 5,
        "min_listeners_percent_variation": 20,
        "send_update_to": "rug.bettinardi@gmail.com",
        "send_perf_eval_to": mails,
        "mail_login_file": r"P:\WORK\PYTHONPATH\RUG\docs\login-dev-gmail.txt",
    }
    run(paramsDict)
