import functools
import json
import pandas as pd
from analyze import *


def read_json(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


RULES = read_json("rule.json").get("Rules")


@functools.cache
def match_rule(url, title) -> str:
    for _, rule in RULES.items():
        if any(link in url for link in rule["links"]):
            return rule["name"]
        if any(keyword in title for keyword in rule["titles"]):
            return rule["name"]
    return "其他"


def filter_data(data: pd.DataFrame, year: int) -> pd.DataFrame:
    data = data[data["Date"].dt.year == year]
    data = data[data["Title"].notnull()]
    data = data[data["URL"].notnull()]
    return data


def read_chrome_data(history_path: str, year: int) -> pd.DataFrame:
    data = read_json(history_path).get("Browser History")
    data = pd.DataFrame(data)
    data["Date"] = pd.to_datetime(data["time_usec"], unit="us")
    data["Date"] = data["Date"].dt.tz_localize("UTC").dt.tz_convert("Asia/Shanghai")
    data.rename(columns={"title": "Title", "url": "URL"}, inplace=True)
    data = data[["Title", "URL", "Date"]]
    data = filter_data(data, year)
    data = data.iloc[::-1]
    return data


def read_safari_data(history_path: str, year: int) -> pd.DataFrame:
    import sqlite3

    conn = sqlite3.connect(history_path)
    query = """
    SELECT 
        history_visits.visit_time as Date,
        history_items.url as URL,
        history_visits.title as Title
    FROM 
        history_visits
    JOIN 
        history_items
    ON 
        history_visits.history_item = history_items.id
    ORDER BY 
        visit_time ASC
    """

    data = pd.read_sql_query(query, conn)
    # Safari 使用的是秒时间戳, 从 2001-01-01 开始
    data["Date"] = pd.to_datetime(data["Date"], unit="s", origin="2001-01-01")
    data["Date"] = data["Date"].dt.tz_localize("UTC").dt.tz_convert("Asia/Shanghai")
    data = filter_data(data, year)
    return data


def read_data(history_path: str, year: int, type: str) -> pd.DataFrame:
    if type == "auto":
        if history_path.endswith(".json"):  # 默认是 Chrome 的历史记录
            return read_chrome_data(history_path, year)
        elif history_path.endswith(".db"):  # 默认 Safari 的历史记录
            return read_safari_data(history_path, year)
        else:
            raise ValueError("不支持的文件格式, 请使用 .json 或 .db 文件")
    elif type == "google":
        if not history_path.endswith(".json"):
            raise ValueError("请使用 Chrome 的历史记录文件")
        return read_chrome_data(history_path, year)
    elif type == "safari":
        if not history_path.endswith(".db"):
            raise ValueError("请使用 Safari 的历史记录文件")
        return read_safari_data(history_path, year)


def read_data_list(files: list, year: int, type: str) -> pd.DataFrame:
    dfs = []
    for file in files:
        dfs.append(read_data(file, year, type))
    if len(dfs) == 1:
        return dfs[0]
    # 合并所有 DataFrame，确保按时间排序
    merged_df = pd.concat(dfs, ignore_index=True)
    merged_df = merged_df.sort_values(by="Date")
    return merged_df


def main(
    files: list,
    year: int,
    type: str,
    output_path: str = "output.json",
    wordcloud_path="dist/wordcloud.png",
):
    df = read_data_list(files, year, type)
    print("历史记录读取成功", flush=True)
    df["Category"] = df.apply(
        lambda x: match_rule(x["URL"].lower(), x["Title"].lower()), axis=1
    )

    # df[df["Category"] == "其他"][["Title", "URL"]].to_json(
    #     "a.json", orient="records", force_ascii=False, indent=4
    # )

    # 分析数据
    calculate_duration(df)
    day, day_time = most_long_day_count(df)
    month_counts = every_month_count(df)
    domain_counts = domain_count(df)
    max_day, max_day_c = max_day_count(df)
    latest_sleep, earliest_wake = find_extreme_sleep_times(df)
    category_counts = category_count(df)
    first_half, second_half = hourly_visit_split(df)
    word_cloud(df, wordcloud_path)

    json_results = {
        "每月访问量": {
            "月份": list(
                map(lambda x: str(x)[-2:].lstrip("0") + "月", month_counts.index)
            ),
            "访问次数": month_counts.to_list(),
        },
        "最常访问的域名": domain_counts.to_dict(),
        "类型占比": category_counts.to_dict(),
        "前半天访问量": first_half.to_list(),
        "后半天访问量": second_half.to_list(),
    }
    # 渲染模板
    days = len(df["Date"].dt.date.unique())
    count = len(df)
    avg = int(count / days)
    with open("dist/template.html", "r", encoding="utf-8") as f:
        content = f.read()
        content = (
            content.replace("{{ OUTPUTJSON }}", str(json_results))
            # 年份
            .replace("{{ YEAR }}", str(year))
            # 总访问次数
            .replace("{{ COUNT }}", str(count))
            # 总天数
            .replace("{{ DAYS }}", str(days))
            # 平均每天访问次数
            .replace("{{ AVG }}", str(avg))
            # 最长访问时间的日期
            .replace("{{ LONGEST_DAY }}", str(day))
            # 最长日期的访问时长
            .replace("{{ LONGEST_DAY_TIME }}", str(day_time))
            # 最多访问的日期
            .replace("{{ MAX_DAY }}", str(max_day))
            # 最多访问的次数
            .replace("{{ MAX_DAY_C }}", str(max_day_c))
            # 最晚睡时间
            .replace(
                "{{ LATEST_SLEEP_DAY }}",
                latest_sleep["Date"].strftime("%m月%d日").lstrip("0"),
            )
            .replace(
                "{{ LATEST_SLEEP_TIME }}",
                latest_sleep["Date"].strftime("%H:%M"),
            )
            # 最晚睡标题
            .replace("{{ LATEST_SLEEP_TITLE }}", str(latest_sleep["Title"]))
            # 最早起时间
            .replace(
                "{{ EARLIEST_WAKE_DAY }}",
                earliest_wake["Date"].strftime("%m月%d日").lstrip("0"),
            )
            .replace(
                "{{ EARLIEST_WAKE_TIME }}",
                earliest_wake["Date"].strftime("%H:%M"),
            )
            # 最早起标题
            .replace("{{ EARLIEST_WAKE_TITLE }}", str(earliest_wake["Title"]))
        )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(json_results, f, ensure_ascii=False, indent=4)
    print(f"分析结果已保存到 {output_path}")

    with open("dist/index.html", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"打开 dist/index.html 查看你的 {args.year} 年浏览历史分析结果吧")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="处理浏览记录并生成统计报告")
    parser.add_argument(
        "files", type=str, nargs="+", help="浏览记录文件路径, 可以指定多个文件"
    )
    parser.add_argument("-y", "--year", type=int, default=2024, help="指定年份")
    parser.add_argument(
        "-t",
        "--type",
        type=str,
        choices=["google", "safari", "auto"],
        default="auto",
        help="指定浏览记录类型 (google, safari, auto)",
    )
    args = parser.parse_args()
    main(args.files, args.year, args.type)
