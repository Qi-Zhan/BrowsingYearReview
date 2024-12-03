# 你的浏览记录年度总结

> 所有程序均为本地运行, 不会泄露任何隐私信息.

本项目用于生成你的浏览记录年度总结, 目前支持 Chrome, Safafi 浏览器.

我们默认用户的电脑上有 Python 环境, 并且掌握基础的命令行操作.

## 数据准备

### Chrome

1. 打开 Chrome 浏览器, 进入 <https://takeout.google.com/settings/takeout> 页面.
2. 只需勾选 Chrome 中的书签、历史记录和其他设置, 然后点击 “下一步”.
3. 选择你喜欢的方式导出并下载数据.
4. 解压下载的文件, 找到 `History.json` 或者 `历史记录.json` 文件, 复制到本项目的目录下, 这就是我们需要的数据.

### Safari

1. 打开 “访达” 应用, 进入 `~/Library/Safari/` 目录. (右键点击 Finder 顶部菜单栏的 “前往” -> “前往文件夹”)
2. 复制 `History.db` 文件到本项目的目录下, 这就是我们需要的数据.

## 运行程序

```bash
cd path/to/your/project
pip install -r requirements.txt
python main.py <path> # path 为 Chrome 或 Safari 的历史记录文件路径, 可以多个
```

在运行程序后, 用浏览器打开 `dist/index.html` 文件即可查看你的浏览记录年度总结.

> 生成词云时我们要求你给定中文字体, 请在 `analyze.py` 文件中修改 `FONT_PATH` 变量.

## 技术栈

- 后端: Python. 使用 `pandas` 库来处理数据, `jieba` 和 `wordcloud` 库来生成词云.
- 前端: CSS, JavaScript. 使用 `charts.js` 来生成图表, `reveal.js` 来生成类幻灯片的展示效果.
