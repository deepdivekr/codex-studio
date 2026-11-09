# Codex Studio

AI가 만든 **영상·이미지·HTML에 수정 요청을 남기는 로컬 편집실**입니다. Codex와 Claude를 번갈아 써도 같은 작업과 기록을 이어갑니다.

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

해당 저장소에 Codex·Claude 스킬을 설치하고, **저장소의 `AGENTS.md`·`CLAUDE.md`**에 작업 이어받기 안내를 추가합니다. 사용자 폴더의 `.codex/AGENTS.md`는 수정하지 않습니다. **업데이트도 같은 명령**입니다. 설치 후 해당 프로젝트에서 새 대화를 시작하세요.

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

설치와 작업 기록은 해당 프로젝트에 저장됩니다. 기본 편집 주소는 실행 중인 PC 전용입니다. **“휴대폰에서도 열리게 Sites로 배포해줘”**라고 요청하면, 에이전트가 사용 가능한 Sites 플러그인으로 비공개 HTTPS 편집실과 클라우드 저장을 구성합니다. 같은 ChatGPT 계정으로 로그인해 사용합니다. Studio 자체에 호스팅 서버나 Sites 계정이 포함되지는 않습니다. [모바일 연결 방식](skills/codex-studio/references/mobile-sites.md)

## 영상 제작 도구 확장

**“Remotion 스킬 팩 추가해줘”**, **“PixiJS와 전환 효과 스킬 설치해줘”**처럼 요청하세요. 검토한 공식 스킬을 해당 프로젝트의 Codex·Claude에 선택 설치합니다.

`remotion` · `hyperframes` · `pixijs` · `motion` · `gl-transitions` · `storyboarding` · `anatomy-reveal` · `colorfigures`

기존 제작 환경에서 쓰던 **스토리보드 영상·사물 분해 애니메이션·Colorfigures 도해**도 다른 사용자가 설치할 수 있습니다. Colorfigures는 라이선스를 포함한 설치본을 내장했고, 나머지 팩은 검토한 공개 원본을 내려받습니다. **“스토리보드와 분해 애니메이션 번들 설치해줘”**라고 요청하면 됩니다. [기존 스킬 선별 결과와 실행 조건](skills/codex-studio/references/local-video-skills.md)

검토한 커밋·파일 해시를 확인하고 설치하며, 기존 변경은 보호합니다. 영상 엔진·모델·앱·MCP는 따로 설정하므로 기본 설치가 무거워지지 않습니다. 설치 후 새 대화를 시작하세요.

[30개 프로젝트 개별 검토표](skills/codex-studio/references/video-tools-audit.md) · [선택 설치 명령과 도구 선택](skills/codex-studio/references/video-toolkit.md)

[상세 사용법·추가 기능·개발 안내](docs/advanced.md) · [MIT License](LICENSE)
