# Codex Studio

AI가 만든 **영상·이미지·HTML에 수정 요청을 남기는 로컬 편집실**입니다. Codex와 Claude를 번갈아 써도 같은 작업과 기록을 이어갑니다.

설치하면 해당 저장소의 AGENTS.md와 CLAUDE.md에 Codex Studio 스킬을 사용하도록 지침을 추가합니다. 이후 영상·이미지·HTML의 검토·편집을 요청하면 Codex와 Claude가 설치된 스킬을 읽고 편집실과 저장된 수정 요청을 활용하도록 안내합니다.

“편집실 띄워줘”라고 하면 에이전트가 Sites를 사용할 수 있는 환경에서 비공개 HTTPS 편집실까지 연결합니다. PC와 휴대폰에서 같은 주소로 열 수 있습니다. [편집실 열기와 Sites 연결](#편집실-열기와-sites-연결)

## 한 줄 설치

**편집할 영상·이미지·HTML이 있는 저장소의 최상위 폴더**에서 실행하세요. Python 3.10 이상이 필요합니다.

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

기본 설치는 해당 저장소에 다음 내용을 적용합니다.

| 대상 | 설치 시 변경 내용 |
| --- | --- |
| `.agents/skills/codex-studio/` | Codex용 스킬과 편집실 파일 설치 |
| `.claude/skills/codex-studio/` | Claude용 스킬과 편집실 파일 설치 |
| `AGENTS.md` | 관련 검토·편집 요청에서 Codex Studio의 SKILL.md를 읽고 사용하도록 Codex 지침 추가 |
| `CLAUDE.md` | 같은 스킬과 저장된 수정 요청·작업 기록을 사용하도록 Claude 지침 추가 |

기존 지침은 보존하고 Studio 안내 구역을 추가·갱신합니다. 파일이 없으면 생성합니다. Codex용 `AGENTS.override.md`가 있으면 그 파일에도 안내를 반영합니다. 사용자 홈의 전역 지침은 수정하지 않습니다.

업데이트도 같은 설치 명령을 사용합니다. 설치 후 해당 프로젝트에서 새 대화를 시작하세요.

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

설치와 로컬 작업 기록은 해당 프로젝트에 저장됩니다.

## 편집실 열기와 Sites 연결

“이 영상 편집하게 스튜디오 열어줘” 또는 “편집실 띄워줘”라고 요청하면 됩니다. Sites를 따로 언급하거나 배포 프롬프트를 다시 입력할 필요가 없습니다.

설치 시 AGENTS.md·CLAUDE.md에 연결 지침을 넣어, 에이전트가 다음 작업까지 이어서 수행하도록 합니다.

1. 현재 작업물과 저장된 수정 내용을 확인합니다.
2. Sites를 사용할 수 있으면 해당 작업물의 기존 편집실을 재사용하거나 비공개 편집실을 배포합니다.
3. 클라우드 저장과 모바일 화면을 확인하고, 배포된 HTTPS 주소를 엽니다. 휴대폰에서도 같은 주소에 동일한 ChatGPT 계정으로 로그인합니다.
4. 편집실에서 수정 내용을 저장한 뒤 대화에서 “저장한 수정 요청 반영해줘”라고 하면, 에이전트가 내용을 가져와 기존 제작 환경에서 반영하고 결과를 갱신합니다.

“로컬로만 열어줘”라고 하면 PC 안에서만 엽니다. Sites 플러그인이 없는 환경도 로컬 편집실을 열고 연결 제한을 알려줍니다. 로컬 주소는 다른 기기에서 사용할 수 없습니다.

이 연결은 설치된 지침을 읽은 Codex·Claude 에이전트가 수행합니다. 설치 프로그램이 Sites 계정을 연결하거나 Python 명령만으로 배포하는 것은 아닙니다. Sites 도구의 접근 권한·승인 절차는 해당 환경을 따릅니다. 수정 내용을 저장하는 것만으로 새 AI 작업이나 MP4 렌더링이 시작되지는 않습니다.

기존 설치자는 위 설치 명령을 다시 실행하고 해당 프로젝트에서 새 대화를 시작하면 변경된 연결 지침이 적용됩니다. [Sites 연결·클라우드 저장·로컬 반영 상세 지침](skills/codex-studio/references/mobile-sites.md)

[상세 사용법·추가 기능·개발 안내](docs/advanced.md) · [MIT License](LICENSE)
