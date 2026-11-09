# Codex Studio

AI가 만든 **영상·이미지·HTML에 수정 요청을 남기는 로컬 편집실**입니다. Codex와 Claude를 번갈아 써도 같은 작업과 기록을 이어갑니다.

설치하면 해당 저장소의 AGENTS.md와 CLAUDE.md에 Codex Studio 스킬을 사용하도록 지침을 추가합니다. 이후 영상·이미지·HTML의 검토·편집을 요청하면 Codex와 Claude가 설치된 스킬을 읽고 편집실과 저장된 수정 요청을 활용하도록 안내합니다.

PC에서는 로컬 편집실을 열고, **휴대폰에서는 [Sites로 배포한 HTTPS 편집실](#휴대폰에서-사용하기--sites)**을 이용할 수 있습니다.

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

## 휴대폰에서 사용하기 — Sites

`localhost`·`127.0.0.1` 주소는 편집실을 실행한 PC 전용이라 휴대폰에서 열리지 않습니다. **Sites 플러그인을 사용할 수 있는 Codex 환경**에서 아래처럼 요청하세요.

> 이 작업물을 휴대폰에서도 편집하게 Sites로 비공개 배포해줘. 자막과 수정 요청을 클라우드에 저장하고, 한글이 깨지지 않도록 확인해줘.

1. 에이전트가 선택한 작업물의 미리보기와 편집 화면, 클라우드 저장 기능을 구성하고 **HTTPS 주소**를 제공합니다.
2. 휴대폰에서 그 주소를 열고, 배포한 **동일한 ChatGPT 계정**으로 로그인합니다. 기본은 소유자만 접근하는 비공개 편집실입니다.
3. 자막이나 수정 요청을 작성하고 **저장**합니다. 다시 열었을 때 저장 내용이 유지되는지 확인하세요.
4. 대화에서 “Sites 편집실에 저장한 수정 요청 반영해줘”라고 요청합니다. 에이전트가 클라우드 수정 내용을 가져와 기존 제작 환경에서 반영·렌더링하고, 결과를 편집실에 갱신합니다.

모바일에서 저장한 내용은 **편집 요청**입니다. 저장만으로 AI 작업이나 새 MP4 렌더링이 자동 시작되지는 않습니다. Sites 연결·계정·호스팅은 Studio 설치와 별도이며, Sites가 없는 환경에서는 먼저 해당 플러그인을 연결해야 합니다.

한글 UTF-8 표시, 모바일 화면, 저장 후 새로고침, 기기 간 수정 충돌까지 확인하도록 스킬에 안내했습니다. [Sites 배포·클라우드 저장·로컬 반영 상세 지침](skills/codex-studio/references/mobile-sites.md)

## 기본 포함 영상 제작 스킬

한 줄 설치를 실행하면 Studio와 영상 제작 스킬 8개 팩이 함께 설치됩니다. 별도로 팩을 추가해달라고 요청할 필요 없이, 만들고 싶은 작업을 말하면 에이전트가 관련 스킬을 활용합니다.

| 스킬 팩 | 용도 |
| --- | --- |
| Remotion | React 기반 영상 구성·자막·합성 |
| HyperFrames | HTML 장면 기반 영상 제작 |
| PixiJS | 2D 그래픽·텍스트·효과 |
| Motion | 타이포·UI 애니메이션 |
| GL Transitions | 셰이더 기반 장면 전환 |
| Storyboarding | 저장소 소개·설명 모션그래픽 |
| Anatomy Reveal | 사물 구조·분해 애니메이션 |
| Colorfigures | 작동 원리를 보여주는 도해·HTML 삽화 |

예: “이 레포 소개 영상을 스토리보드로 만들어줘”, “이 물체의 분해 애니메이션 만들어줘”.

7개 팩은 설치 과정에서 검토한 공개 원본 버전을 내려받고, Colorfigures는 라이선스를 포함한 내장 설치본을 사용합니다. 기존 스킬 폴더는 보존하고 없는 스킬만 추가합니다. 다운로드에 실패하면 완료로 표시하지 않으며, 같은 명령을 다시 실행해 이어서 설치할 수 있습니다.

함께 설치되는 것은 스킬 지침·템플릿·보조 스크립트입니다. 실제 제작에 필요한 영상 엔진·앱·모델과 유료 서비스 인증은 작업과 기기에 맞춰 별도로 설정합니다. 설치 후 해당 프로젝트에서 새 대화를 시작하세요.

Python 설치기를 직접 사용할 때는 `--studio-only`로 편집실만 설치하거나, `--bundle NAME`을 반복해 설치할 팩을 제한할 수 있습니다.

[8개 팩의 설치·사용 방법](skills/codex-studio/references/video-toolkit.md) · [기존 제작 스킬과 실행 조건](skills/codex-studio/references/local-video-skills.md)

그 밖의 영상 도구는 [30개 프로젝트 활용 안내](skills/codex-studio/references/video-tools-audit.md)에서 용도와 준비 사항을 확인하세요. 이 목록은 30개 도구 모두가 설치되거나 연동됐다는 의미가 아닙니다.

[상세 사용법·추가 기능·개발 안내](docs/advanced.md) · [MIT License](LICENSE)
