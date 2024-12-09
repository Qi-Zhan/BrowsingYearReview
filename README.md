# 你的浏览记录年度总结

> [!IMPORTANT]
> - 对于 Chrome 浏览器, 我们实现了对应的插件, 你可以直接在浏览器中查看你的(近90天)年度总结. [Chrome 插件](https://chromewebstore.google.com/detail/浏览记录年度总结/cajegnmfgehjccfjlekbmmgcibbkocnm?authuser=0&hl=zh-CN&pli=1)·
> - 所有程序均为本地运行, 不会泄露任何隐私信息.

我们默认用户的电脑上有 Python 3.9+ 环境, 并且掌握基础的命令行操作.

## Quick Start

在命令行中运行以下命令:

```bash
git clone https://github.com/Qi-Zhan/BrowsingYearReview.git
cd BrowsingYearReview
pip install -r requirements.txt
python main.py
```

如果浏览器没有弹出, 请手动打开 `dist/index.html` 文件查看你的年度总结.

> [!TIP]
> Chrome, Edge 等浏览器只保存最近 3 个月的历史记录, 如果你发现数据明显缺失, 请查看下面的手动导出历史记录的方法.

## 使用手动导出的历史记录

### Chrome

1. 打开 Chrome 浏览器, 进入 <https://takeout.google.com/settings/takeout> 页面.
2. 只需勾选 Chrome 中的书签、历史记录和其他设置, 然后点击 “下一步”.
3. 选择你喜欢的方式导出并下载数据.
4. 解压下载的文件, 找到 `History.json` 或者 `历史记录.json` 文件.

### Safari

1. 打开 “访达” 应用, 进入 `~/Library/Safari/` 目录. (右键点击 Finder 顶部菜单栏的 “前往” -> “前往文件夹”)
2. 复制 `History.db` 文件到本项目的目录下.


### 运行程序

和上面的 Quick Start 基本一样, 只需要指定历史记录文件的路径:

```bash
python main.py <path> # path 为 Chrome 或 Safari 的历史记录文件路径, 可以多个
```

## 技术栈

- 后端: Python. 使用 `pandas` 库来处理数据, `jieba` 和 `wordcloud` 库来生成词云.
- 前端: CSS, JavaScript. 使用 `charts.js` 来生成图表, `reveal.js` 来生成类幻灯片的展示效果.
