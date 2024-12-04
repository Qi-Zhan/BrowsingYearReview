import datetime
import webbrowser
import functools
import json
import pandas as pd
from pathlib import Path

from analyze import *

CURRENT_DIR = Path(__file__).parent
RULE_PATH = CURRENT_DIR / "rule.json"
DIST_PATH = CURRENT_DIR / "dist"
INDEX_PATH = DIST_PATH / "index.html"
TEMPLATE_PATH = DIST_PATH / "template.html"
WORD_CLOUD_PATH = DIST_PATH / "wordcloud.png"
FONT_PATH = DIST_PATH.joinpath(
    "static", "fonts", "方正黑体简体.ttf"
)  # 可以替换为其他字体文件


def read_json(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


RULES = read_json(RULE_PATH).get("Rules")
TIME_ZONE = datetime.datetime.now().astimezone().tzinfo


@functools.cache
def match_rule(url, title) -> str:
    for _, rule in RULES.items():
        if any(link in url for link in rule["links"]):
            return rule["name"]
        if any(keyword in title for keyword in rule["titles"]):
            return rule["name"]
    return "其他"


def filter_data(data: pd.DataFrame, year: int) -> pd.DataFrame:
    if len(data) == 0:
        raise ValueError("没有找到有效的数据, 考虑使用手动导出的方式")
    data = data[data["Date"].dt.year == year]
    data = data[data["Title"].notnull()]
    data = data[data["URL"].notnull()]
    return data


def read_chrome_file(history_path: str, year: int) -> pd.DataFrame:
    data = read_json(history_path).get("Browser History")
    data = pd.DataFrame(data)
    data["Date"] = pd.to_datetime(data["time_usec"], unit="us")
    data["Date"] = data["Date"].dt.tz_localize("UTC").dt.tz_convert(TIME_ZONE)
    data.rename(columns={"title": "Title", "url": "URL"}, inplace=True)
    data = data[["Title", "URL", "Date"]]
    data = filter_data(data, year)
    data = data.iloc[::-1]
    return data


def read_safari_file(history_path: str, year: int) -> pd.DataFrame:
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
    data["Date"] = data["Date"].dt.tz_localize("UTC").dt.tz_convert(TIME_ZONE)
    data = filter_data(data, year)
    return data


def read_from_file(history_path: str, year: int, type: str) -> pd.DataFrame:
    if type == "auto":
        if history_path.endswith(".json"):  # 默认是 Chrome 的历史记录
            return read_chrome_file(history_path, year)
        elif history_path.endswith(".db"):  # 默认 Safari 的历史记录
            return read_safari_file(history_path, year)
        else:
            raise ValueError("不支持的文件格式, 请使用 .json 或 .db 文件")
    elif type == "google":
        if not history_path.endswith(".json"):
            raise ValueError("请使用 Chrome 的历史记录文件")
        return read_chrome_file(history_path, year)
    elif type == "safari":
        if not history_path.endswith(".db"):
            raise ValueError("请使用 Safari 的历史记录文件")
        return read_safari_file(history_path, year)
    assert False, "unreachable"


def read_data_list(files: list, year: int, type: str) -> pd.DataFrame:
    if len(files) > 0:
        dfs = []
        for file in files:
            dfs.append(read_from_file(file, year, type))
        if len(dfs) == 1:
            return dfs[0]
        # 合并所有 DataFrame，确保按时间排序
        merged_df = pd.concat(dfs, ignore_index=True)
        merged_df = merged_df.sort_values(by="Date")
        return merged_df
    else:
        from browser_history import get_history

        outputs = get_history()
        data = pd.DataFrame(outputs.histories, columns=["Date", "URL", "Title"])
        # print all unique year
        data = filter_data(data, year)
        data.sort_values(by="Date")
        return data


def analyze_data(df: pd.DataFrame, wordcloud_path: Path, font_path: Path) -> dict:

    df["Category"] = df.apply(
        lambda x: match_rule(x["URL"].lower(), x["Title"].lower()), axis=1
    )
    calculate_duration(df)
    day, day_time = most_long_day_count(df)
    month_counts = every_month_count(df)
    domain_counts = domain_count(df)
    max_day, max_day_c = max_day_count(df)
    latest_sleep, earliest_wake = find_extreme_sleep_times(df)
    category_counts = category_count(df)
    first_half, second_half = hourly_visit_split(df)
    peek_hour, peek_titles, peek_counts = find_peak_hourly_activity(df)
    word_cloud(df, wordcloud_path, font_path)

    count = len(df)
    days = len(df["Date"].dt.date.unique())
    avg = int(count / days)
    analysis_results = {
        "总访问次数": count,
        "总天数": days,
        "平均每天访问次数": avg,
        "每月访问量": {
            "月份": [f"{index.month}月" for index in month_counts.index],
            "访问次数": month_counts.to_list(),
        },
        "最常访问的域名": domain_counts.to_dict(),
        "类型占比": category_counts.to_dict(),
        "前半天访问量": first_half.to_list(),
        "后半天访问量": second_half.to_list(),
        "最长访问时间的日期": day,
        "最长日期的访问时长": day_time,
        "最多访问的日期": max_day,
        "最多访问的次数": int(max_day_c),
        "最晚睡时间": {
            "日期": month_day(latest_sleep["Date"]),
            "时间": latest_sleep["Date"].strftime("%H:%M"),
            "标题": latest_sleep["Title"],
        },
        "最早起时间": {
            "日期": month_day(earliest_wake["Date"]),
            "时间": earliest_wake["Date"].strftime("%H:%M"),
            "标题": earliest_wake["Title"],
        },
        # "高峰小时访问量": {
        #     "小时": peek_hour,
        #     "标题": peek_titles,
        #     "访问量": peek_counts,
        # },
    }

    return analysis_results


def generate_report(
    results: dict,
    year: int,
    output_path: Path,
    template_path: Path,
    index_path: Path,
):
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
        content = (
            content.replace("{{ OUTPUTJSON }}", str(results))
            .replace("{{ YEAR }}", str(year))
            .replace("{{ COUNT }}", str(results["总访问次数"]))
            .replace("{{ DAYS }}", str(results["总天数"]))
            .replace("{{ AVG }}", str(results["平均每天访问次数"]))
            .replace("{{ LONGEST_DAY }}", str(results["最长访问时间的日期"]))
            .replace("{{ LONGEST_DAY_TIME }}", str(results["最长日期的访问时长"]))
            .replace("{{ MAX_DAY }}", str(results["最多访问的日期"]))
            .replace("{{ MAX_DAY_C }}", str(results["最多访问的次数"]))
            .replace("{{ LATEST_SLEEP_DAY }}", results["最晚睡时间"]["日期"])
            .replace("{{ LATEST_SLEEP_TIME }}", results["最晚睡时间"]["时间"])
            .replace("{{ LATEST_SLEEP_TITLE }}", results["最晚睡时间"]["标题"])
            .replace("{{ EARLIEST_WAKE_DAY }}", results["最早起时间"]["日期"])
            .replace("{{ EARLIEST_WAKE_TIME }}", results["最早起时间"]["时间"])
            .replace("{{ EARLIEST_WAKE_TITLE }}", results["最早起时间"]["标题"])
        )
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(content)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)


def main(
    files: list,
    year: int,
    type: str,
    browser: bool,
):
    print(f"使用 {args.year} 年的数据进行分析", flush=True)
    print("读取数据中...", flush=True)
    df = read_data_list(files, year, type)
    print("历史记录读取成功", flush=True)

    print("正在分析数据...", flush=True)
    analysis_results = analyze_data(df, WORD_CLOUD_PATH, FONT_PATH)
    print("数据分析完成", flush=True)

    print("正在生成报告...", flush=True)
    generate_report(
        analysis_results, year, DIST_PATH / "output.json", TEMPLATE_PATH, INDEX_PATH
    )

    if browser:
        print("正在打开浏览器...", flush=True)
        try:
            webbrowser.open(INDEX_PATH.as_uri())
        except Exception as e:
            print(f"浏览器打开失败，请手动打开 {INDEX_PATH}. 错误: {e}")
    else:
        print(f"请打开 {INDEX_PATH} 查看结果")


if __name__ == "__main__":
    import argparse

    def default_year():
        today = datetime.date.today()
        return today.year - 1 if today.month <= 6 else today.year

    parser = argparse.ArgumentParser(description="处理浏览记录并生成统计报告")
    parser.add_argument(
        "files", type=str, nargs="*", help="浏览记录文件路径, 可以指定多个文件"
    )
    parser.add_argument(
        "-y",
        "--year",
        type=int,
        default=default_year(),
        help="指定年份（前6个月默认查看上一年，后6个月默认查看今年）",
    )
    parser.add_argument(
        "-t",
        "--type",
        type=str,
        choices=["google", "safari", "auto"],
        default="auto",
        help="指定浏览记录类型 (google, safari, auto)",
    )
    parser.add_argument(
        "--browser",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="是否使用浏览器打开生成的报告",
    )
    args = parser.parse_args()
    main(args.files, args.year, args.type, args.browser)
