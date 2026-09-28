# MMS 管理平台设计系统

## 设计方向
**医疗级操作工具** - 专业、清晰、高密度信息展示，适合长时间专注工作

## 色彩系统

### 主题色（医疗蓝）
- Primary: `#1e40af` (blue-800) - 专业可信赖
- Primary-light: `#3b82f6` (blue-500) - 交互高亮
- Primary-dark: `#1e3a8a` (blue-900) - 深色模式主色

### 语义色
```css
--color-success: #059669  /* green-600 - 成功/匹配 */
--color-warning: #d97706  /* amber-600 - 警告/待处理 */
--color-error: #dc2626    /* red-600 - 错误/未匹配 */
--color-info: #0284c7     /* sky-600 - 信息 */
```

### 中性色（zinc 调色板）
- 背景层级：`zinc-50` → `white` → `zinc-100`
- 文本层级：`zinc-900` → `zinc-700` → `zinc-500` → `zinc-400`
- 边框：`zinc-200` (light) / `zinc-700` (dark)

## 排版
- 标题：`font-semibold` + `text-lg/xl/2xl`
- 正文：`text-sm` (操作密集) / `text-base` (阅读)
- 辅助文本：`text-xs text-zinc-500`

## 组件规范

### 统计卡片
- 背景：`bg-white border border-zinc-200 rounded-lg shadow-sm`
- 数值颜色：统一用 `text-blue-600`，不按语义分色
- 图标：`text-zinc-400` 保持低调

### 表格
- 表头：`bg-zinc-50 text-xs font-semibold text-zinc-700 uppercase`
- 行悬停：`hover:bg-zinc-50`
- 边框：`border-zinc-200`

### 按钮
- Primary：Ant Design `type="primary"` 自动继承主题色
- Secondary：`border border-zinc-300 hover:border-zinc-400`
- 危险操作：`type="primary" danger`

### 标签 (Tag)
- 成功：`bg-green-50 text-green-700 border-green-200`
- 警告：`bg-amber-50 text-amber-700 border-amber-200`
- 错误：`bg-red-50 text-red-700 border-red-200`
- 中性：`bg-zinc-100 text-zinc-700 border-zinc-300`

## 暗色模式
使用 Tailwind 的 `dark:` 前缀，遵循以下映射：
- `bg-white` → `dark:bg-zinc-900`
- `bg-zinc-50` → `dark:bg-zinc-800/50`
- `text-zinc-900` → `dark:text-zinc-100`
- `border-zinc-200` → `dark:border-zinc-700`

## 禁止事项
- ❌ 内联 style 写颜色（除非动态计算）
- ❌ 统计卡用不同颜色区分类型
- ❌ 混用 hex 颜色和 Tailwind 类
- ❌ 纯装饰性渐变/阴影/模糊
