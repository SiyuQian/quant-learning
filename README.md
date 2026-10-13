# 知本 · 金融与量化学习记录

从零开始的中文学习手册，包含 **30 课**：原有 24 课的入门正文与深入案例，加上 6 个专题。每课有前置阅读、预计阅读/练习时间、机制和边界、完整演算或资料阅读案例、3 个有解析的练习与可重试自测；保留复利、购买力、回撤和费用计算实验。

在线阅读：**[知本 · 金融学习手册](https://siyuqian.github.io/quant-learning/)**。GitHub Pages 从 `main` 根目录发布。

## 学习路线

阅读顺序与课程 ID 分开，原 `#lesson-1` 至 `#lesson-24` 链接与保存的阅读标记继续对应原主题。

- 基础：投资 1 → 现金专题 25 → 复利 2 → 通胀 3 → 股票/债券/基金 4–6 → 订单/费用/杠杆 7–9。
- 收益与组合：收益 10 → Python/表格选读 26 → 回撤/统计 11–12 → 风险实验 27 → 分散/配置/再平衡 13–15。
- 企业与决策：报表/软件公司/估值 16–18 → 利率与汇率/行为/计划 19–21。企业分析可作为选修路线。
- 研究：数据 22 → 策略来源 28 → 回测 23 → 时间序列验证 29 → 分析工具 24 → 模拟交易与监控 30。

初学量化主线可先完成 1、25、2–4、6–8、10–12、26–27、22、28、23、29、24、30；不要求先掌握公司估值。课程内前置链接用于查读，阅读无需答题。**读完标记不代表掌握，也不代表具备真实交易能力。**

## 本地阅读与实验

浏览器打开 `index.html`，或在仓库根目录运行 `python3 -m http.server 8000` 后访问 <http://localhost:8000>。网页保持静态，无后端和运行时依赖；下载实验需要保留 `examples/` 目录。

进度使用原本的 `zhiben-progress-v1` 本地存储键，只存在当前浏览器。存储被禁用时页面提示进度仅在本次阅读中有效；不上传财务或个人资料。

[下载实验说明与参考结果](examples/README.md)；课程 22–24、26 也提供直接下载链接。所有 CSV 均为可公开使用的人工合成数据，不是市场业绩：

```sh
python3 examples/analysis.py --self-test
python3 examples/analysis.py analyze examples/net-values.csv
python3 examples/analysis.py backtest examples/prices.csv
python3 examples/analysis.py actions examples/corporate-actions.csv
```

Python 3.10+ 标准库即可。参考净值累计收益 10%、最大回撤 25%、截至终点未恢复；次开盘回测期末 195、收益 −2.5%、交易 2 笔，买卖费用各 1。基准按末收盘持仓估值 198，扣最终卖费清算则 197。指标假设、输入验证、错误练习与完整逐日账本见实验说明。

## 文件与检查

| 文件 | 内容 |
| --- | --- |
| `index.html` | 静态入口 |
| `lessons.js` | 30 课、90 道解析练习、资料与下载元数据 |
| `app.js` / `style.css` | 导航、阅读进度、原计算器、表格与原生答案揭示 |
| `examples/` | 合成 CSV、完整标准库程序、参考结果和限制 |
| `tests/` | 内容、数值、程序与外部浏览器验证 |

在仓库根目录运行：

```sh
node --check app.js
node --check lessons.js
node tests/check-content.mjs
node tests/check-worked-cases.mjs
python3 tests/check-examples.py
python3 examples/analysis.py --self-test
```

浏览器验证使用仓库之外安装的 Playwright 与 Chromium，未增加网站依赖。启动本地服务器后可运行：

```sh
PLAYWRIGHT_MODULE=/absolute/path/to/playwright/index.mjs \
BASE_URL=http://127.0.0.1:8000 \
ARTIFACT_DIR=/tmp/quant-learning-browser \
node tests/browser.mjs
```

测试覆盖全部 30 课的 1440/390px 布局、答案、下载、自测重试、原有保存 ID、阅读导航、四个计算器与受限存储；截图保存在指定目录。需要该外部安装的浏览器可执行文件。

## 内容来源与范围

原入门页面来自 2026-10-04 的本地 `finance-school/dist`，原 24 课介绍保留；深入课程核查于 2026-10-12。来源包括 Investor.gov/SEC、FINRA、NIST、BLS、Microsoft FY2025 年报、NYU/Stanford/作者研究资料、Python 官方文档，以及新西兰 Sorted、RBNZ、FMA、IRD。每课说明从哪里读、支持哪项概念、地区与样本限制；地区规则与外部页面会变化。

内容用于教育，不构成个人配置、具体买卖建议或收益承诺。合成样本用于验证账本和计算，不评估可交易优势；真实数据应核对口径、信息可用时间与再分发许可。请勿提交账户信息、密钥或个人财务记录。
