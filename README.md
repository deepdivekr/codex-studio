# Codex Studio

A local studio for reviewing videos, images and HTML, with shared revision requests and handoffs for Codex and Claude Code. Python 3.10+, no account. The editor needs no runtime packages. FFmpeg/ffprobe is required for MP4 export; Pillow is optional for image-region preparation and composition.

## 시작하기

이 저장소를 클론한 폴더에서 다음을 실행합니다. Windows PowerShell에서는 `python3` 대신 `python -X utf8`을 사용하세요.

```bash
python3 skills/codex-studio/scripts/artifact.py --project /path/to/project install
cd /path/to/project
python3 .agents/skills/codex-studio/scripts/artifact.py open
```

Codex에서는 `$codex-studio`, Claude Code에서는 `/codex-studio`로 호출합니다. 화면 이름은 **Codex Studio**입니다. 스킬은 각각 `.agents/skills/`와 `.claude/skills/`에 설치합니다. [Codex 스킬](https://developers.openai.com/codex/skills) · [Claude Code 스킬](https://code.claude.com/docs/en/skills)

설치하면 프로젝트의 `AGENTS.md`와 `CLAUDE.md`에 각 도구의 인계 확인 절차가 추가됩니다. 기존 프로젝트 지침은 유지됩니다. 이전 버전에서 업데이트하려면 설치 명령에 `--upgrade`를 붙이고 같은 프로젝트 폴더에서 새 세션을 여세요. [Codex 프로젝트 지침](https://developers.openai.com/codex/guides/agents-md) · [Claude Code 프로젝트 지침](https://code.claude.com/docs/en/memory)

이름을 바꿔도 기존 `.codex-artifacts/`의 편집안·요청·영상 rev·인계 기록은 유지합니다. `install --upgrade`는 이전 스킬의 진입 문서를 백업하고 `codex-studio`로 연결합니다. 기존 실행 명령도 호환용 진입점으로 계속 작동합니다.

**설치 형태는 스킬 + 로컬 편집 서버입니다. MCP 설정은 필요하지 않습니다.** 설치 후 같은 프로젝트에서 “이 영상 편집하게 아티펙트 생성해줘”, “자막 수정할 화면 열어줘”, “이 HTML 아티펙트로 보여줘”처럼 요청하세요. 에이전트가 파일을 등록하고 서버를 켜거나 재사용한 뒤 해당 아티펙트 주소를 엽니다. 요청과 스킬 설명을 맞춰 선택하는 방식이며, 대상이 여러 개면 파일을 확인합니다. [자연어로 스킬 선택](https://learn.chatgpt.com/docs/build-skills#how-chatgpt-and-codex-use-skills)

`open ID`는 준비된 `http://127.0.0.1:<port>/?artifact=ID`를 반환합니다. Codex 데스크톱에서는 에이전트가 인앱 Browser로 열고, 브라우저 열기 도구가 없는 환경에서는 클릭할 링크를 제공합니다. `assets/index.html`을 직접 열면 저장·불러오기 기능에 연결할 수 없습니다. 같은 PC에서 WSL을 쓰면 Windows 브라우저에서 WSL localhost 연결을 사용합니다. 원격 호스트는 포트 전달이 필요합니다. [Codex Browser 안내](https://learn.chatgpt.com/docs/browser)

서버는 브라우저를 닫아도 계속 실행되며 프로젝트당 하나를 재사용합니다. 주소와 PID는 `status`, 실행 로그는 `.codex-artifacts/runtime/server.log`에서 확인합니다. 직접 프로세스를 관리하려면 기존 `serve --port 0` 명령을 사용하고 Ctrl+C로 종료할 수 있습니다. 목록은 등록된 아티펙트 기록만 읽으며 저장소 전체를 스캔하지 않습니다. 연결 실패는 10초 안에 안내하고 다시 연결할 수 있습니다.

## 작업물 검토

아래 명령의 `artifact.py`는 설치한 스킬의 `scripts/artifact.py`를 뜻합니다. 경로는 프로젝트에 상대적이며 구분자는 `/`입니다. Git이 없는 폴더도 `--project PATH`로 지정할 수 있습니다.

```bash
python3 artifact.py add video episode-01 cut.mp4 --title "Episode 01" \
  --fps 30 --captions subtitles.srt --voice narration.wav --music bed.mp3 --effects effects.wav --music-level 55
python3 artifact.py add html design ui/index.html --title "Design" --asset ui/style.css
python3 artifact.py add image poster art/poster.png --title "Poster"
python3 artifact.py render episode-01 --out exports/episode-01-review.mp4
```

- **영상**은 프레임 이동, 수정 요청, 자막 수정과 나레이션·배경음악·효과음 볼륨 조절을 지원합니다. `--fps` 생략 시 ffprobe로 읽습니다. 정밀한 프레임 위치는 일정한 프레임레이트(CFR) 영상이 필요합니다.
- **자막**은 SRT, WebVTT 또는 `[{"start":0,"end":2,"text":"첫 줄"}]` 형태의 JSON을 읽습니다. 별도 `--voice`가 있으면 영상에 이미 섞인 소리 대신 그 트랙을 사용합니다. 기존 자막이 구워진 영상은 `--mask 19`처럼 아래쪽을 가릴 비율을 지정하세요.
- **내보내기**는 화면에서 SRT, CLI에서 SRT 또는 새 MP4를 지원합니다. MP4 자막은 FFmpeg/libass로 합성하며 `--font "Noto Sans CJK KR"`처럼 설치된 글꼴을 지정할 수 있습니다. 미리보기와 내보내기는 줄바꿈·글꼴이 다를 수 있습니다.
- **HTML**은 등록 문서와 `--asset`으로 허용한 파일만 샌드박스에서 엽니다. 외부 네트워크와 폼 제출을 막습니다. API 또는 모듈 로더에 의존하는 앱은 프로젝트 개발 서버를 사용하세요. **이미지**에는 지점·영역을 지정해 수정 요청을 남길 수 있습니다.
- 영상·자막 원본을 수정했다면 새 ID로 등록합니다. 이전 프레임 메모와 자막 편집이 다른 영상에 적용되지 않도록 원본 해시를 검사합니다.

## 이미지의 특정 부분 수정

이미지를 열고 **드래그로 영역 지정** 또는 **클릭으로 지점 표시** → 댓글 입력 → **수정 요청 추가** → **편집안 저장** 순서로 사용합니다. 수정 요청 탭에 선택 표시가 들어간 썸네일과 댓글이 함께 나오며, 누르면 그 위치로 돌아갑니다. 원본 좌표를 저장하므로 화면 크기를 바꿔도 같은 영역을 가리킵니다. 영역을 바꾸면 이전 완료 상태가 대기로 돌아갑니다.

클릭은 지점을 표시하는 기능입니다. 객체의 윤곽을 자동으로 인식하는 선택은 아직 포함하지 않습니다. 드래그 영역은 사각형이므로 그 안의 배경도 수정 범위에 들어갑니다.

에이전트는 `image prepare ID NOTE_ID --out edits/request-1`로 원본·선택 영역·마스크를 준비하고, 사용 중인 클라이언트의 이미지 도구로 후보를 만든 뒤 `image apply ID NOTE_ID --request-version HASH --edited edits/candidate.png --out edits/result.png`로 반영합니다. Pillow가 필요한 이 단계는 **선택한 사각형 밖의 원본 픽셀을 보존**합니다. 후보 이미지와 결과를 확인한 뒤 새 이미지 ID로 등록하고 요청에 연결합니다. 이미지 생성 모델은 이 패키지에 포함하지 않으며, 영상의 rev 보관 기능을 이미지·HTML까지 확장하는 것은 후속 작업입니다.

## 사용자의 수정 요청

편집하는 사람은 사용자입니다. 작업자나 에이전트를 선택하지 않습니다. **댓글 추가 → 편집안 저장 → 수정 요청 탭**에서 프레임 썸네일, 댓글, 대기·작업 중·완료·확인 필요 상태와 처리 결과를 모아 봅니다. 썸네일은 원본 영상의 해당 프레임이며 클릭하면 그 위치로 이동합니다. 작업물·상태 필터와 완료 후 **다시 확인 요청**을 지원합니다.

같은 대화에서 “저장한 수정 요청 반영해줘”라고 하면 현재 클라이언트가 처리합니다. 저장 자체가 쉬고 있는 AI를 자동 실행하지는 않습니다. 에이전트는 아래 명령으로 요청을 읽고, 실제 반영과 검증 후 완료 내용을 기록합니다. 화면은 5초마다 표시 중인 목록과 상태를 갱신하며, 저장하지 않은 편집 내용을 덮어쓰지 않습니다.

```bash
python3 artifact.py requests list --open
python3 artifact.py requests update episode-01 NOTE_ID --revision 0 --request-version HASH \
  --by codex --status done --summary "요청한 제목 크기 반영" \
  --checks "해당 프레임과 모바일 화면 확인" --file exports/revised.mp4 --result-artifact episode-01-v2
```

`revision`과 `request_version`은 조회 결과의 값을 사용하고, Claude에서 작업하면 `--by claude`로 기록합니다. 처리 기록은 `.codex-artifacts/requests/`에 편집안과 별도로 저장됩니다. 댓글이나 프레임이 바뀌면 이전 완료 상태는 대기로 돌아가고 이력은 유지됩니다.

## 영상 버전 보관

영상 편집안을 저장할 때마다 **rev1, rev2, rev3…**으로 당시의 댓글·자막·볼륨을 보관합니다. **버전** 탭에서 rev를 선택하면 저장한 요청과 처리 결과를 볼 수 있습니다. 수정 영상이 아직 없는 rev는 **반영 대기**로 표시됩니다. 에이전트가 검증한 MP4를 연결하면 **반영 완료**가 되고 영상 재생과 해당 rev의 MP4 다운로드가 가능합니다.

```bash
python3 artifact.py versions list episode-01
python3 artifact.py versions show episode-01 1
python3 artifact.py render episode-01 --rev 1 --out exports/rev1.mp4
# 실제 수정 결과를 검증하고 요청 완료 기록을 남긴 다음 로컬 버전을 확정합니다.
python3 artifact.py versions publish episode-01 1 --video exports/rev1.mp4 --by codex \
  --summary "제목 크기와 효과음 볼륨 수정" --checks "요청 프레임과 오디오 확인"
```

`versions publish`는 외부 게시가 아닌 **로컬 보관** 명령입니다. `.codex-artifacts/versions/`에 MP4 사본과 완료 시점의 메모를 저장하며, 완료된 rev는 덮어쓰지 않습니다. 사용자가 새 편집안을 저장하지 않고 추가 수정본을 만들 때는 에이전트가 `versions create ID`로 다음 rev를 만듭니다. 이전 rev를 다운로드해도 현재 편집안은 바뀌지 않습니다. 버전 영상은 로컬 디스크 공간을 사용하므로 이 폴더를 작업 자료와 함께 백업하세요.

## 세 가지 오디오 레이어

나레이션·배경음악·효과음 원본을 영상 시작 시각에 맞춰 연결합니다. 효과음 앞의 무음도 포함해야 합니다. 각 볼륨과 음소거는 재생 중 즉시 반영되고, 저장한 값은 MP4 내보내기에 적용됩니다. 기존 영상에 새 레이어를 연결하려면 다음을 사용합니다.

```bash
python3 artifact.py audio episode-01 --voice narration.wav --music music.wav --effects effects.wav
```

기존 연결과 편집안은 `.codex-artifacts/audio-history/`에 보관하며, 프레임 댓글은 유지됩니다. 분리되지 않은 영상 소리는 **원본 소리**, 연결하지 않은 레이어는 **미연결**로 표시합니다. 완성된 음원에서 AI로 소리를 분리하는 기능은 포함하지 않습니다. 원본이나 제작 코드에서 분리된 트랙을 준비하세요. 나레이션 길이를 바꾸면 효과음도 새 컷에 맞춰 만들고 `sync render ... --effects new-effects.wav`로 전달해야 합니다.

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

같은 작업 폴더를 다른 도구에서 열면 시작 지침에 따라 이전 작업 기록과 사용자의 미완료 요청을 확인합니다. 인계는 클라이언트를 바꿨을 때 이어 작업할 수 있도록 에이전트가 남기는 기록이며, 사용자 화면에는 인계함이 없습니다. 편집안 버전과 Git 브랜치·커밋도 함께 저장합니다.

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

수신을 확인한 인계도 답장을 남기기 전까지 CLI의 열린 인계 목록에 남습니다. 서비스는 IPv4 루프백에 열립니다. 공개 배포에는 도구 소스와 예제만 포함하며 사용자의 프로젝트, 영상, 댓글, 처리 기록은 각 작업 폴더에 유지됩니다. 화면의 프로젝트 이름도 현재 연 폴더에서 가져옵니다.

## Try the HTML example

From this repository:

```bash
python3 skills/codex-studio/scripts/artifact.py add html station-07 examples/sample.html --title "Station 07"
python3 skills/codex-studio/scripts/artifact.py serve --port 0
```

Use `artifact.py status` to find the running URL for this checkout. Stop the server with Ctrl+C. Run `python3 -m unittest discover -s tests -v` for the tests. Export tests require FFmpeg and ffprobe. MIT licensed.
