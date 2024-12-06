function defaultYear() {
    const today = new Date();
    const year = today.getFullYear();
    const month = today.getMonth() + 1; // getMonth() returns 0-indexed months
    return month <= 3 ? year - 1 : year;
}

async function read_data_list(year) {
    const startOfYear = new Date(year, 0, 1).getTime();
    const endOfYear = new Date(year + 1, 0, 1).getTime();

    var historyItems = await chrome.history.search({
        text: "",
        startTime: startOfYear,
        endTime: endOfYear,
        maxResults: 1000000,
    });
    historyItems = historyItems.filter(item => item.url && item.title);
    return historyItems;
}

const OVERVIEW_PAGE = 1;
const WORD_CLOUD_PAGE = 2;
const DOMAIN_PAGE = 3;
const CATEGORY_PAGE = 4;
const MONTH_PAGE = 5;
const WEEK_PAGE = 6;
const HOUR_PAGE = 7;

const stopwords = new Set([
    'for', 'at', 'in', 'on', 'and', 'the', 'a', 'to', 'of', 'is', 'it', 'as', 'with', 'that', 'by', 'an', 'this', 'was', 'from', 'you', 'are'
]);

(async function () {

    Reveal.initialize({
        width: 1024, height: 768,
        slideNumber: false,
        controlsTutorial: false,
        progress: false,
        hash: true,
        center: false,
        touch: true,
        autoAnimateUnmatched: true,
        autoAnimateEasing: 'ease-out',
        autoAnimateDuration: 1.0,
        transitionSpeed: 'default',
        transition: 'slide', // zoom
    });

    const year = defaultYear();
    document.querySelector('title').textContent = `${year}年度总结`;
    document.getElementById('_1').textContent = `你的${year}年浏览记录年度总结🚀`;

    const historyItems = await read_data_list(year);
    if (historyItems.length == 0) {
        document.getElementById('_1').textContent = `未找到可用的${year}年的浏览记录😭`;
        return;
    }
    historyItems.sort((a, b) => b.lastVisitTime - a.lastVisitTime);
    const dates = historyItems.map(item => new Date(item.lastVisitTime));
    const urls = historyItems.map(item => item.url);
    const titles = historyItems.map(item => item.title);

    var rendered_page = new Set();
    Reveal.on('slidechanged', (event) => {
        if (rendered_page.has(event.indexh)) {
            return;
        }
        rendered_page.add(event.indexh);
        if (event.indexh != OVERVIEW_PAGE) {
            const typingSound = document.getElementById("typing-sound");
            typingSound.pause();
            typingSound.currentTime = 0;
        }

        switch (event.indexh) {
            case OVERVIEW_PAGE:
                generate_overview(year, dates, titles);
                break;
            case WORD_CLOUD_PAGE:
                generate_word_cloud(titles);
                break;
            case DOMAIN_PAGE:
                generate_domain_chart(urls);
                break;
            case CATEGORY_PAGE:
                generate_category_chart(urls, titles);
                break;
            case MONTH_PAGE:
                generate_month_chart(dates);
                break;
            case WEEK_PAGE:
                generate_weekday_chart(dates);
                break;
            case HOUR_PAGE:
                generate_hour_chart(dates);
                break;
            default:
                break;
        }
    });
})();

function generate_domain_chart(urls, first_n = 10) {
    function domain_count(urls, first_n = 10) {
        const domainCounts = {};
        urls.forEach(url => {
            var domain = url.split("/")[2] || "";
            if (domain === "") {
                return;
            }
            if (domain.startsWith("www.")) {
                domain = domain.slice(4);
            }
            domainCounts[domain] = (domainCounts[domain] || 0) + 1;
        });
        return Object.entries(domainCounts).sort((a, b) => b[1] - a[1]).slice(0, first_n);
    }
    const domainData = domain_count(urls, first_n);
    const labels = domainData.map(item => item[0]);
    const values = domainData.map(item => item[1]);
    const data = {
        labels: labels,
        datasets: [{
            label: '访问次数',
            data: values,
            backgroundColor: 'rgba(54, 162, 235, 0.2)',
            borderColor: 'rgba(54, 162, 235, 1)',
            borderWidth: 1
        }]
    };

    const config_domains = {
        type: 'bar',
        data: data,
        options: {
            indexAxis: 'y',
            animation: {
                duration: 1500, // 动画持续时间（以毫秒为单位）
                easing: 'easeOutBounce', // 动画缓动效果
                onComplete: () => {
                }
            },
            responsive: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: true
                }
            },
        }
    };
    new Chart(document.getElementById('Chart_domains'), config_domains);
}

function generate_word_cloud(titles) {
    const canvas = document.getElementById("word-cloud");
    const segmenter = new Intl.Segmenter('zh', { granularity: 'word' });
    const wordCounts = {};
    titles.forEach(item => {
        const title = (item || "").replace("Google", "").replace("搜索", "");
        if (title.includes("CC98")) {
            wordCounts["CC98"] = (wordCounts["CC98"] || 0) + 1;
        }
        const segments = Array.from(segmenter.segment(title));
        segments.forEach(segment => {
            const word = segment.segment; // 获取分词
            const normalizedWord = word;
            if (normalizedWord.length > 1 && /^[\u4e00-\u9fa5a-zA-Z]+$/.test(normalizedWord) && !stopwords.has(normalizedWord.toLowerCase())) {
                wordCounts[normalizedWord] = (wordCounts[normalizedWord] || 0) + 1;
            }
        });
    });
    const sortedWordCounts = Object.entries(wordCounts).sort((a, b) => b[1] - a[1]).slice(0, 100);
    const maxCount = sortedWordCounts[0][1];
    const minCount = sortedWordCounts[sortedWordCounts.length - 1][1];

    for (let i = 0; i < sortedWordCounts.length; i++) {
        sortedWordCounts[i][1] = ((sortedWordCounts[i][1] - minCount) * 100 / (maxCount - minCount)) + 16;
    }

    WordCloud(canvas, {
        list: sortedWordCounts,
        gridSize: 10,
        backgroundColor: '#f9f9f9',
    });
}

function generate_category_chart(urls, titles, first_n = 5) {
    const cached = {};
    function match_rule(url, title, cached = {}) {
        const cacheKey = JSON.stringify([url, title]);
        if (cached[cacheKey]) {
            return cached[cacheKey];
        }

        // 遍历规则
        for (const [_, rule] of Object.entries(rules)) {
            // 检查 URL 是否包含规则中的任意链接
            if (rule.links.some(link => url.includes(link))) {
                cached[cacheKey] = rule.name; // 缓存结果
                return rule.name;
            }
            // 检查标题是否包含规则中的任意关键字
            if (rule.titles.some(keyword => title.includes(keyword))) {
                cached[cacheKey] = rule.name; // 缓存结果
                return rule.name;
            }
        }

        return "其他";
    }
    categories = [];
    for (let i = 0; i < urls.length; i++) {
        categories.push(match_rule(urls[i], titles[i], cached));
    }
    const categoryData = {};
    categories.forEach(category => {
        categoryData[category] = (categoryData[category] || 0) + 1;
    }
    );
    const x = Object.entries(categoryData).sort((a, b) => b[1] - a[1]).slice(0, first_n);
    const category_labels = x.map(item => item[0]);
    var category_values = x.map(item => item[1]);
    const sum = category_values.reduce((a, b) => a + b, 0);
    category_values = category_values.map(item => item / sum);
    const config_category = {
        type: 'pie',
        data: {
            labels: category_labels,
            datasets: [{
                label: '占比',
                data: category_values,
                backgroundColor: [
                    'rgba(255, 99, 132, 0.2)',
                    'rgba(54, 162, 235, 0.2)',
                    'rgba(255, 206, 86, 0.2)',
                    'rgba(75, 192, 192, 0.2)',
                    'rgba(153, 102, 255, 0.2)',
                    'rgba(255, 159, 64, 0.2)',
                    'rgba(255, 99, 132, 0.2)',
                ],
                borderColor: [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)',
                    'rgba(255, 99, 132, 1)',
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            animation: {
                duration: 2000,
                easing: 'easeOut',
            }
        },
        plugins: [{
            id: 'customLabels',
            afterDatasetsDraw(chart) {
                const { ctx, chartArea: { width, height }, data } = chart;
                chart.data.datasets[0].data.forEach((value, index) => {
                    const meta = chart.getDatasetMeta(0).data[index];
                    const { x, y } = meta.tooltipPosition();
                    ctx.save();
                    ctx.fillStyle = 'black';
                    ctx.font = '16px Arial';
                    ctx.textAlign = 'center';
                    if (value > 0.1) {
                        ctx.fillText(`${data.labels[index]}: ${(value * 100).toFixed(0)}%`, x, y);
                    }
                    ctx.restore();
                });
            }
        }]
    }
    new Chart(document.getElementById('Chart_category'), config_category);
}

function generate_month_chart(dates) {
    function every_month_count(dates) {
        const monthCounts = Array.from({ length: 13 }, () => 0);
        dates.forEach(date => {
            const month = date.getMonth() + 1;
            monthCounts[month] += 1;
        });
        return monthCounts;
    }
    monthData = every_month_count(dates);
    const labels = Array.from({ length: 12 }, (_, i) => i + 1 + "月");
    const config_months = {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                data: monthData.slice(1),
                fill: false,
                borderColor: 'rgb(75, 192, 192)',
            }]
        },
        options: {
            animations: {
                tension: {
                    duration: 1000,
                    easing: 'linear',
                    from: 1,
                    to: 0,
                    loop: true
                }
            },
            plugins: {
                legend: {
                    display: false // 隐藏图例
                },
            }
        }
    };
    new Chart(document.getElementById('Chart_months'), config_months);
}

function generate_hour_chart(dates) {
    function hourly_count(dates) {
        const hourCounts = {};
        for (let i = 0; i < 24; i++) {
            hourCounts[i] = 0;
        }
        dates.forEach(date => {
            const hour = date.getHours();
            hourCounts[hour] += 1;
        });
        return hourCounts;
    }
    const hourData = hourly_count(dates);
    const first_half = Array.from({ length: 12 }, (_, i) => hourData[i]);
    const second_half = Array.from({ length: 12 }, (_, i) => hourData[i + 12]);

    const chart_colors = [
        'rgba(54, 162, 235, 0.8)', // 蓝色
        'rgba(75, 192, 192, 0.8)', // 青绿色
        'rgba(153, 102, 255, 0.8)', // 紫色
        'rgba(255, 159, 64, 0.8)',  // 橙色
        'rgba(255, 99, 132, 0.8)',  // 红色
        'rgba(201, 203, 207, 0.8)', // 灰色
        'rgba(255, 205, 86, 0.8)',  // 黄色
        'rgba(93, 173, 226, 0.8)',  // 天蓝色
        'rgba(46, 204, 113, 0.8)',  // 绿色
        'rgba(231, 76, 60, 0.8)',   // 深红色
        'rgba(241, 196, 15, 0.8)',  // 金色
        'rgba(127, 140, 141, 0.8)'  // 深灰色
    ];
    const ctx_first = document.getElementById('Chart_first_half').getContext('2d');
    const data_first = {
        labels: [...Array(12).keys()],
        datasets: [{
            label: '访问分布',
            data: first_half,
            backgroundColor: chart_colors,
            Width: 1
        }]
    };
    const config_first = {
        type: 'polarArea',
        data: data_first,
    };
    new Chart(ctx_first, config_first);
    const ctx_second = document.getElementById('Chart_second_half').getContext('2d');
    const data_second = {
        labels: [...Array(12).keys()].map(i => i + 12),
        datasets: [{
            label: '访问分布',
            data: second_half,
            backgroundColor: chart_colors,
            Width: 1
        }]
    };
    const config_second = {
        type: 'polarArea',
        data: data_second,
    };
    new Chart(ctx_second, config_second);
}

function generate_weekday_chart(dates) {
    function weekday_count(dates) {
        const weekdayCounts = Array.from({ length: 7 }, () => 0);
        dates.forEach(date => {
            const weekday = date.getDay();
            weekdayCounts[weekday] += 1;
        });
        return weekdayCounts;
    }
    const weekdayData = weekday_count(dates);
    const labels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
    const config_weekdays = {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '访问次数',
                data: weekdayData,
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: true
                }
            },
        }
    };
    new Chart(document.getElementById('Chart_weekdays'), config_weekdays);
}

function generate_overview(year, dates, titles) {
    function calculate_duration(dates) {
        const duration = [];
        duration.push(10);
        for (let i = 1; i < dates.length; i++) {
            // seconds
            const diff = (dates[i - 1] - dates[i]) / 1000;
            if (diff > 3600) {
                duration.push(10);
            } else {
                duration.push(diff);
            }

        }
        return duration;
    }

    function find_peak_hourly_activity(dates, titles, first_n = 5) {
        const hour = dates.map(date => new Date(date.getFullYear(), date.getMonth(), date.getDate(), date.getHours()));
        const hourCounts = {};
        hour.forEach(date => {
            hourCounts[date] = (hourCounts[date] || 0) + 1;
        });
        const peak = Object.entries(hourCounts).sort((a, b) => b[1] - a[1])[0];
        const peak_hour = new Date(peak[0]);
        const peak_count = peak[1];
        const peak_titles = [];
        for (let i = 0; i < dates.length; i++) {
            if (hour[i] - peak_hour == 0)
                peak_titles.push(titles[i]);
        }

        // 对这些标题进行分词统计
        const segmenter = new Intl.Segmenter('zh', { granularity: 'word' });
        const wordCounts = {};
        peak_titles.forEach(item => {
            const title = (item || "").replace("Google", "").replace("搜索", "");
            const segments = Array.from(segmenter.segment(title));
            segments.forEach(segment => {
                const word = segment.segment; // 获取分词
                const normalizedWord = word;
                if (normalizedWord.length > 1 && /^[\u4e00-\u9fa5a-zA-Z]+$/.test(normalizedWord) && !stopwords.has(normalizedWord.toLowerCase())) {
                    wordCounts[normalizedWord] = (wordCounts[normalizedWord] || 0) + 1;
                }
            });
        });
        const sortedWordCounts = Object.entries(wordCounts).sort((a, b) => b[1] - a[1]).slice(0, first_n);
        const peak_titles_str = sortedWordCounts.map(item => item[0]).join("、");
        const peak_hour_str = `${peak_hour.getMonth() + 1}月${peak_hour.getDate()}日 ${peak_hour.getHours()}时`;
        return [peak_hour_str, peak_count.toString(), peak_titles_str];
    }

    function find_extreme_sleep_times(dates, titles) {
        const adjustedTimes = dates.map(date => {
            return (date.getHours() + 24 - 4) % 24 * 60 * 60 + date.getMinutes() * 60 + date.getSeconds();
        });
        const latestIndex = adjustedTimes.indexOf(Math.max(...adjustedTimes));
        const earliestIndex = adjustedTimes.indexOf(Math.min(...adjustedTimes));
        const latestSleepDate = `${dates[latestIndex].getMonth() + 1}月${dates[latestIndex].getDate()}日`;
        const earliestWakeDate = `${dates[earliestIndex].getMonth() + 1}月${dates[earliestIndex].getDate()}日`;
        const latestSleepTime = dates[latestIndex].toLocaleTimeString();
        const earliestWakeTime = dates[earliestIndex].toLocaleTimeString();
        const latestSleepTitle = titles[latestIndex];
        const earliestWakeTitle = titles[earliestIndex];
        return [[latestSleepDate, latestSleepTime, latestSleepTitle], [earliestWakeDate, earliestWakeTime, earliestWakeTitle]];
    }

    function most_long_day_count(dates, duration) {
        const day_duration = {};
        for (let i = 0; i < dates.length; i++) {
            const date = dates[i].toDateString();
            day_duration[date] = (day_duration[date] || 0) + duration[i];
        }
        const max_day = Object.entries(day_duration).sort((a, b) => b[1] - a[1])[0];
        const count = (max_day[1] / 3600).toFixed(0);
        const date = new Date(max_day[0]);
        const date_str = `${date.getMonth() + 1}月${date.getDate()}日`;
        return [date_str, count];
    }

    const count = dates.length;
    const days = new Set(dates.map(date => date.toDateString())).size;
    const average = count / days;
    const duration = calculate_duration(dates);
    const max_day = most_long_day_count(dates, duration);
    const extremes = find_extreme_sleep_times(dates, titles);
    const peaks = find_peak_hourly_activity(dates, titles);
    const over_view_content = [
        { text: "在", highlight: false },
        { text: year.toString(), highlight: true },
        { text: "年, 你共计浏览过", highlight: false },
        { text: days.toString(), highlight: true },
        { text: "天, 点击了", highlight: false },
        { text: count.toString(), highlight: true },
        { text: "次链接, 平均每天点击", highlight: false },
        { text: average.toFixed(0), highlight: true },
        { text: "次.", highlight: false },
        { text: "\n\n", highlight: false },
        { text: max_day[0], highlight: false },
        { text: ", 你竟然访问了足足", highlight: false },
        { text: max_day[1], highlight: true },
        { text: "小时, 真是太厉害了!", highlight: false },
        { text: "从", highlight: false },
        { text: peaks[0], highlight: true },
        { text: "开始的一小时, 你疯狂敲击了 ", highlight: false },
        { text: peaks[1], highlight: true },
        { text: "次链接, 嘴里念叨着", highlight: false },
        { text: "\"", highlight: false },
        { text: peaks[2], highlight: false },
        { text: "\".", highlight: false },
        { text: "\n\n", highlight: false },
        { text: extremes[0][0], highlight: false },
        { text: ", 你在", highlight: false },
        { text: extremes[0][1], highlight: true },
        { text: "还未入眠, 陪伴你的是 \"", highlight: false },
        { text: extremes[0][2], highlight: false },
        { text: "\"\n", highlight: false },
        { text: "你最早在 ", highlight: false },
        { text: extremes[1][0], highlight: false },
        { text: extremes[1][1], highlight: true },
        { text: "醒来, 第一个访问的 \"", highlight: false },
        { text: extremes[1][2], highlight: false },
        { text: "\"", highlight: false },
    ];


    const container = document.getElementById("animated-text");
    const typingSound = document.getElementById("typing-sound"); // 获取音频元素
    typingSound.currentTime = 0; // 重置音频到开始位置
    let index = 0;
    const allCharacters = over_view_content.flatMap(item =>
        item.text.split("").map(char => ({ char, highlight: item.highlight }))
    );
    function typeOverViewText() {
        if (index == 0) {
            typingSound.play();
        }
        if (index < allCharacters.length) {
            const span = document.createElement("span");
            const text = allCharacters[index].char;
            // 检查是否包含换行符
            if (text === '\n') {
                const br = document.createElement("br");
                container.appendChild(br);  // 换行
            } else {
                span.textContent = text;
                if (allCharacters[index].highlight) {
                    span.className = "text-red-700 bg-yellow-200 font-bold px-1";
                }
                container.appendChild(span);
            }
            // 动态滚动逻辑
            if (container.scrollHeight > container.clientHeight) {
                const scrooStep = 20 * window.innerHeight / 100;
                container.scrollTop = container.scrollHeight - container.clientHeight + scrooStep;
            }
            index++;
            setTimeout(typeOverViewText, 100);
        } else {
            typingSound.pause();
        }
    }
    setTimeout(typeOverViewText, 500);
}

const rules = {
    "study": {
        "name": "科研",
        "links": [
            "overleaf",
            "latex",
            "dl.acm",
            "arxiv",
            "ieee",
            "springer",
            "nature",
            "science",
            "researchgate",
            "cambridge.org",
            "mail",
            "research"
        ],
        "titles": [
            "学术",
            "论文",
            "研究",
            "文献",
            "参考资料",
            "paper"
        ]
    },
    "code": {
        "name": "编程",
        "links": [
            "github",
            "stackoverflow",
            "csdn",
            "gitee",
            "gitlab",
            "hackerrank",
            "geeksforgeeks",
            "python.org",
            "npmjs",
            "rust-lang.org",
            "code"
        ],
        "titles": [
            "代码",
            "技术博客",
            "开发工具",
            "编程",
            "glados",
            "gitlab",
            "documentation",
            "compiler"
        ]
    },
    "fun": {
        "name": "娱乐",
        "links": [
            "bilibili",
            "douyu",
            "youtube",
            "netflix",
            "twitch",
            "disneyplus",
            "spotify",
            "qqmusic",
            "applemusic",
            "douyin",
            "huya",
            "tiktok",
            "v.qq.com",
            "iqiyi.com",
            "youku.com"
        ],
        "titles": [
            "cc98",
            "直播",
            "影院",
            "游戏",
            "书吧",
            "电视剧",
            "在线观看",
            "在线播放",
            "短视频",
            "电影",
            "音乐",
            "动画",
            "综艺",
            "搞笑",
            "直播间",
            "腾讯视频"
        ]
    },
    "news": {
        "name": "资讯",
        "links": [
            "bbc",
            "cnn",
            "reuters",
            "newyorktimes",
            "zhihu.com",
            "weibo.com",
            "news.qq.com",
            "163.com/news",
            "wiki"
        ],
        "titles": [
            "头条",
            "热点新闻",
            "实时资讯",
            "评论",
            "财经新闻",
            "社会热点",
            "微博",
            "浙江大学"
        ]
    },
    "shopping": {
        "name": "购物",
        "links": [
            "amazon",
            "taobao",
            "jd",
            "aliexpress",
            "tmall",
            "ebay",
            "pinduoduo",
            "walmart"
        ],
        "titles": [
            "购物车",
            "折扣",
            "优惠券",
            "促销",
            "网购",
            "清单",
            "评价"
        ]
    },
    "social": {
        "name": "社交",
        "links": [
            "facebook",
            "twitter",
            "wechat",
            "whatsapp",
            "discord",
            "slack",
            "telegram",
            "linkedin",
            "qq"
        ],
        "titles": [
            "聊天",
            "朋友圈",
            "动态",
            "消息",
            "社区",
            "话题"
        ]
    }
};