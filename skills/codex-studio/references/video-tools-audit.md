# 영상 제작 도구 30개: 활용 방식과 설치 구성

기준일: 2026-11-09. 아래 표에 링크한 30개 저장소를 기준으로 용도와 스킬 제공 형태를 확인했다. Manim은 커뮤니티판, Motion은 motiondivision/motion, Postprocessing은 pmndrs/postprocessing 기준이다.

## 조사 범위와 판단

각 저장소의 기본 브랜치 README·라이선스·파일 트리를 확인했다. 27개는 재귀 트리 전체에서 SKILL.md를 검색했고, Remotion 본체·Blender·tsParticles는 응답 크기 제한 때문에 루트와 에이전트 설정 하위 트리를 조사했다. 스킬 파일의 확인 여부는 도구 자체의 사용 가능 여부와 다르다. 이 문서는 모든 커뮤니티 스킬을 검색한 목록이 아니다. AGENTS.md/CLAUDE.md/llms.txt는 설치용 SKILL.md와 구분했다. 별도 공식 스킬 저장소는 본체 README에서 연결된 출처로 확인했다. 조사 범위·경로·고정 참조는 [기계 판독 카탈로그](../assets/toolkits.json)에 남겼다.

**기본 설치 구성:** Studio와 아래 공식 스킬 5팩, 기존 제작 환경에서 선별한 3팩을 합쳐 8팩을 함께 설치한다. [추가 3팩과 설치 조건](local-video-skills.md)을 참고한다. npm/Python 런타임, 모델 가중치, 앱 바이너리, MCP 설정은 설치하지 않는다. 전체 코드/가중치를 MIT 패키지로 재포장하지 않는다.

## 바로 설치할 수 있는 공식 스킬 팩

| 팩 | 원본 | 포함 | 제한 |
|---|---|---|---|
| remotion | [remotion-dev/skills](https://github.com/remotion-dev/skills) | remotion-best-practices + 내부 참조 147파일 | 엔진 라이선스 별도. 스킬 저장소에 별도 루트 LICENSE 파일은 확인하지 못함; 이 레포에 원문을 재배포하지 않고 설치 시 원본에서 받음 |
| hyperframes | [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes/tree/main/skills) | 코어 4스킬·226파일 | 원격 미디어/계정/사용 이벤트는 별도. 설치기가 실행하지 않음 |
| pixijs | [pixijs/pixijs](https://github.com/pixijs/pixijs/tree/dev/skills) | 서로 참조하는 26스킬·65파일 | 렌더 타임라인·MP4 출력은 별도 |
| motion | [motiondivision/ai-kit](https://github.com/motiondivision/ai-kit) | motion 1스킬·12파일 | best-practices는 로컬. MCP와 Motion+ 유료 기능 미설정 |
| gl-transitions | [공식 스킬](https://github.com/gl-transitions/gl-transitions/tree/master/skills/gl-transitions) | 1스킬·5파일 | 셰이더별 조건, 버전 호환, GPU/호스트 확인 |

설치기는 검토한 커밋과 Git blob 해시를 고정하고, 전체 다운로드 검증을 마친 뒤 프로젝트의 .agents/skills 및 .claude/skills에 넣는다. 같은 버전은 재설치하지 않으며 변경된 기존 스킬은 명시적 --upgrade와 복구 사본으로 보호한다. 상위 라이선스 파일이 있는 팩은 함께 내려받는다. 이 표는 스킬 파일 검토 결과이며, 30개 엔진의 실제 렌더 벤치마크를 수행했다는 뜻은 아니다.

## 30개 도구의 활용 방식

“개별 스킬 미포함”은 현재 Studio 기본 번들에 해당 도구 전용 스킬을 넣지 않았다는 뜻이다. 도구를 사용할 수 없다는 뜻이 아니며, 필요하면 공식 문서를 바탕으로 프로젝트에 도입할 수 있다. 별도 스킬 작성·런타임 설치·실제 연동은 이 표의 제공 범위와 구분한다.

| # | 프로젝트 | 확인한 스킬 | 역할 | 결정 | 라이선스 표기 |
|---|---|---|---|---|---|
| 1 | [three.js](https://github.com/mrdoob/three.js) | 개별 스킬 미포함; 공식 사용 문서 참고 | 3D 지도·카메라·조명·공간 자막 | 보조 도구 | MIT |
| 2 | [Remotion](https://github.com/remotion-dev/remotion) | 별도 공식 제작 스킬 | React 기반 컷·자막·합성·MP4 렌더 | 기본 스킬 팩 | Remotion License (source-available) |
| 3 | [Manim CE](https://github.com/ManimCommunity/manim) | 개별 스킬 미포함; 공식 사용 문서 참고 | 수학·다이어그램·설명형 모션 영상 | 보조 도구 | MIT |
| 4 | [Chatterbox](https://github.com/resemble-ai/chatterbox) | 개별 스킬 미포함; 공식 사용 문서 참고 | 로컬 내레이션·다국어 TTS | 기본 제외 | MIT (code) |
| 5 | [Motion](https://github.com/motiondivision/motion) | 별도 공식 AI Kit; 본체는 유지보수용 | 타이포·UI·스프링 애니메이션 | 기본 스킬 팩 | MIT (library / motion-ai package declaration) |
| 6 | [HyperFrames](https://github.com/heygen-com/hyperframes) | 공식 공개 9개; 코어 4개 선택 | HTML 장면을 결정론적 MP4로 렌더 | 기본 스킬 팩 | Apache-2.0 |
| 7 | [Blender mirror](https://github.com/blender/blender) | 개별 스킬 미포함; 공식 사용 문서 참고 | 3D 모델·시뮬레이션·합성·VSE | 별도 앱 | GPL-3.0 (whole application) |
| 8 | [Matter.js](https://github.com/liabru/matter-js) | 개별 스킬 미포함; 공식 사용 문서 참고 | 2D 충돌·낙하·운동 시뮬레이션 | 보조 도구 | MIT |
| 9 | [PixiJS](https://github.com/pixijs/pixijs) | 공식 제작 26개 | 2D 스프라이트·텍스트·입자·필터 | 기본 스킬 팩 | MIT |
| 10 | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | 개별 스킬 미포함; 공식 사용 문서 참고 | 음성 전사·단어 타임스탬프·자막 초안 | 우선 보조 도구 | MIT |
| 11 | [Anime.js](https://github.com/juliangarnier/anime) | 개별 스킬 미포함; 공식 사용 문서 참고 | SVG·DOM·타이포 타임라인 애니메이션 | 보조 도구 | MIT |
| 12 | [Babylon.js](https://github.com/BabylonJS/Babylon.js) | 저장소 개발·유지보수용 | 복잡한 3D 장면·카메라·물리 연출 | 보조 도구 | Apache-2.0 |
| 13 | [React Three Fiber](https://github.com/pmndrs/react-three-fiber) | 개별 스킬 미포함; 공식 사용 문서 참고 | React/Remotion에서 Three.js 장면 구성 | 보조 도구 | MIT |
| 14 | [Tone.js](https://github.com/Tonejs/Tone.js) | 개별 스킬 미포함; 공식 사용 문서 참고 | 음악·효과음 합성·비트 시퀀싱 | 보조 도구 | MIT |
| 15 | [Lottie Web](https://github.com/airbnb/lottie-web) | 개별 스킬 미포함; 공식 사용 문서 참고 | 벡터 애니메이션·아이콘·타이틀 재사용 | 보조 도구 | MIT |
| 16 | [OGL](https://github.com/oframe/ogl) | 개별 스킬 미포함; 공식 사용 문서 참고 | 가벼운 WebGL·커스텀 셰이더 | 보조 도구 | Unlicense (package.json) |
| 17 | [Motion Canvas](https://github.com/motion-canvas/motion-canvas) | 개별 스킬 미포함; 공식 사용 문서 참고 | 내레이션에 맞춘 설명형 2D 모션 | 보조 도구 | MIT |
| 18 | [tsParticles](https://github.com/tsparticles/tsparticles) | 저장소 개발·유지보수용 | 입자·배경·불꽃·컨페티 | 보조 도구 | MIT |
| 19 | [OBS Studio](https://github.com/obsproject/obs-studio) | 개별 스킬 미포함; 공식 사용 문서 참고 | 화면·창·장치 녹화 | 별도 앱 | GPL-2.0-or-later |
| 20 | [Rapier](https://github.com/dimforge/rapier) | 개별 스킬 미포함; 공식 사용 문서 참고 | 2D/3D 강체·충돌 시뮬레이션 | 보조 도구 | Apache-2.0 |
| 21 | [p5.js](https://github.com/processing/p5.js) | 개별 스킬 미포함; 공식 사용 문서 참고 | 생성형 그래픽·데이터 표현 | 보조 도구 | LGPL-2.1 |
| 22 | [Postprocessing](https://github.com/pmndrs/postprocessing) | 개별 스킬 미포함; 공식 사용 문서 참고 | Three.js 색보정·블룸·깊이 효과 | 보조 도구 | Zlib |
| 23 | [Shotcut](https://github.com/mltframework/shotcut) | 저장소 개발·유지보수용 | 수동 타임라인 편집·MLT 프로젝트 | 별도 앱 | GPL-3.0 |
| 24 | [Howler.js](https://github.com/goldfire/howler.js) | 개별 스킬 미포함; 공식 사용 문서 참고 | 웹 편집실 오디오 재생·프리뷰 | 보조 도구 | MIT |
| 25 | [Paper.js](https://github.com/paperjs/paper.js) | 개별 스킬 미포함; 공식 사용 문서 참고 | 벡터 경로·마스크·도형 모션 | 보조 도구 | MIT |
| 26 | [glTF Transform](https://github.com/donmccurdy/glTF-Transform) | 개별 스킬 미포함; 공식 사용 문서 참고 | 3D 자산 크기·텍스처·메시 최적화 | 보조 도구 | MIT |
| 27 | [WaveSurfer.js](https://github.com/katspaugh/wavesurfer.js) | 개별 스킬 미포함; 공식 사용 문서 참고 | 오디오 파형·구간 선택·자막 정렬 UI | 우선 보조 도구 | BSD-3-Clause |
| 28 | [React Spring](https://github.com/pmndrs/react-spring) | 저장소 개발·유지보수용 | React 스프링·자연스러운 전환 | 보조 도구 | MIT |
| 29 | [GL Transitions](https://github.com/gl-transitions/gl-transitions) | 공식 제작 스킬 | 셰이더 기반 장면 전환 | 기본 스킬 팩 | MIT catalog; per-shader licenses |
| 30 | [FFmpeg](https://github.com/FFmpeg/FFmpeg) | 개별 스킬 미포함; 공식 사용 문서 참고 | 컷·합성·자막·믹싱·인코딩·ffprobe | 기본 실행 기반 | LGPL-2.1+ / optional GPL and other build terms |

## 항목별 설치·연동 메모

### 1. three.js

프레임 시간을 직접 주입해 장면을 그려야 하며 자체 MP4 인코더는 없다.

- 런타임 식별: `three`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/mrdoob/three.js/blob/dev/README.md), [라이선스/패키지 선언](https://github.com/mrdoob/three.js/blob/dev/LICENSE), [검토 트리](https://github.com/mrdoob/three.js/tree/739478bc5ac18509be78095ed8f2fa4403b8207e).

### 2. Remotion

공식 remotion-dev/skills의 라우터와 참조 묶음. 엔진은 회사 규모 등에 따라 별도 라이선스가 필요하며 MIT로 재배포하지 않는다.

- 런타임 식별: `remotion @remotion/cli`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/remotion-dev/remotion/blob/main/README.md), [라이선스/패키지 선언](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md), [검토 트리](https://github.com/remotion-dev/remotion/tree/137fae7730aaaeddab76ca957dd7578a25b65421).

### 3. Manim CE

ManimCommunity/manim 기준. 3b1b/manim과 API·설치가 다르므로 혼용하지 않는다. Cairo/Pango와 선택적 LaTeX 설치 확인.

- 런타임 식별: `manim`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/ManimCommunity/manim/blob/main/README.md), [라이선스/패키지 선언](https://github.com/ManimCommunity/manim/blob/main/LICENSE), [검토 트리](https://github.com/ManimCommunity/manim/tree/e80274a2586c3c2f8d72600fe873e5f7971c0c9c).

### 4. Chatterbox

README에 2026-08 연구 종료·미유지보수 명시. 모델 파일·GPU·물표식·음성 사용 권한 별도 확인. 요청 시 격리 환경에서만 검토.

- 런타임 식별: `chatterbox-tts`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/resemble-ai/chatterbox/blob/master/README.md), [라이선스/패키지 선언](https://github.com/resemble-ai/chatterbox/blob/master/LICENSE), [검토 트리](https://github.com/resemble-ai/chatterbox/tree/ab55923c27757c90cfcc407baa57dc25a7d25217).

### 5. Motion

별도 공식 motiondivision/ai-kit의 motion 스킬. 기본 가이드는 오프라인 사용 가능; MCP·Motion+ 기능은 별도이며 번들 설치가 연결하거나 구매하지 않는다.

- 런타임 식별: `motion`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/motiondivision/motion/blob/main/README.md), [라이선스/패키지 선언](https://github.com/motiondivision/motion/blob/main/LICENSE.md), [검토 트리](https://github.com/motiondivision/motion/tree/78f3ff51b5508f7e8c1c283d8e80bcd26fec37d7).

### 6. HyperFrames

공식 코어 4개를 기본 팩에 포함. 현재 스킬의 사용 이벤트·계정·유료 미디어 경로를 분리하고, 로컬 렌더와 원격 서비스를 혼동하지 않는다.

- 런타임 식별: `hyperframes`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/heygen-com/hyperframes/blob/main/README.md), [라이선스/패키지 선언](https://github.com/heygen-com/hyperframes/blob/main/LICENSE), [검토 트리](https://github.com/heygen-com/hyperframes/tree/c1e96a45b24c66c96ed9151075f5262d4a3614dc).

### 7. Blender mirror

GitHub는 개발 소스 미러. 배포 앱의 Python/bpy와 headless 렌더를 사용하며 전체 소스 복제·컴파일을 기본 설치로 하지 않는다.

- 런타임 식별: `Blender official release`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/blender/blender/blob/main/README.md), [라이선스/패키지 선언](https://github.com/blender/blender/blob/main/COPYING), [검토 트리](https://github.com/blender/blender/tree/741e9ebfbd960a10dac0d4a51bf802a1e03ccf05).

### 8. Matter.js

고정 timestep·seed·초기화 후 순차 시뮬레이션이 필요하다. 실시간 Runner를 그대로 캡처하면 재현성이 약하다.

- 런타임 식별: `matter-js`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/liabru/matter-js/blob/master/README.md), [라이선스/패키지 선언](https://github.com/liabru/matter-js/blob/master/LICENSE), [검토 트리](https://github.com/liabru/matter-js/tree/b8ee71cd7f9b49f53639ddaedd6254f1929bcbe5).

### 9. PixiJS

공식 라우터가 다른 스킬 폴더를 참조하므로 공개 skills 디렉터리 전체 26개를 함께 설치. 렌더 엔진과 타임라인은 별개.

- 런타임 식별: `pixi.js`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/pixijs/pixijs/blob/dev/README.md), [라이선스/패키지 선언](https://github.com/pixijs/pixijs/blob/dev/LICENSE), [검토 트리](https://github.com/pixijs/pixijs/tree/2ab93d21c9b4f28e3e6f66a9e82ea1e81e771a49).

### 10. faster-whisper

독립 Python venv. CPU int8부터 점검; CUDA/cuDNN은 기존 환경과 맞춘다. 첫 사용 모델 다운로드, 한국어 고유명사·타임코드 검수 필요.

- 런타임 식별: `faster-whisper`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/SYSTRAN/faster-whisper/blob/master/README.md), [라이선스/패키지 선언](https://github.com/SYSTRAN/faster-whisper/blob/master/LICENSE), [검토 트리](https://github.com/SYSTRAN/faster-whisper/tree/846467d436117e44d54ad74f555d85c75834edb0).

### 11. Anime.js

시간 기반 seek를 렌더러에 연결. v3/v4 API 차이와 브라우저 자동재생 루프를 점검.

- 런타임 식별: `animejs`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/juliangarnier/anime/blob/master/README.md), [라이선스/패키지 선언](https://github.com/juliangarnier/anime/blob/master/LICENSE.md), [검토 트리](https://github.com/juliangarnier/anime/tree/01b81be1df6843ccfe0a71c0699a746bf740dd77).

### 12. Babylon.js

발견된 스킬은 코드리뷰·PR·도구 포팅용. 영상 제작용 스킬로 묶지 않는다. Three.js와 동시에 기본 설치할 이유가 없다.

- 런타임 식별: `@babylonjs/core`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/BabylonJS/Babylon.js/blob/master/readme.md), [라이선스/패키지 선언](https://github.com/BabylonJS/Babylon.js/blob/master/license.md), [검토 트리](https://github.com/BabylonJS/Babylon.js/tree/f35c62d21403fd9641493f5d9b3a011ec959d46c).

### 13. React Three Fiber

React 메이저 버전 호환성을 확인하고 useFrame의 실제 경과시간 대신 영상 프레임 기준으로 계산.

- 런타임 식별: `three @react-three/fiber`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/pmndrs/react-three-fiber/blob/master/readme.md), [라이선스/패키지 선언](https://github.com/pmndrs/react-three-fiber/blob/master/LICENSE), [검토 트리](https://github.com/pmndrs/react-three-fiber/tree/d74622ea8ed717f7212d7e19d65ff3e325508389).

### 14. Tone.js

오프라인 오디오 렌더로 WAV를 생성해 영상에 합성. 브라우저 재생 권한·오디오 시작 지연을 최종 타임라인과 분리.

- 런타임 식별: `tone`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/Tonejs/Tone.js/blob/dev/README.md), [라이선스/패키지 선언](https://github.com/Tonejs/Tone.js/blob/dev/LICENSE.md), [검토 트리](https://github.com/Tonejs/Tone.js/tree/105c04cc00289caf49684ac5c7621bce8a042c4c).

### 15. Lottie Web

goToAndStop 등 프레임 제어와 폰트·외부 이미지 로딩을 점검. 애니메이션 파일 자체의 이용 조건도 확인.

- 런타임 식별: `lottie-web`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/airbnb/lottie-web/blob/master/README.md), [라이선스/패키지 선언](https://github.com/airbnb/lottie-web/blob/master/LICENSE.md), [검토 트리](https://github.com/airbnb/lottie-web/tree/bede03d25d232826e0c9dca1733d542d8a7754fb).

### 16. OGL

소규모 효과에 적합. 장면 편집기·타임라인·인코더는 별도다.

- 런타임 식별: `ogl`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/oframe/ogl/blob/master/README.md), [라이선스/패키지 선언](https://github.com/oframe/ogl/blob/master/package.json), [검토 트리](https://github.com/oframe/ogl/tree/385ce65c352c70734a36dc98c787fdd1d30ddb3b).

### 17. Motion Canvas

TypeScript generator 기반 타임라인. 완성 영상은 프로젝트 exporter로 만들고 Studio에 등록.

- 런타임 식별: `@motion-canvas/core @motion-canvas/2d`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/motion-canvas/motion-canvas/blob/main/README.md), [라이선스/패키지 선언](https://github.com/motion-canvas/motion-canvas/blob/main/LICENSE), [검토 트리](https://github.com/motion-canvas/motion-canvas/tree/7b91435c301d530351dcf5ebb91dd139c002e405).

### 18. tsParticles

발견된 공식 저장소 스킬은 Nx 유지보수용. 고정 난수·수동 시간 진행이 가능한 구성만 영상에 사용.

- 런타임 식별: `@tsparticles/engine`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/tsparticles/tsparticles/blob/main/README.md), [라이선스/패키지 선언](https://github.com/tsparticles/tsparticles/blob/main/LICENSE), [검토 트리](https://github.com/tsparticles/tsparticles/tree/b52e18b662d7401b3a7cc7bc835a445a13c2b146).

### 19. OBS Studio

실시간 캡처 도구이며 프레임 결정론적 렌더러가 아니다. 실제 소스·프로필·녹화 경로를 확인하고 필요한 경우 공식 websocket 기능 사용.

- 런타임 식별: `OBS official release`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/obsproject/obs-studio/blob/master/README.rst), [라이선스/패키지 선언](https://github.com/obsproject/obs-studio/blob/master/COPYING), [검토 트리](https://github.com/obsproject/obs-studio/tree/7a25c3fd8b5eb87c2d2e0606cae36e32014bc6fa).

### 20. Rapier

기본 저장소는 Rust 코어. 웹용은 공식 JS/WASM 패키지와 비동기 초기화 필요; 고정 timestep과 재설정 검증.

- 런타임 식별: `@dimforge/rapier3d-compat`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/dimforge/rapier/blob/master/README.md), [라이선스/패키지 선언](https://github.com/dimforge/rapier/blob/master/LICENSE), [검토 트리](https://github.com/dimforge/rapier/tree/475caa3ff4646fd9a796b67d14116256f4962bc7).

### 21. p5.js

AGENTS.md는 저장소 기여 지침이지 설치할 영상 스킬은 아니다. seed/noLoop/redraw와 프레임 계산으로 재현성 확보.

- 런타임 식별: `p5`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/processing/p5.js/blob/main/README.md), [라이선스/패키지 선언](https://github.com/processing/p5.js/blob/main/license.txt), [검토 트리](https://github.com/processing/p5.js/tree/32ebd9f21de73d2c78c9e962d4c549c13f73537f).

### 22. Postprocessing

Three.js 호환 버전과 색공간·톤매핑을 맞춘다. 이름이 일반적이므로 pmndrs/postprocessing으로 식별.

- 런타임 식별: `postprocessing`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/pmndrs/postprocessing/blob/main/README.md), [라이선스/패키지 선언](https://github.com/pmndrs/postprocessing/blob/main/LICENSE.md), [검토 트리](https://github.com/pmndrs/postprocessing/tree/a1f103559d15cf56cbcbb15d4373711b09418f3f).

### 23. Shotcut

new-filter-ui 스킬은 Shotcut 자체 QML 필터 개발용. 영상 편집 스킬로 자동 설치하지 않는다.

- 런타임 식별: `Shotcut official release`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/mltframework/shotcut/blob/master/README.md), [라이선스/패키지 선언](https://github.com/mltframework/shotcut/blob/master/COPYING), [검토 트리](https://github.com/mltframework/shotcut/tree/2f85cdff3c67fe364e806dca7f97d1a7a32018d0).

### 24. Howler.js

편집실 재생용이며 오프라인 믹싱 엔진은 아니다. 음원 분리가 없는 믹스에 개별 트랙 볼륨을 표시하지 않는다.

- 런타임 식별: `howler`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/goldfire/howler.js/blob/master/README.md), [라이선스/패키지 선언](https://github.com/goldfire/howler.js/blob/master/LICENSE.md), [검토 트리](https://github.com/goldfire/howler.js/tree/1d3053576a860e9854645493ad6c4a72c6cc6e45).

### 25. Paper.js

Canvas 경로를 프레임별 계산. 브라우저 렌더러/FFmpeg 출력 파이프라인과 결합해야 한다.

- 런타임 식별: `paper`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/paperjs/paper.js/blob/develop/README.md), [라이선스/패키지 선언](https://github.com/paperjs/paper.js/blob/develop/LICENSE.txt), [검토 트리](https://github.com/paperjs/paper.js/tree/0d1446a1bb040e3c87533b28bcc384d87663587b).

### 26. glTF Transform

원본 GLB 보존 후 별도 출력. 최적화 전후 재질·애니메이션·스킨을 대표 장면에서 비교.

- 런타임 식별: `@gltf-transform/cli`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/donmccurdy/glTF-Transform/blob/main/README.md), [라이선스/패키지 선언](https://github.com/donmccurdy/glTF-Transform/blob/main/LICENSE.md), [검토 트리](https://github.com/donmccurdy/glTF-Transform/tree/8e2a94a2616d293c4b503d0fb6a4b42e6ec7c62f).

### 27. WaveSurfer.js

AGENTS.md는 기여 지침. 대용량 오디오는 peaks 활용; 웹 UI 표시와 실제 샘플 정렬·렌더 결과를 구분.

- 런타임 식별: `wavesurfer.js`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/katspaugh/wavesurfer.js/blob/main/README.md), [라이선스/패키지 선언](https://github.com/katspaugh/wavesurfer.js/blob/main/LICENSE), [검토 트리](https://github.com/katspaugh/wavesurfer.js/tree/9fbcf154461031e070bcc11817e7047aea5c7f58).

### 28. React Spring

발견된 14개 speckit 스킬은 프로젝트 개발 관리용. 영상 프레임마다 스프링 상태를 재현할 방법이 있어야 한다.

- 런타임 식별: `@react-spring/web`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/pmndrs/react-spring/blob/next/README.md), [라이선스/패키지 선언](https://github.com/pmndrs/react-spring/blob/next/LICENSE), [검토 트리](https://github.com/pmndrs/react-spring/tree/83e476061290532ab517c4d4dfd60de21589e78e).

### 29. GL Transitions

공식 제작용 스킬. 일반 FFmpeg에 gltransition 필터는 없으며 커스텀 빌드나 브라우저 프레임 렌더가 필요. 각 셰이더 저자·라이선스 확인.

- 런타임 식별: `gl-transitions`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/gl-transitions/gl-transitions/blob/master/README.md), [라이선스/패키지 선언](https://github.com/gl-transitions/gl-transitions/blob/master/LICENSE), [검토 트리](https://github.com/gl-transitions/gl-transitions/tree/e84faf9cc1dd54616471298218e5d22469ab63bc).

### 30. FFmpeg

기존 Studio의 렌더 기반. 설치된 빌드·필터·인코더를 먼저 확인하고 외부 바이너리를 MIT 번들로 포함하지 않는다.

- 런타임 식별: `FFmpeg official build`. 이는 설치를 실행한 기록이 아니다. 기존 프로젝트의 버전/lockfile과 공식 설치 문서를 확인해 필요한 구성만 선택한다.
- 근거: [README](https://github.com/FFmpeg/FFmpeg/blob/master/README.md), [라이선스/패키지 선언](https://github.com/FFmpeg/FFmpeg/blob/master/LICENSE.md), [검토 트리](https://github.com/FFmpeg/FFmpeg/tree/16a345b022e69c2fc1ba606e1d7833829e29202d).

## 번들 적용 순서

1. 기존 렌더 기반인 FFmpeg/ffprobe를 재사용한다. 전사 필요 시 faster-whisper, 파형 검토 필요 시 WaveSurfer를 추가한다.
2. React 장면은 Remotion, HTML 장면은 HyperFrames 중 작업에 맞는 것을 선택한다. 출력은 기존 Studio의 새 rev에 등록한다.
3. 2D 장면은 PixiJS, 3D는 Three.js/React Three Fiber 또는 Blender, 수학 설명은 Manim을 선택한다. 전체 엔진을 한꺼번에 설치하지 않는다.
4. Motion/Anime.js/Tone.js/Lottie/GL Transitions는 장면과 음향 보조에 사용한다. 프레임 재현성·오디오 정렬을 검증한다.
5. Sites는 모바일 검토·기기 간 수정 저장을 담당한다. 렌더 작업은 기존 실행 환경에서 한다. [모바일 워크플로](mobile-sites.md), [도구 선택·설치](video-toolkit.md)를 따른다.

라이선스 표기는 소스 파일을 확인한 식별 결과이다. 바이너리 배포·상용 사용·모델 가중치·사용자 자산의 조건은 해당 버전의 원문을 따른다. 특히 Remotion은 일괄적으로 MIT/OSI 오픈소스라고 표기하지 않고, FFmpeg는 빌드 옵션에 따른 조건을 구분한다.
