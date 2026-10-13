# VRC Chatbox

**A tool for VRChat players who prefer not to speak, letting them type on their phones to chat with friends while in VR.**

[简体中文](README.md) · **English** · [日本語](README.ja.md) · [한국어](README.ko.md)

VRC Chatbox is a Windows text chat companion for VRChat using OSC. Run the app on your computer and open its web interface from a desktop browser or a phone on the same local network. Translate messages before sending, reuse phrases, and keep a shared message history.

> **No Python installation is required for the Windows release.** Download `VRCChatbox-1.4-Windows-x64.zip` from this repository's **Releases** section. The source archive is for development and building the app yourself.

## Features

| Feature | What it does |
| --- | --- |
| Access across devices | Use a computer or a phone on the same LAN |
| Manual browser launch | Shows local and LAN addresses without opening a browser automatically |
| Four interface languages | Simplified Chinese, English, Japanese and Korean, with saved preferences and host system language detection |
| Multiple translation providers | MyMemory, DeepL, Azure Translator and OpenAI-compatible APIs |
| Review before sending | Translation goes into the editor; you can revise it before sending |
| Bilingual messages | Send original + translation, translation only, or original only; choose the bilingual order |
| History and phrases | Shared storage on the host computer; edit, copy, resend and export history as TXT |
| Appearance settings | Light/dark themes, colors, avatars and background images |

This app sends text. **It cannot receive messages from other VRChat players.** A history entry records submission; it is not a delivery receipt.

## Quick start

### 1. Download and run

1. Download the Windows x64 release archive.
2. Extract the **entire archive** into a folder you can write to.
3. Run `VRCChatbox.exe` and leave its console window open.

Keep the `_internal` folder beside the EXE. Do not launch from inside an archive viewer or copy only the EXE.

### 2. Open the web interface

When the server is ready, the console displays addresses such as:

```text
This computer: http://127.0.0.1:5000/
LAN devices:   http://192.168.1.8:5000/
```

These are examples. Use the actual addresses printed by your app.

- **On the host computer:** open the “This computer” address in a browser.
- **On your phone or another device:** connect to the same LAN and open a LAN address. `127.0.0.1` on a phone refers to the phone itself.
- **Several addresses listed:** multiple adapters or a VPN may produce multiple candidates. Choose an address on the same subnet as your phone.

### 3. Enable OSC in VRChat

Enable OSC in VRChat's OSC settings. The default target is `127.0.0.1:9000`, intended for VRChat running on the same computer as this app.

Type a message and select **Send**. To translate, select **Translate**, review the result, then send it yourself.

## Everyday use

- `Enter` / `Return` sends a message; `Shift + Enter` adds a line break.
- Messages exceeding 144 characters or 9 lines are split at suitable punctuation when possible. **One segment is sent per action**; the remainder stays in the editor. If no suitable boundary exists, shorten the text or add punctuation.
- Sending an empty message requests that the chat bubble be cleared. **Clear input** only clears the editor.
- History supports editing in the composer, copying, resending and TXT export, and retains up to 150 entries.
- Save up to 100 quick phrases. Sending a phrase directly does not call a translation API.
- Close the console or press `Ctrl + C` to stop the app.

## Interface language

Open **Settings → Interface language** and select Simplified Chinese, English, Japanese or Korean.

**System default** reads the display language of the **Windows computer running the app**, not the phone. Unsupported languages fall back to English. Manual selection is saved on the host computer. All connected devices share this preference; reload other open pages to apply a change.

## Translation setup

Open **Settings → Translation provider**. Requests are sent by the host computer, which must be able to reach the selected provider.

| Provider | Required | Notes |
| --- | --- | --- |
| MyMemory | Nothing | Optional email; up to 500 UTF-8 bytes per request, not 500 characters in every language |
| DeepL | API Key | Uses the Free endpoint by default; Pro requires a different base URL |
| Azure Translator | API Key | Set Region when required by your resource; uses the global endpoint by default |
| OpenAI-compatible | API Key | Verify the base URL and model ID; the service must implement Chat Completions |

### MyMemory

Select MyMemory to try translation without a key. You may enter an email address. Availability and quotas are controlled by MyMemory.

### DeepL

Use a DeepL **API** key and the base URL appropriate to your account:

```text
Free: https://api-free.deepl.com
Pro:  https://api.deepl.com
```

Do not append `/v2/translate`; the app adds it.

### Azure Translator

Enter your key and the Region required by your resource, such as `eastasia`. Leave the base URL empty to use:

```text
https://api.cognitive.microsofttranslator.com
```

The app appends `/translate?api-version=3.0...`. A custom base URL must support that path. This version does not automatically adapt paths for Azure custom domains.

### OpenAI-compatible APIs

Enter your key, base URL and model ID. The app's default example is:

```text
API Base URL: https://api.openai.com/v1
Model:        gpt-4o-mini
```

This example does not guarantee model access for your account. For another compatible provider, use its actual HTTPS base URL and model ID. The app appends `/chat/completions`; do not include that suffix yourself.

### Saved settings and keys

- Language, provider, base URL, model, Region and optional email are saved on the host computer.
- **API keys stay in the current page's memory only.** Re-enter them after reloading, closing the page or changing providers.
- Changing providers clears the key, base URL, model and Region to avoid reusing the previous provider's settings.
- Text is submitted for translation only when you select **Translate**. Failure preserves the editor contents and never sends a message automatically.
- Providers may charge fees or enforce quotas. Your text is sent to the chosen provider; review its terms and privacy policy.

## Data, upgrades and migration

The Windows release creates files as needed in `config` beside the EXE:

| Path | Contents |
| --- | --- |
| `config/config.json` | Connection and appearance settings |
| `config/frontend_state.json` | History, phrases and interface preferences |
| `config/data/` | Uploaded avatars and backgrounds |

Before upgrading, close the app and back up the entire `config` folder. Extract the new release to a new location and copy the backup beside its EXE.

To migrate from the earlier source layout, copy the contents of `HTML osc chat/config` into the new `config` folder. Never publish your personal configuration directory.

## Networking and privacy

The default web binding is `0.0.0.0:5000`; the default OSC target is `127.0.0.1:9000`. Changing the web binding or port requires a restart. Use the new addresses displayed after restarting.

The app **has no sign-in and uses HTTP by default**. Use a trusted LAN only. Devices that can reach the interface can operate chat and shared settings; messages and keys submitted from a phone also travel over that LAN connection. Do not expose or forward this port to the public Internet. Set the web IP to `127.0.0.1` if you only need access from the host computer.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| Do I need Python? | Not for the Windows release; only for running or building from source |
| No browser opens | Expected behavior: manually open the address in the console |
| Phone cannot connect | Check the LAN address, shared network and private-network firewall permission; guest Wi-Fi may isolate devices |
| Port is occupied | Close another running copy; if needed, stop the app, edit `WEB_PORT` in `config/config.json`, then restart |
| VRChat shows no message | Check OSC, target IP/port and VRChat chatbox settings; history does not confirm receipt |
| Translation returns 401 / 403 | Check provider, key, account permissions and Azure Region where applicable |
| Quota or network error | Check the provider's quota and the host's network; you can still send the original text |
| Key disappears on reload | Intended behavior; keys are not written to disk |
| EXE does not run alone | Keep the full extracted folder and `_internal`; the current EXE is not code-signed |

## Run from source

Install Python 3.10 or later. The first dependency installation needs Internet access. From the repository root, run:

```bat
Start-Windows.cmd
```

Or create an environment manually:

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe "HTML osc chat\osc_viewer.py"
```

Source runs store data in `HTML osc chat/config`.

## Build a Windows release

On Windows x64 with 64-bit Python, run:

```bat
Build-Standalone-Windows.cmd
```

The output is `dist/VRCChatbox/`. Distribute the **entire folder**, not only the EXE. The build script does not copy your runtime data; a fresh launch uses default settings. When distributing binaries, provide the corresponding source and licenses as well.

## Validation and feedback

Version 1.4 has backend tests, storage and OSC request regression checks, packaged EXE startup checks and browser language-switching tests. Translation request/response handling was tested with mocked services. Real paid accounts, receipt inside VRChat and physical phone connections have not been fully tested.

When opening an issue, include the app version, Windows version, steps to reproduce and a sanitized error message. **Do not post API keys, private chat history or your complete personal configuration.**

## License and credits

This project includes code from [a2942/VRChat-OSC-WEB-Chat](https://github.com/a2942/VRChat-OSC-WEB-Chat) and is distributed under [GPL-3.0](LICENSE). See [NOTICE.md](NOTICE.md) for attribution. Third-party dependencies retain their own licenses. This project is not officially affiliated with VRChat or any translation provider.
