# /codex-아티펙트 · Codex Artifacts

A local video, HTML and image review board with a shared handoff log for Codex and Claude Code. Python 3.10+, no runtime packages, no account. FFmpeg/ffprobe is optional for review and required for MP4 export.

## 시작하기

이 저장소를 클론한 폴더에서 다음을 실행합니다. Windows PowerShell에서는 `python3` 대신 `python -X utf8`을 사용하세요.

```bash
python3 skills/codex-artifacts/scripts/artifact.py --project /path/to/project install
cd /path/to/project
python3 .agents/skills/codex-artifacts/scripts/artifact.py open
```

Codex에서는 `$codex-artifacts`, Claude Code에서는 `/codex-artifacts`로 호출합니다. 화면 이름은 **/codex-아티펙트**입니다. 스킬은 각각 `.agents/skills/`와 `.claude/skills/`에 설치합니다. [Codex 스킬](https://developers.openai.com/codex/skills) · [Claude Code 스킬](https://code.claude.com/docs/en/skills)

설치하면 프로젝트의 `AGENTS.md`와 `CLAUDE.md`에 각 도구의 인계 확인 절차가 추가됩니다. 기존 프로젝트 지침은 유지됩니다. 이전 버전에서 업데이트하려면 설치 명령에 `--upgrade`를 붙이고 같은 프로젝트 폴더에서 새 세션을 여세요. [Codex 프로젝트 지침](https://developers.openai.com/codex/guides/agents-md) · [Claude Code 프로젝트 지침](https://code.claude.com/docs/en/memory)

**설치 형태는 스킬 + 로컬 편집 서버입니다. MCP 설정은 필요하지 않습니다.** 설치 후 같은 프로젝트에서 “이 영상 편집하게 아티펙트 생성해줘”, “자막 수정할 화면 열어줘”, “이 HTML 아티펙트로 보여줘”처럼 요청하세요. 에이전트가 파일을 등록하고 서버를 켜거나 재사용한 뒤 해당 아티펙트 주소를 엽니다. 요청과 스킬 설명을 맞춰 선택하는 방식이며, 대상이 여러 개면 파일을 확인합니다. [자연어로 스킬 선택](https://learn.chatgpt.com/docs/build-skills#how-chatgpt-and-codex-use-skills)

`open ID`는 준비된 `http://127.0.0.1:<port>/?artifact=ID`를 반환합니다. Codex 데스크톱에서는 에이전트가 인앱 Browser로 열고, 브라우저 열기 도구가 없는 환경에서는 클릭할 링크를 제공합니다. `assets/index.html`을 직접 열면 저장·불러오기 기능에 연결할 수 없습니다. 같은 PC에서 WSL을 쓰면 Windows 브라우저에서 WSL localhost 연결을 사용합니다. 원격 호스트는 포트 전달이 필요합니다. [Codex Browser 안내](https://learn.chatgpt.com/docs/browser)

서버는 브라우저를 닫아도 계속 실행되며 프로젝트당 하나를 재사용합니다. 주소와 PID는 `status`, 실행 로그는 `.codex-artifacts/runtime/server.log`에서 확인합니다. 직접 프로세스를 관리하려면 기존 `serve --port 0` 명령을 사용하고 Ctrl+C로 종료할 수 있습니다. 목록은 등록된 아티펙트 기록만 읽으며 저장소 전체를 스캔하지 않습니다. 연결 실패는 10초 안에 안내하고 다시 연결할 수 있습니다.

## 아티펙트 검토

아래 명령의 `artifact.py`는 설치한 스킬의 `scripts/artifact.py`를 뜻합니다. 경로는 프로젝트에 상대적이며 구분자는 `/`입니다. Git이 없는 폴더도 `--project PATH`로 지정할 수 있습니다.

```bash
python3 artifact.py add video episode-01 cut.mp4 --title "Episode 01" \
  --fps 30 --captions subtitles.srt --voice narration.wav --music bed.mp3 --music-level 55
python3 artifact.py add html design ui/index.html --title "Design" --asset ui/style.css
python3 artifact.py add image poster art/poster.png --title "Poster"
python3 artifact.py render episode-01 --out exports/episode-01-review.mp4
```

- **영상**은 프레임 이동, 메모, 자막 수정, 배경음 조절을 지원합니다. `--fps` 생략 시 ffprobe로 읽습니다. 정밀한 프레임 위치는 일정한 프레임레이트(CFR) 영상이 필요합니다.
- **자막**은 SRT, WebVTT 또는 `[{"start":0,"end":2,"text":"첫 줄"}]` 형태의 JSON을 읽습니다. 별도 `--voice`가 있으면 영상에 이미 섞인 소리 대신 그 트랙을 사용합니다. 기존 자막이 구워진 영상은 `--mask 19`처럼 아래쪽을 가릴 비율을 지정하세요.
- **내보내기**는 화면에서 SRT, CLI에서 SRT 또는 새 MP4를 지원합니다. MP4 자막은 FFmpeg/libass로 합성하며 `--font "Noto Sans CJK KR"`처럼 설치된 글꼴을 지정할 수 있습니다. 미리보기와 내보내기는 줄바꿈·글꼴이 다를 수 있습니다.
- **HTML**은 등록 문서와 `--asset`으로 허용한 파일만 샌드박스에서 엽니다. 외부 네트워크와 폼 제출을 막습니다. API 또는 모듈 로더에 의존하는 앱은 프로젝트 개발 서버를 사용하세요. **이미지**에는 메모를 남길 수 있습니다.
- 영상·자막 원본을 수정했다면 새 ID로 등록합니다. 이전 프레임 메모와 자막 편집이 다른 영상에 적용되지 않도록 원본 해시를 검사합니다.

## 대본 수정과 싱크

발음과 일치하는 오탈자나 표기 수정은 **표시 자막만**으로 저장해 기존 시각을 사용합니다. 실제로 읽을 문장이 달라지면 **나레이션 대본 → 편집안 저장 → 대본 변경사항 → 이 대본으로 승인**을 사용하세요. 승인 후 문장을 바꾸면 다시 검토합니다. 기존 음성을 그대로 사용한 일반 내보내기는 대본 수정 상태에서 차단됩니다.

승인한 문장은 `script show ID`로 가져옵니다. 프로젝트의 기존 TTS나 녹음 방식으로 새 음성을 만들고, 그 음성의 실제 구간을 전달하세요. 기존 나레이션과 새 나레이션에서 문장 순서와 개수는 같아야 합니다.

```bash
# 새 나레이션 전체 파일과 새 음성에 정렬한 자막
python3 artifact.py sync plan episode-01 --voice narration-v2.wav --timings narration-v2.srt
python3 artifact.py sync render episode-01 --voice narration-v2.wav --timings narration-v2.srt --out exports/episode-01-synced.mp4

# 문장별 PCM WAV가 있으면 파일 길이로 시각을 계산합니다
python3 artifact.py sync render episode-01 --clips voice-v2 --out exports/episode-01-synced.mp4
```

`--clips`는 승인 대본 순서대로 `0001.wav`, `0002.wav` 등을 읽고, 기존 문장 사이 쉼을 보존합니다. `sync plan`은 전후 길이와 컷 기준점을 보여줍니다. 기존 그림을 구간별로 늘리거나 줄이는 방식이라 장면 내부의 동작은 빨라지거나 느려질 수 있습니다. 소제목 정보가 담긴 JSON에서 새 음성이 소제목 구간과 겹치면 렌더를 멈춥니다. 새 컷 추가, 문장 재배치 및 음성 생성은 각 프로젝트의 제작 도구에서 처리합니다.

## Codex와 Claude 인계

같은 작업 폴더를 다른 도구에서 열면 시작 지침에 따라 그 도구 앞으로 온 인계를 확인합니다. 작업을 넘기는 에이전트는 완료 내용, 다음 작업, 검증 결과, 관련 파일을 기록합니다. 편집안 버전과 Git 브랜치·커밋도 함께 저장합니다. 편집실의 **인계함**에서는 같은 기록과 수신·답장 상태를 볼 수 있습니다.

```bash
python3 artifact.py handoff add --from codex --to claude \
  --title "Episode 01 subtitle pass" --summary "Reviewed the title-card transition" \
  --next "Check the note near 03:21 and review the music level" --artifact episode-01
python3 artifact.py handoff list --to claude --open
python3 artifact.py handoff show HANDOFF_ID
python3 artifact.py handoff ack HANDOFF_ID --by claude
python3 artifact.py handoff add --from claude --to codex --reply-to HANDOFF_ID \
  --title "Music reviewed" --summary "Saved the new music level" \
  --next "Render a separate MP4" --artifact episode-01
```

**같은 체크아웃**에서는 `.codex-artifacts/`의 아티펙트 정의, 편집안, 인계서, 수신 기록을 즉시 공유합니다. 같은 편집안에 동시에 쓰면 뒤늦은 저장을 거부합니다. **다른 체크아웃·워크트리·PC**에서는 필요한 기록과 원본·코드 변경을 Git 등으로 명시적으로 옮깁니다. 같은 영상의 편집안을 별개 워크트리에서 동시에 바꾸면 병합이 필요합니다.

수신을 확인한 인계도 답장을 남기기 전까지 열린 인계함에 남습니다. 작업자 선택은 기록용 라벨입니다. 서비스는 IPv4 루프백에 열리며 비공개 영상·경로·인계는 공개 저장소에 올리기 전에 검토하세요.

## Try the HTML example

From this repository:

```bash
python3 skills/codex-artifacts/scripts/artifact.py add html station-07 examples/sample.html --title "Station 07"
python3 skills/codex-artifacts/scripts/artifact.py serve --port 0
```

Use `artifact.py status` to find the running URL for this checkout. Stop the server with Ctrl+C. Run `python3 -m unittest discover -s tests -v` for the tests. Export tests require FFmpeg and ffprobe. MIT licensed.
