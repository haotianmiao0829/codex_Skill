# reconcile-book-files

这是一个用于整理、核对和交付书籍文件的 Codex Skill。

它主要用于处理 CSV 书单和本地 PDF / EPUB 文件之间的对应关系，帮助确认书名、作者、出版社、ISBN、文件名是否一致，并在需要时生成可验证的交付结果。

## 适合处理的问题

这个 skill 适合用于：

- 识别 CSV 中的书籍名称是否能和文件夹里的 PDF / EPUB 一一对应
- 检查文件夹里的书籍文件数量和 CSV 行数是否一致
- 处理同名书、重复书、PDF 和 EPUB 是否为同一本书
- 根据书名、作者、出版社、ISBN 判断书籍是否重复
- 安全地重命名书籍文件
- 保留和处理 macOS 的 `._` 辅助文件
- 在不乱改原始文件的前提下生成新的交付 CSV
- 做交付前后的校验报告

## 使用原则

这个 skill 的核心原则是安全：

- 不直接覆盖原始 CSV
- 不随便删除文件
- 不根据猜测修改书名、作者、出版社、ISBN
- 文件名和 CSV 必须真实匹配，不能只看计划路径
- 修改前先做只读检查
- 修改后必须复核结果

## 文件结构

```text
reconcile-book-files/
  SKILL.md
  README.md
  references/
    sop.md
  scripts/
    preflight.py
    verify_delivery.py
```

## 安装方式

把整个 `reconcile-book-files` 文件夹复制到 Codex 的 skills 目录：

```text
/Users/你的用户名/.codex/skills/reconcile-book-files/
```

注意：必须复制整个文件夹，不能只复制 `SKILL.md`。

## 常见使用方式

可以这样对 Codex 说：

```text
使用 reconcile-book-files，帮我识别这个 CSV 里的书名是否能和这个文件夹里的 PDF / EPUB 一一对应。
```

或者：

```text
使用 reconcile-book-files，帮我检查这个书单和文件夹是否可以交付，不允许修改原文件。
```

或者：

```text
使用 reconcile-book-files，帮我按照 CSV 里的书籍名称安全重命名文件，先告诉我 dry run 结果。
```

## 注意事项

如果任务涉及修改 CSV、重命名文件、移动文件，必须先确认：

- CSV 路径
- 文件夹路径
- 哪些列允许修改
- 输出的新 CSV 放在哪里
- 是否允许处理 `._` 辅助文件
- 是否只做识别，还是允许实际修改

默认情况下，应该先只识别，不直接修改。
