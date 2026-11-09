# 기존 영상 제작 환경에서 선별한 번들

확인일: 2026-11-09. Windows와 WSL의 사용자 스킬, 영상 프로젝트, 공개 원본을 대조했다. 개인 프로젝트 전체나 로그인 상태를 복제하지 않고 재사용 가능한 제작 도구를 선택했다.

| 발견한 도구 | 제공 방식 | 용도와 실행 조건 |
|---|---|---|
| [Storyboarding](https://github.com/deepdivekr/Storyboarding-skill) | `storyboarding` 팩; MIT와 폰트 OFL 보존 | 저장소 설명 모션그래픽, HTML/MP4/GIF. Python, 브라우저, FFmpeg와 렌더 스크립트의 의존성을 별도 확인 |
| [Anatomy Reveal](https://github.com/annnguyentt/anatomy-reveal-skill) | `anatomy-reveal` 팩; MIT, THIRD_PARTY_NOTICES, kit LICENSE 포함 | 사물 구조·분해·조립 애니메이션. Node 20+, Chrome 계열 브라우저, FFmpeg, ImageMagick 7; package.json 기준 프로젝트 의존성 설치 |
| [Colorfigures](https://april-zhu.com/colorfigures) | `colorfigures` 팩; MIT 원문 포함, 7개 텍스트 파일을 Studio 자산으로 제공 | 삽화·작동 원리 HTML. 2026-10-19 설치본의 고정 시점 버전이며 최신 사이트의 회전 기능과 다름. Python 빌더와 브라우저 필요; MP4 변환은 별도 |
| war-map-shorts / footage-shorts | [범용 제작 절차](source-led-shorts.md)로 정리 | 출처 기반 대본·지도·실사 컷·자막·검수. 원본의 개인 경로, 채널 지침, 미공개 에피소드와 영상은 포함하지 않음 |
| fish-web-tts / sunra / dreamina-canvas-cli | 사용자별 연결 절차 | 로그인·유료 크레딧·브라우저/CLI 환경에 종속. 설치 당시 생성된 사용자별 스킬과 쿠키·키는 배포하지 않음 |
| FFmpeg / Blender / Whisper 캐시 | 환경에서 재사용, 설치 여부와 버전 확인 | 실행 바이너리·GPU 라이브러리·대용량 모델을 번들에 넣지 않음. 필요 기능에 맞춰 공식 설치 경로 사용 |
| 프로젝트 내부 Remotion / HyperFrames | 기존 패키지와 lockfile 유지 | 프로젝트 node_modules를 복사하지 않고 해당 공식 스킬 팩으로 보완 |
| 보관된 Manim 스킬 | 기본 번들 제외 | 아카이브 항목을 활성 도구로 간주하지 않음. Manim CE의 현재 공식 문서와 프로젝트 환경을 기준으로 선택 |

기본 설치 시 이 세 팩도 함께 설치된다. 아래 명령은 누락된 팩을 따로 설치할 때 사용한다. 프로젝트 루트에서 설치된 Studio를 사용한다. Windows PowerShell은 `python -X utf8`, WSL/macOS/Linux는 `python3`를 사용한다.

```sh
python3 .agents/skills/codex-studio/scripts/toolkit.py install storyboarding anatomy-reveal colorfigures --for both
python3 .agents/skills/codex-studio/scripts/toolkit.py plan anatomy-reveal
```

팩 설치는 파일을 배치하는 단계다. 렌더러 설치 완료를 의미하지 않는다. 처음 실제 제작할 때 필요한 실행 파일과 버전을 확인하고, 짧은 샘플을 출력해 해상도·길이·음성·한글 폰트까지 검증한다. Colorfigures는 HTML 출력 경로로 검증한다.

## 계정형 생성 도구 연결

1. 작업에 필요한 제공업체를 고르고 사용자의 기존 설치·인증 상태를 확인한다. 기본 음성·모델·요금제를 다른 사용자의 환경에서 가져오지 않는다.
2. 제공업체의 현재 공식 CLI/플러그인과 도움말을 확인한다. 인증은 사용자의 계정으로 수행하고 인증 정보는 스킬/저장소 밖에 둔다.
3. 원문·발음·길이·음성 선택과 요청 비용 범위를 확정한다. 기존 사용자 승인 범위에서만 유료 생성 호출을 실행한다.
4. 작업 ID와 산출물 위치를 기록한다. 타임아웃이면 작업 상태를 먼저 확인해 중복 과금을 피한다.
5. 내려받은 음성/영상을 로컬 파일로 검수하고 Studio에 등록한다. 공급자 스킬이 없는 사용자에게 준비 완료라고 표시하지 않는다.

## 출처와 업데이트

GitHub 팩의 정확한 커밋과 파일별 Git blob 해시는 `assets/toolkits.json`에 있다. Colorfigures의 `commit` 필드는 Git 커밋이 아닌 묶음 JSON의 SHA-1 식별자이며 `revision_kind`로 구분한다. 원본 크레딧과 라이선스는 번들 안에 그대로 있다. 새 버전은 원본과 의존성을 다시 확인한 뒤 명시적으로 갱신한다.
