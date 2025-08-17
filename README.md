# FastmcpDocs

**I18N**  
The internationalized documentation of fastmcp.

🚀 The fast, Pythonic way to build MCP servers and clients.

[fastmcp source code](https://github.com/jlowin/fastmcp)

## Folder description

`i18n`: Internationalized document.  
`origin`:  Original comparison document.(The fastmcp does not have an i18n structure. This folder is used to facilitate the comparison with the original content.)

## Contributions

1. Usually, you need to perform a diff operation with the original document, Make sure the document is up-to-date.
2. Then, create the corresponding language configuration file in the `i18n/json_config` directory, and translate the parts that need to be translated in the language configuration file.
3. Create a folder named with the corresponding LANGUAGE CODE in the `i18n` directory, and name the file as the corresponding CODE. The CODE can be referred to in the
   table [LANGUAGE_CODE](./LanguageCode.md)
4. Create a copy of `origin` or `i18n/en`. If you use `origin` as the source for the copy, be sure to maintain the correctness of the file structure.
5. Use the command `cd i18n` to enter the directory `i18n`, and then use the script `python build_docs_json.py` to update the file `i18n/docs.json`.
6. Start the translation process and use `mint dev` to check the accuracy of the translation at any time.(Regarding the installation and usage of Mint, please refer to
   Document [MintlifyDocs](https://mintlify.com/docs/installation).)
7. Submit your internationalized content.

---

# FastmcpDocs

**I18N**  
fastmcp国际化文档。

🚀 构建 MCP 服务端和客户端更快捷，更Pythonic的方式.

## 文件夹叙述

`i18n`: 国际化后的文档.  
`origin`:  原始对照文档.(fastmcp没有i18n结构化，该文件夹用于方便与原始内容进行diff)

## 贡献

1. 通常你需要先与原始文档进行diff操作，确保文档是最新的。
2. 然后在`i18n/json_config`目录下创建对应的语言配置文件，并将其语言配置文件中需要翻译的部分进行翻译。
3. 在`i18n`目录创建对应语言的LANGUAGE CODE文件夹，文件名为对应的CODE，CODE可以参考该表格[LANGUAGE_CODE](./LanguageCode.md)
4. 创建`origin`或`i18n/en`的拷贝，如果你使用`origin`为源进行拷贝，注意文件结构的正确性。
5. 使用命令`cd i18n`进入目录`i18n`，然后使用脚本`python build_docs_json.py`更新`i18n/docs.json`文件。
6. 开始进行翻译，并随时使用`mint dev`检查翻译正确性。(关于mint的安装和使用参考文档[MintlifyDocs](https://mintlify.com/docs/installation)进行)。
7. 提交你的国际化内容。  