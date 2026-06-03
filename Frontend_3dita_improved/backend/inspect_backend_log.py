from pathlib import Path

path = Path(r'c:/Users/rishi/AppData/Roaming/Code/User/workspaceStorage/30f7bc9b30d9113325bcfa23e135df50/GitHub.copilot-chat/chat-session-resources/a51bde33-81fe-4cc9-863e-ee954ff3e4fd/toolu_bdrk_01PEGHPaiaRebNUi8q9AhwLE__vscode-1777960513389/content.txt')
print('exists', path.exists())
if not path.exists():
    raise SystemExit(1)
with path.open('r', encoding='utf-8', errors='ignore') as f:
    count = 0
    for line in f:
        if '[backend]' in line:
            print(line.strip())
            count += 1
            if count >= 20:
                break
