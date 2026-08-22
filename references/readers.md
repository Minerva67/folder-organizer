# 内容读取器 · 按类型策略与外部依赖

`signatures.py` 对每种文件用不同方式抽「它到底是什么」的一行签名。核心设计是
**优雅退化**：能深读就深读，工具缺失/格式未知就退回「名字+大小+日期」，永不硬失败。
这样它对任意文件夹都成立，而不是只对办公文档成立。

## 各家族读法

| 家族 | 扩展名 | 读什么 | 依赖 | 退化到 |
|---|---|---|---|---|
| 纯文本/代码 | .md .txt .csv .json .py .js .ts .sh .yml | markdown 标题 or 首几行 | 无（stdlib）| — |
| 网页 | .html .htm | `<title>` + 首个 h1 + 前几个 h2 | 无 | (无标题) |
| Office | .xlsx .docx .pptx | 文档标题(core.xml) + 工作表名(xlsx) / 幻灯片数(pptx) / 正文首段(docx) | 无（zip 解 xml）| (无法提取) |
| PDF | .pdf | 首页正文 | `pdftotext`(poppler) | /Title 元数据 → 提示装工具 |
| 图片 | .jpg .png .heic .tiff | 拍摄时间 + 机型 + 尺寸 + GPS | `exiftool` | 提示装 exiftool |
| 音视频 | .mp4 .mov .mp3 .wav .m4a .mkv | 时长 + 标题/艺人标签 | `ffprobe`(ffmpeg) | 提示装 ffmpeg |
| 压缩包 | .zip | 条目数 + 前几个文件名 | 无 | (压缩包) |
| 其他 | * | — | — | (二进制/未知 · 创建日期) |

## 可选外部工具（装了更强，不装也能跑）

- **poppler**（`pdftotext`）：读 PDF 正文。`brew install poppler`
- **exiftool**：读图片/RAW 的 EXIF（拍摄时间/机型/定位），照片库整理特别有用。`brew install exiftool`
- **ffmpeg**（`ffprobe`）：读音视频时长与标签。`brew install ffmpeg`

signatures.py 会自动检测这些工具是否存在；不存在就在签名里提示「装 X 可读 Y」，
让用户自己决定要不要装。**不要**因为缺工具就中断整理流程。

## 扩展新类型

给某类文件写更好的读法时，在 `signatures.py` 里加一个 `r_xxx(path)->str` 函数，
并注册到 `READERS` 字典。约定：只返回**一行**可读签名；出错吞掉异常、返回空串走退化。
读取要**快且只读头部**（大文件别整读），整理一个大目录会调用成百上千次。

## 按内容纠偏的典型场景（为什么这步不能省）

- `report.html` 实为营销登录页 → 归到「落地页」而非「报告」。
- `report.xlsx`、`report-副本.xlsx`、`report_v2.xlsx` 工作表名一模一样 → 同一分析的多份拷贝。
- 一个叫 `files.zip` 的包，解出来就是同目录已存在的两个文件 → 纯冗余。
- 名字里写 `v3` 的文件，创建时间反而比 `v2` 早 → 版本号不可信，以内容+创建时间为准。
