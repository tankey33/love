---
title: 一篇完整功能示例：代码、公式与表格
date: 2026-03-12
summary: 这篇文章用来展示碎碎念页面对代码高亮、复制、公式、表格、引用和图片等内容的支持。
---

# 一篇完整功能示例

![功能演示配图](images/fulls/02.jpg)

这篇文章专门用来测试博客文章最常见的需求：段落、列表、代码、公式、表格、引用、图片。

## 一段普通文字

有时候碎碎念并不需要很长，它更像是把当天的灵感认真保存下来。页面应该安静，但功能不能弱。

## 代码块（JavaScript）

```js
function sum(a, b) {
  return a + b;
}

const result = sum(3, 9);
console.log('result =', result);
```

## 代码块（Python）

```python
def fib(n: int) -> int:
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)

print(fib(8))
```

## 行内代码

比如 `git status`、`pnpm dev`、`python3 scripts/generate_posts.py` 这些都应该看起来清楚。

## 数学公式

行内公式：$e^{i\pi} + 1 = 0$

块级公式：

$$
\int_0^1 x^2 \, dx = \frac{1}{3}
$$

再来一个：

$$
\mathrm{Var}(X) = E[X^2] - (E[X])^2
$$

## 表格

| 项目 | 说明 | 状态 |
| --- | --- | --- |
| 代码高亮 | 使用 highlight.js | 已支持 |
| 公式渲染 | 使用 KaTeX | 已支持 |
| 复制按钮 | 每个代码块单独复制 | 已支持 |

## 引用

> 好的博客样式不是花哨，而是让内容本身更容易被认真读完。

![内容插图](images/fulls/07.jpg)

## 列表

- 支持 markdown 基础语法
- 支持代码高亮
- 支持公式
- 支持复制代码
- 支持较完整的文章阅读体验

## 一点结尾

如果以后要写更长的东西，这套排版也应该撑得住。它不只是"碎碎念"，也能承接偏正式的技术文章。
