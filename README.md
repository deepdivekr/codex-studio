# Codex Studio

AI가 만든 **영상·이미지·HTML에 수정 요청을 남기는 로컬 편집실**입니다. Codex와 Claude를 번갈아 써도 같은 작업과 기록을 이어갑니다.

## 한 줄 설치

**편집할 프로젝트 폴더**의 터미널에서 실행하세요. Python 3.10 이상이 필요합니다.

**macOS · Linux · WSL**

```bash
curl -fsSL https://raw.githubusercontent.com/deepdivekr/codex-studio/refs/heads/main/install.sh | bash
```

<details>
<summary>Windows PowerShell</summary>

```powershell
irm https://raw.githubusercontent.com/deepdivekr/codex-studio/refs/heads/main/install.ps1 | iex
```

</details>

Codex·Claude 양쪽에 설치됩니다. **업데이트도 같은 명령**입니다. 설치 후 해당 프로젝트에서 새 대화를 시작하세요.

## 이렇게 쓰세요

1. **“이 사진 편집하게 스튜디오 열어줘.”** — 영상과 HTML도 가능합니다.
2. 열린 화면에서 바꿀 부분을 지정하고 댓글을 남긴 뒤 **편집안 저장**을 누릅니다.
3. 대화에 “저장한 수정 요청 반영해줘”라고 말합니다.

수정 요청 탭에서 반영 결과를 확인하세요. 저장만으로 AI 작업이 시작되지는 않습니다.

| 작업물 | 할 수 있는 일 |
| --- | --- |
| 영상 | 프레임 댓글, 자막·오디오 볼륨 수정, rev별 영상 보관·다운로드 |
| 이미지 | 지점·사각형 영역 지정, 댓글, 수정 결과 확인 |
| HTML | 미리보기와 수정 요청 |

설치와 작업 기록은 해당 프로젝트에 저장됩니다. 화면은 모바일 크기에도 맞춰지며, **현재 편집 주소는 실행 중인 PC 전용**입니다.

[상세 사용법·추가 기능·개발 안내](docs/advanced.md) · [MIT License](LICENSE)
