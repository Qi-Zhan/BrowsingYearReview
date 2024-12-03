import pandas as pd
import jieba
from wordcloud import WordCloud

FONT_PATH = "~/Library/fonts/方正黑体_GBK.ttf"  # 请根据自己的字体路径修改


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
    return day_duration.idxmax().strftime("%Y年%m月%d日"), day_duration.max()


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


def calculate_duration(data: pd.DataFrame):
    time_diff = (data["Date"] - data["Date"].shift(1)).dt.total_seconds() / 3600
    # 对于相隔不超过1小时的记录，记录时间差
    data["Duration"] = time_diff.where(time_diff <= 1, 0)


def most_long_day_count(data: pd.DataFrame):
    # 计算每日访问时间
    day_duration = data.groupby(data["Date"].dt.date)["Duration"].sum()
    return day_duration.idxmax().strftime("%m月%d日").lstrip("0"), int(
        day_duration.max()
    )


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


def word_cloud(data: pd.DataFrame, file_name: str = "dist/wordcloud.png"):
    text = " ".join(jieba.cut(" ".join(data["Title"]))).replace("Google", "")
    try:
        wc = WordCloud(
            font_path=FONT_PATH,
            width=800,
            height=400,
            background_color="white",
            max_words=100,
        ).generate(text)
    except:
        print("未找到字体文件，使用默认字体, 中文显示可能异常")
        wc = WordCloud(
            width=800,
            height=400,
            background_color="white",
            max_words=100,
        ).generate(text)
    wc.to_file(file_name)
