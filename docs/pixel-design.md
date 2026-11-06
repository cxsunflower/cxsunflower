# 像素街机主页设计记录

主页按一台复古街机的流程排版，每块用不同的界面风格，避免整页同一种面板：

| 顺序 | 面板 | 风格 | 主要动画 |
| --- | --- | --- | --- |
| 1 | `hero.svg` 标题屏 | 合成波夜空、向日葵太阳、透视网格地面 | 标题波浪与扫光、标语打字、花瓣旋转、太阳条纹下移、地面推进、流星、飞船、吉祥物摇头眨眼 |
| 2 | `profile.svg` 玩家卡 | 复古窗口 + RPG 状态栏 | 任务光标、HP/MP/XP 条、升级闪烁 |
| 3 | `inventory.svg` 背包 | 游戏物品格 | 选择框巡游、物品说明切换、咖啡冒汽 |
| 4 | `btn-repos.svg` / `btn-stars.svg` | 凸起像素按钮 | 按下、扫光、箭头推动 |
| 5 | `terminal.svg` / `aur.svg` | 终端（neofetch + yay） | 命令打字、逐行输出、色块、光标 |
| 6 | `arcade.svg` + 贪吃蛇 | 街机灯箱与屏幕机框 | 跑马灯、投币提示、金色贪吃蛇 |
| 7 | `log.svg` 任务日志 | HUD 时间线 | 逐行出现、扫描条 |
| 8 | `followers.svg` 船员 | 像素头像卡 | 卡片浮动、空位 JOIN 闪烁 |
| 9 | `waka.svg` 飞行日志 | 仪表盘 | 能量条、里程表滚动、占比扫光 |
| 10 | `footer.svg` 结尾 | 夜晚向日葵花田 | 花朵摇摆、萤火虫、火箭升空 |

## 约束

- 画布宽 846 像素，等于 GitHub 桌面端 README 的实际内容宽度（846.4px），按 1:1 绘制，像素不被缩放糊掉。所有条带在 300 像素宽的手机页面上仍高于 24 像素行高，图片之间不会出现缝隙。
- README 用一个连续的 HTML 容器排列图片，相邻标签之间不留空白，全部 `align="top"`；按钮各占半行，其余全宽。
- 调色板沿用深空紫蓝、青色和粉色，再加入头像向日葵的黄、橙与叶绿。
- 文字全部是点阵路径：5×9 字形（含小写与下伸部）、横向加粗体，以及标题专用的两格粗字形；不使用 `<text>`、外部字体或脚本。
- 动画只用 CSS keyframes（transform、opacity、clip-path 打字），keyframes 中不使用 `var()`。静止画面即完整信息，`prefers-reduced-motion` 时全部动画停止。
- 生成脚本只依赖标准库，随机数固定种子，相同输入得到相同输出。

## 数据与更新

| 面板 | 生成脚本 | 数据来源 | 工作流 |
| --- | --- | --- | --- |
| 标题屏、玩家卡、背包、按钮、灯箱、结尾 | `scripts/build_assets.py` | 静态 | 修改后手动构建 |
| 终端、AUR、任务日志 | `src/githubStats.py` | GitHub GraphQL、公开事件 REST、AUR RPC | `profileStats.yml` |
| 飞行日志 | `src/wakaPixel.py` | WakaTime OAuth | `wakaPixel.yml` |
| 船员 | `src/getTopFollowers.py` | GitHub GraphQL；头像以 24px 内嵌后像素化放大 | `topFollowers.yml` |
| 贪吃蛇 | Platane/snk + `scripts/style_snake.py` | 贡献日历 | `contribution-snake.yml`，发布到 `output` 分支 |

WakaTime 使用仓库 Actions Secret `WAKATIME_OAUTH_TOKEN`；GitHub 数据用 Actions 自带的 `GITHUB_TOKEN`。不要把凭据放进 README、SVG 或脚本。

构建与测试：

```powershell
python scripts/build_assets.py
python src/githubStats.py cxsunflower sunflowercx assets
python src/wakaPixel.py assets/waka.svg
python src/getTopFollowers.py cxsunflower $env:GITHUB_TOKEN assets/followers.svg
python scripts/style_snake.py dist/snake.svg
python -m unittest discover -s tests -v
```

通用图标采用 [Pixelarticons](https://github.com/halfmage/pixelarticons)，固定源码版本 `c9ecc2da61afde85dbe539025e3d931c6152ad75`，MIT 授权见 `licenses/pixelarticons.txt`，路径随仓库保存在 `scripts/pixelarticons.json`。语言与系统图标、向日葵吉祥物、行星和飞船为项目内绘制的像素图形。
