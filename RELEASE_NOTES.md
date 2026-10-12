# VRC Chatbox 1.4

简体中文：无需安装 Python 的 Windows x64 发布版。启动后显示本机与局域网地址，不自动打开网页。新增中英日韩界面和语言保存，支持 MyMemory、DeepL、Azure Translator、OpenAI 兼容翻译。解压完整目录后运行 VRCChatbox.exe。密钥仅保留在当前页面内存中。

English: Standalone Windows x64 release; no Python installation needed. Startup shows local and LAN addresses without opening a browser. Includes four interface languages with saved preferences, plus MyMemory, DeepL, Azure Translator and OpenAI-compatible translation. Extract the entire archive and run VRCChatbox.exe. Keys stay in the current page's memory only.

日本語：Python のインストール不要の Windows x64 版です。起動時に PC 用・LAN 用の URL を表示し、ブラウザーは自動起動しません。4 言語の UI と設定保存、MyMemory・DeepL・Azure Translator・OpenAI 互換翻訳に対応。全ファイルを展開して VRCChatbox.exe を起動してください。キーは現在のページのメモリー内でのみ保持します。

한국어: Python 설치가 필요 없는 Windows x64 배포판입니다. 시작 시 로컬 및 LAN 주소를 표시하며 브라우저를 자동으로 열지 않습니다. 4개 화면 언어와 설정 저장, MyMemory, DeepL, Azure Translator, OpenAI 호환 번역을 지원합니다. 전체 파일을 압축 해제하고 VRCChatbox.exe를 실행하세요. 키는 현재 페이지 메모리에만 유지됩니다.

## Downloads / 下载

- `VRCChatbox-1.4-Windows-x64.zip`: complete Windows application / Windows 完整程序。
- `VRCChatbox-1.4-Source.zip`: matching source and build scripts / 对应源码和构建脚本。
- `SHA256SUMS.txt`: archive checksums / 压缩包校验值。

## Validation / 验证范围

Packaged startup, browser language switching and backend regression checks passed. Translation adapters were tested with mocked responses. Real paid API accounts, delivery inside VRChat and physical phone connections have not been fully tested. The executable is not code-signed.

已验证打包启动、浏览器语言切换与后端回归。翻译接口使用模拟响应测试；真实付费账户、VRChat 内接收及实体手机连接尚未完整实测。EXE 未代码签名。

Use a trusted LAN only: no login authentication; HTTP by default. See the README for setup, privacy and migration details.
