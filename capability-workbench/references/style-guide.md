# style-guide · 工作台视觉规范（v2 大地色版）

> 从已验证的 v2 实现沉淀。改风格 = 改模板 `assets/workbench-template.html` 的 CSS 变量区；本规范保证「换数据不换气质」。

## 设计 tokens（CSS 变量）

```css
:root{
  --cream:#FAF7F1; --oat:#F2EDE4; --sand:#EAE2D5;         /* 背景三级 */
  --line:#E5DCCD; --line-soft:#EFE8DC;                     /* 描边两级 */
  --ink:#33291F; --ink-soft:#6E6355; --ink-mute:#9C9080;   /* 文字三级 */
  --terra:#B5622F; --terra-d:#8F4A20;                      /* 赤陶橙：人类三角/强调 */
  --olive:#77805C; --olive-d:#5C6446;                      /* 橄榄绿：AI三角/次强调 */
  --gold:#D4A24A;                                          /* 关键发现侧条 */
  --r:16px; --r-lg:22px;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,"Songti SC","Source Han Serif SC",STSong,serif;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",Roboto,sans-serif;
}
```

语义绑定（不可混用）：
- **赤陶橙 = 人类三角 / 人类侧证据 / has-ev 顶边**；**橄榄绿 = AI 三角 / AI 侧证据**。
- 背景：页面 cream、卡片白、面板 oat、次级面板 sand；正文 ink、辅助 ink-soft、提示 ink-mute。
- 字体：`h1/h2/角落名/lv 层号用 serif`；正文/表格用 sans。两个权重（400/600），不用更粗。

## 布局骨架

```text
wrap (max-width 1120, 居中)
├─ hero 横幅（深可可底 #33291F 反白）：eyebrow + serif h1 + cap + 徽章行
└─ bento 12 列网格（gap 16）
   ├─ tile.c12 双三角（SVG + 两侧灵魂拷问卡 + 证据面板）
   ├─ tile.c12 周期律（表格 + 场景栏 + 证据面板）
   ├─ tile.c7 迭代链 / tile.c5 Feature Library
   ├─ tile.c12 七资产画布 / tile.c12 关键发现
   └─ footer（细顶边线 + 来源声明）
```

- 瓦片：白底 + `border:1px solid var(--line-soft)` + `border-radius:var(--r)` + `box-shadow:0 1px 16px rgba(70,58,46,.07)`。
- 瓦片头：`eyebrow`（10.5px 大写字距 .32em）→ serif `h2`（22px）→ `cap` 说明（13px）。
- **证据面板**（`.detail`）：oat 底圆角 12px，列表项用 7px 方点（左三角橙/右橄榄绿区分侧别）；**必须有默认内容**，不允许初始空白。

## 双三角 SVG 形态规则（架构忠实于原图）

1. 单个大三角**左右对分**：左半人类三角（赤陶浅填充 #EBB28B）、右半 AI 三角（橄榄浅填充 #A9B48B），外框虚线，中缝白线。
2. 顶部尖角两侧：创造力（左）/ 场景（右）；底边四角从左到右：审美 / 体系 / 基本功 / 数据。
3. 中央「人类三角 × AI三角」衬线标题 + 上下两条飞轮弧线箭头（top/bottom 文案来自数据）。
4. 角块四行制：**名称（serif 19px）→ 判级圆点（●○ 第二行居中）→ 徽章胶囊（白底描边「段位 · 点击看证据」）→ 原图条目（11px）**——各段留空 ≥26px，禁止重叠。
5. 角块可点击（`g.corner`），点击切换证据面板；默认面板选中一个证据最丰富的角。

## 周期律网格规则

- 行序 **L5 → L1**（自上而下）；L1 跨维度两格 colspan=2。
- `td.has-ev`（有实证格）：`border-top:3px solid var(--terra)` + 底色 #FBF4EC——**橙色顶边是「证据归位」的唯一标记**。
- 层号列深色反白（serif 层号 + 中文层名/主线）；点击格切换证据面板；默认面板 = 使用说明（不允许空白）。
- 场景栏（借假修真）独立沙色卡：chip 标签间距 ≥5px，不过密。

## 其余组件

- 迭代链卡：交替赤陶/橄榄顶边；span 行带 commit 数。
- Library：六阶段计量条（hit 阶段实心赤陶圆点）+ 胶囊清单。
- 资产卡：六要素判级胶囊，`完备/确认` 用赤陶实底反白，其余白底描边。
- 关键发现：金色左侧条卡。

## 响应式

- ≤820px：bento 全宽单列、tri-zone 纵向堆叠、周期律容器 `overflow-x:auto`（表格可横向滚动，不隐藏）。
- 零外部依赖：无 CDN/字体外链/图片，图标全内联 SVG 或 CSS 形状；emoji 不作图标。
