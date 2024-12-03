import pandas as pd
import jieba
from wordcloud import WordCloud

FONT_PATH = "./dist/static/fonts/方正黑体简体.ttf"  # 可以替换为其他字体文件


# 规避 Windows 下 strftime 不支持中文的问题
def month_day(time: pd.Timestamp):
    return str(time.month) + "月" + str(time.day) + "日"


def year_month_day(time: pd.Timestamp):
    return str(time.year) + "年" + str(time.month) + "月" + str(time.day) + "日"


def calculate_duration(data: pd.DataFrame):
    time_diff = (data["Date"] - data["Date"].shift(1)).dt.total_seconds() / 3600
    # 对于相隔不超过1小时的记录，记录时间差
    data["Duration"] = time_diff.where(time_diff <= 1, 0)


def domain_count(data: pd.DataFrame, fisrt_n: int = 10):
    return (
        data["URL"]
        .apply(lambda x: x.split("/")[2] if "://" in x else "Invalid URL")
        .value_counts()
        .head(fisrt_n)
    )


def every_month_count(data: pd.DataFrame):
    monthly_counts = data.groupby(data["Date"].dt.to_period("M")).size()
    return monthly_counts


def max_day_count(data: pd.DataFrame) -> tuple:
    day_duration = data.groupby(data["Date"].dt.date).size()
    return year_month_day(day_duration.idxmax()), day_duration.max()


def category_count(data: pd.DataFrame):
    return data["Category"].value_counts().head(5).apply(lambda x: x / len(data))


def find_extreme_sleep_times(data: pd.DataFrame):
    data["Time"] = data["Date"].dt.time
    data["Adjusted Time"] = data["Time"].apply(
        lambda x: (x.hour + 24 - 4) % 24 * 60 * 60 + x.minute * 60 + x.second
    )
    latest_sleep_time = data.loc[data["Adjusted Time"].idxmax()]
    earliest_wake_time = data.loc[data["Adjusted Time"].idxmin()]
    return latest_sleep_time, earliest_wake_time


def most_long_day_count(data: pd.DataFrame):
    # 计算每日访问时间
    day_duration = data.groupby(data["Date"].dt.date)["Duration"].sum()
    return month_day(day_duration.idxmax()), int(day_duration.max())


def hourly_visit_split(data: pd.DataFrame):
    data["Hour"] = data["Date"].dt.hour
    first_half = (
        data[(data["Hour"] >= 0) & (data["Hour"] < 12)]
        .groupby("Hour")["Duration"]
        .sum()
    )
    second_half = (
        data[(data["Hour"] >= 12) & (data["Hour"] < 24)]
        .groupby("Hour")["Duration"]
        .sum()
    )
    first_half = first_half.reindex(range(0, 12), fill_value=0)
    second_half = second_half.reindex(range(12, 24), fill_value=0)
    return first_half, second_half


def find_peak_hourly_activity(data: pd.DataFrame, first_n: int = 3):
    data["Hour"] = data["Date"].dt.floor("h")  # 只保留小时部分
    hourly_activity = data["Hour"].value_counts().sort_index()
    peak_hour = hourly_activity.idxmax()
    peak_count = hourly_activity.max()
    peak_titles = data[data["Hour"] == peak_hour]["Title"]
    peak_titles = peak_titles.value_counts().head(first_n)
    return peak_hour, peak_titles, peak_count


def word_cloud(data: pd.DataFrame, file_name: str = "dist/wordcloud.png"):
    text = " ".join(jieba.cut(" ".join(data["Title"]))).replace("Google", "")
    try:
        import pathlib

        if not pathlib.Path(FONT_PATH).exists():
            pathlib.Path(FONT_PATH).parent.mkdir(parents=True, exist_ok=True)
            print("开始下载字体文件")
            import requests
            import shutil

            url = "https://github.com/wordshub/free-font/raw/master/assets/font/%E4%B8%AD%E6%96%87/%E6%96%B9%E6%AD%A3%E5%AD%97%E4%BD%93%E7%B3%BB%E5%88%97/%E6%96%B9%E6%AD%A3%E9%BB%91%E4%BD%93%E7%AE%80%E4%BD%93.ttf"
            response = requests.get(url, stream=True)
            with open(FONT_PATH, "wb") as out_file:
                shutil.copyfileobj(response.raw, out_file)
            del response
        wc = WordCloud(
            font_path=FONT_PATH,
            width=800,
            height=400,
            background_color="white",
            max_words=100,
        ).generate(text)
    except Exception as e:
        print(e)
        print("未找到字体文件，使用默认字体, 中文显示可能异常")
        wc = WordCloud(
            width=800,
            height=400,
            background_color="white",
            max_words=100,
        ).generate(text)
    wc.to_file(file_name)
    print("词云生成成功")
