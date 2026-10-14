# MailProcessor

使用 Python 将一个或多个 EML 邮件文件合并为 MBOX 文件，支持递归扫描目录，并保留邮件原有的字符编码和 MIME 内容。

## 运行环境

- Python 3，建议使用 Python 3.10 或更高版本。
- 仅使用 Python 标准库，无需安装第三方依赖。
- 以下命令均在项目根目录运行；中文或带空格的路径请使用引号包裹。

## 快速开始

查看命令行帮助：

```bash
python3 eml_to_mbox.py --help
```

转换全部示例邮件，写入新的输出文件，避免覆盖仓库中的 `output.mbox`：

```bash
python3 eml_to_mbox.py examples -o demo.mbox
```

`examples/` 包含 7 封邮件，转换成功后会打印每封邮件的路径及消息总数。

## 命令行参数

```text
python3 eml_to_mbox.py <eml_file_or_dir> [...] [-o output.mbox] [-a]
```

| 参数 | 说明 |
| --- | --- |
| `inputs` | 一个或多个 EML 文件或目录，目录会被递归扫描 |
| `-o`, `--output` | 输出 MBOX 路径，默认是当前工作目录下的 `output.mbox` |
| `-a`, `--append` | 追加到输出文件；未指定时覆盖已有文件 |
| `-h`, `--help` | 显示帮助信息 |

转换指定邮件：

```bash
python3 eml_to_mbox.py examples/sample_utf8.eml examples/sample_cjk_utf8.eml -o selected.mbox
```

合并多个目录中的邮件：

```bash
python3 eml_to_mbox.py directory_test_data/single directory_test_data/nested -o combined.mbox
```

处理中文和带空格的路径：

```bash
python3 eml_to_mbox.py "directory_test_data/中文邮件/带 空格的目录" -o "unicode mail.mbox"
```

追加另一个目录中的邮件：

```bash
python3 eml_to_mbox.py directory_test_data/single -o appended.mbox
python3 eml_to_mbox.py directory_test_data/nested -o appended.mbox -a
```

输出目录必须预先存在：

```bash
mkdir -p exports
python3 eml_to_mbox.py examples -o exports/messages.mbox
```

## 字符编码与转换方式

- 以二进制读取邮件，不对正文进行字符集转码，也不重新序列化 MIME 内容。
- 保留原有 `Content-Type`、字符集声明、encoded-word 邮件头，以及 quoted-printable 和 base64 内容。
- UTF-8、ISO-8859-1、windows-1251 等编码可按原样保存；查看邮件时，客户端仍需按邮件自身的字符集声明解码。
- 将 CRLF 和 CR 换行统一为 LF，因此输出并非与输入逐字节完全相同。
- 根据邮件头生成以 `From ` 开头的 MBOX 分隔行，并补齐消息末尾换行和消息之间的空行。
- 当前实现将行首 `From ` 转为 `>From `，将行首 `>From ` 转为 `>>From `。

MBOX 文件不保证整体采用 UTF-8：只有新增分隔行使用 UTF-8 编码，邮件内容仍保留原始编码。程序不会修复错误的字符集标签或损坏的邮件内容。

## 示例文件

| 文件 | 编码或结构 | 内容 |
| --- | --- | --- |
| `examples/sample_utf8.eml` | UTF-8 | 英文纯文本 |
| `examples/sample_cjk_utf8.eml` | UTF-8 | 中文、日文、韩文和特殊符号 |
| `examples/sample_arabic_utf8.eml` | UTF-8 | 阿拉伯文 |
| `examples/sample_cyrillic_cp1251.eml` | windows-1251、quoted-printable | 俄文 |
| `examples/sample_iso88591.eml` | ISO-8859-1、quoted-printable | 法文重音字符 |
| `examples/sample_multipart.eml` | multipart/mixed | 纯文本、HTML 和 base64 附件 |
| `examples/sample_from_escape.eml` | UTF-8 | `From ` 行转义 |

`output.mbox` 是上述 7 封示例邮件的已生成转换结果。示例仅用于演示编码和格式处理，不代表真实邮件。

## 目录测试数据

`directory_test_data/` 保留目录测试输入和转换输出，不自动删除：

| 路径 | 用途 |
| --- | --- |
| `single/` | 单目录、大小写 EML 扩展名、非邮件文件过滤 |
| `nested/level1/level2/` | 多层目录递归扫描 |
| `other/` | 多目录合并、附件保留 |
| `中文邮件/带 空格的目录/` | 中文及空格路径 |
| `输出 目录/` | 10 个已生成的 MBOX 结果，包括合并、去重和追加场景 |

此前已运行 14 个目录相关场景，覆盖单目录、多层嵌套、多个目录、中文及空格路径、重叠输入、文件和目录混合、相对路径、追加写入、空目录、无效目录、附件保留及输出父目录缺失。

这些文件是测试样本和结果，不是可一键运行的自动化测试套件。Git 不记录空目录，克隆仓库后如需测试空目录，可手动创建：

```bash
mkdir -p directory_test_data/empty
python3 eml_to_mbox.py directory_test_data/empty -o empty_result.mbox
```

该命令预期返回退出码 `1`，且不生成 MBOX 文件。

## 退出码

| 退出码 | 含义 |
| --- | --- |
| `0` | 转换成功 |
| `1` | 未找到 EML 文件；未捕获的文件系统异常也可能导致此退出码 |
| `2` | 单封邮件转换或写入失败；命令行参数错误也使用此退出码 |

不存在的输入路径会打印警告；如果其他输入中仍有有效 EML 文件，转换会继续。

## 已知限制

- 默认覆盖输出文件；转换失败不会回滚已写入的内容，使用真实邮件前请备份。
- 输出父目录不存在时会抛出 `FileNotFoundError`，不会自动创建目录。
- 路径去重仅针对相同的路径字符串，不保证识别同一文件的相对路径、绝对路径或符号链接别名。追加模式也不检查已有邮件是否重复。
- 当前转义覆盖整个邮件字节内容，并且不会为行首 `>>From ` 或更多 `>` 的行再添加前缀，尚未完整实现 mboxrd 的递归转义规则。
- 日期缺失或无效时使用当前时间作为分隔行日期；该回退格式与正常邮件日期的格式不同。
- 没有并发写入锁，也没有严格验证每个输入文件是否为有效邮件。请勿同时向同一个 MBOX 写入。
- 未针对所有邮件客户端验证兼容性，导入真实邮箱前建议先用少量邮件验证。
