# 宇宙像素海报设计记录

本次筛选按 README SVG、图标一致性和可维护性评估，并非全网排名。沿用已有深空紫蓝、青色和粉色配色，不安装额外的图像生成服务。

| Skill | 适合的任务 | 本项目采用方式 |
| --- | --- | --- |
| [Pixel Art Fundamentals](https://github.com/ProkStudio/skills/blob/main/skills/game/2d/pixel-art-fundamentals/SKILL.md) | 图标轮廓、像素密度、原尺寸可读性检查 | 统一 24×24 图标，限制杂色，检查小屏尺寸 |
| [Pixel Art SVG Generator](https://github.com/rohitg00/auto-claude-code-research-in-sleep/blob/main/skills/pixel-art/SKILL.md) | README 插画、复用 SVG 图形、紧凑画布 | 点阵字形、复用图标、紧凑双栏；无需执行第三方脚本 |
| [Hermes Pixel Art](https://github.com/NousResearch/hermes-agent/blob/main/optional-skills/creative/pixel-art/SKILL.md) | 照片转像素画、复古调色板、循环动画 | 作为调色板与像素密度参考；当前 SVG 实现不依赖其图片转换脚本 |

通用图标采用 [Pixelarticons](https://github.com/halfmage/pixelarticons)，固定源码版本 `c9ecc2da61afde85dbe539025e3d931c6152ad75`，保留 MIT 授权于 `licenses/pixelarticons.txt`。图标路径随仓库保存，不依赖 CDN。蛇、宇航员和行星为项目内绘制的像素图形。

README 用一个连续的 HTML 容器排列图片；相邻图片标签不插入文本空白，所有图片设置 `align="top"`，消除段落外边距和图片基线空隙。AUR 与收藏项目各占半行，其他面板全宽。所有面板内部背景固定为 `#0b0a1f`，仅保留海报外边框。

蛇图原始 viewBox 有负坐标。`scripts/style_snake.py` 将动画整体平移到完整填色的 900 像素画布，同时保留动画，避免顶部透明条。关注者由 `src/getTopFollowers.py` 输出自包含的 SVG，头像内嵌，昵称用点阵路径绘制；点击整个面板进入关注者列表。

构建与更新：

```powershell
python scripts/build_assets.py
python src/wakaPixel.py assets/waka.svg
python src/getTopFollowers.py cxsunflower $env:GITHUB_TOKEN assets/followers.svg
python scripts/style_snake.py dist/snake.svg
python -m unittest discover -s tests -v
```

WakaTime 使用仓库 Actions Secret `WAKATIME_OAUTH_TOKEN`；不要把凭据放进 README、SVG 或生成脚本。修改布局时可沿用已有统计快照，实际数据由定时工作流刷新。
