# 安装和第一次使用

## 推荐：交给 Codex 的安装器

在 Codex 中粘贴以下整段文字，不是在 PowerShell 中执行：

```text
$skill-installer install https://github.com/leishifu666/lsf-logo-geometry-system/tree/main/skills/lsf-logo-geometry-system
```

安装完成后，在下一轮消息显式输入 `$lsf-logo-geometry-system`，加上你的请求。如果当前会话没有识别，新开任务再试。

## 手动安装

1. 在 [Releases](https://github.com/leishifu666/lsf-logo-geometry-system/releases/latest) 下载 `lsf-logo-geometry-system-v1.5.0.zip`。
2. 解压出 `lsf-logo-geometry-system` 文件夹，确认里面直接有 `SKILL.md`、`references` 和 `scripts`。
3. 放入当前 Codex 安装器使用的 skills 目录。默认是 `$CODEX_HOME/skills`，未设置时为 `~/.codex/skills`。Windows 常见位置是 `%USERPROFILE%\.codex\skills`。
4. 不要多套一层同名文件夹。最终路径应类似 `~/.codex/skills/lsf-logo-geometry-system/SKILL.md`。
5. 如已有同名目录，先备份并比较版本，不直接覆盖本地定制。

上述路径来自当前 [OpenAI skill-installer](https://github.com/openai/skills/tree/main/skills/.system/skill-installer) 的默认规则；使用自定义环境时，以实际安装器返回的目录为准。

## 验证是否装好

先发送一条不会生成图片的请求：

```text
$lsf-logo-geometry-system
请确认你已加载这个Skill，并列出它支持的三种主要工作入口，暂不制作。
```

确认回复基于本 Skill 的三种入口后，再发送真实主题或上传图片。仅仅看到 AI 回答“可以设计Logo”，不算安装验证。

## 工具条件

探索板模式要能调用 Codex 内置生图。若环境没有该工具，应直接报告，不应假装已生图。直接设计与上传规整模式还需要能写入文件、执行构造或渲染命令的环境。

只有需要运行辅助脚本时，才在仓库根目录安装对应依赖：

```bash
python -m pip install -r skills/lsf-logo-geometry-system/requirements.txt
```

Python 测量依赖 NumPy、Pillow；Node 渲染依赖 `sharp`，也可由 Codex 采用已有 SVG 渲染器。安装 Skill 和安装脚本依赖是两件事，环境可能已有依赖。

## 常见情况

| 情况 | 处理 |
|---|---|
| 已存在同名 Skill | 使用现有版本或备份后更新，安装器不应悄悄覆盖 |
| `$` 后找不到名字 | 检查目录层级、下一轮消息或新任务中重试 |
| 能聊天但不能生图 | 检查当前环境是否提供内置生图；Skill 不能赋予工具权限 |
| 图像生成时间较长 | 等待真实工具完成；录像可剪掉等待，但应注明 |
| 黑底异常、少格、重复 | 要求针对实际问题修订，不把失败图当成功案例 |
| SVG 有了，PNG 没有 | 检查渲染器；不能把 SVG 文件改后缀充当 PNG |
| 生成了网格图，却没矢量文件 | 明确要求可编辑 SVG 和同源制图，不接受只有位图的制图外观 |
