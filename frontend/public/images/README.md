# 차량 구조 이미지 제작 기록

- 생성 방식: 내장 `image_gen` 도구. CLI/API 키를 사용하지 않았습니다.
- 저장 위치: `frontend/public/images/`.
- 사용자 레퍼런스는 반투명 구조 표현을 참고하는 용도였습니다. 결과물은 브랜드 없는 일반 가솔린 세단의 개념도이며 K5의 정확한 부품 배치도가 아닙니다.
- 기본 이미지의 불투명도는 화면에서 0.5로 낮추고, 선택한 부품만 SVG clipPath 레이어로 선명하게 합성합니다. 원본 PNG 알파는 유지했습니다.
- 원본 기본 1장과 기존 파츠 8장은 보존했습니다. 와이퍼 렌더링을 추가하고 9종 × 3색 = 27개의 새로운 PNG를 `states/`에 생성했습니다. 경고등/소모품 상태에 맞는 파일 자체를 바꾸며 SVG 색상 필터·hue-rotate를 사용하지 않습니다. SVG는 해당 영역을 합성하는 좌표 마스크로만 사용합니다.
- 빨강 `urgent` / 주황 `soon` / 청록 `comfortable`입니다. 상태 미확인은 중립 차체를 사용합니다. 전체 화면에서 같은 계통의 여러 항목이 충돌하면 가장 긴급한 색을 우선하고, 개별 상세에서는 선택 항목의 색을 표시합니다.
- 새 27장과 로고의 전체 프롬프트·원본·출력 경로는 [`../../artwork-prompts.json`](../../artwork-prompts.json)에 저장했습니다. 아래는 최초 원본 제작 프롬프트입니다.
- `vehicle-engine.png`: 엔진 / 호박색
- `vehicle-oil.png`: 윤활 계통을 설명하는 엔진 영역 / 산호색
- `vehicle-brakes.png`: 보이는 두 바퀴의 디스크·캘리퍼 / 산호색
- `vehicle-battery.png`: 12V 배터리 / 산호색 (충전 계통의 위치 예시)
- `vehicle-tires.png`: 두 타이어 / 호박색 (특정 바퀴 고장을 확정하지 않음)
- `vehicle-fuel.png`: 연료 탱크 / 호박색
- `vehicle-coolant.png`: 라디에이터·호스 / 청록색 (부품 선택 표시)
- `vehicle-cabin.png`: 안전장치 위치 / 산호색 (에어백 미전개)
- 에어컨 필터 선택의 강조는 사용자 요청에 따라 기존 맨 앞쪽 `vehicle-coolant.png` 레이어로 복원했습니다. 새로 추가했던 필터 SVG는 제거했습니다. 원본은 라디에이터·호스 그림이므로 실제 에어컨 필터 위치나 구조로 해석하면 안 되며, 시스템 수준의 탐색용 시각 표현입니다.
- 와이퍼는 앞유리 하단의 고무날과 암을 image_gen으로 렌더링한 PNG입니다. 기존 SVG 선 그림은 제거했고 `states/wiper-{urgent,soon,comfortable}.png`를 사용합니다. 실제 차량의 정확한 부품 배치도가 아닌 개념 표현입니다.
- `chageun-logo.png`: 사용자가 제공한 루트 `image.png`에서 흰 배경과 내부 흰 여백을 내장 image_gen으로 추출한 실제 알파 PNG입니다. 원본 루트 파일은 보존했습니다. 앱은 동일한 투명 형상에 테마별 단색을 적용하고, 서버 인증 페이지와 파비콘은 원래 남색 PNG를 사용합니다.
- 첫 진입에는 차체의 흰빛·앞쪽 부품·엔진·배터리·와이퍼·타이어를 하나의 스캔 레이어에 합성합니다. 공통 마스크가 0.95초 동안 앞에서 뒤로 움직이며 빛의 위치와 부품 강조가 정확히 함께 이동합니다. 타이어를 포함한 부품별 타이머·펄스는 제거했습니다. 빠른 선두와 짧은 잔광을 두며, 실제 센서 스캔을 뜻하지 않습니다. 직접 부품을 선택하면 스캔을 중지하고 기존 강조 상태를 표시합니다.

## 기본 이미지 · vehicle-cutaway.png

```text
Use case: stylized-concept. Asset type: transparent PNG vehicle illustration for a Korean novice-driver in-car diagnostic web UI. The supplied image is a reference only for translucent cutaway styling, not an edit target. Create a NEW premium photorealistic 3D visualization of a generic modern midsize Korean GASOLINE sedan, no brand logo, no text. A full car, elevated front-left three-quarter view, front bumper towards bottom-left and rear towards top-right, composed WIDE landscape with the car filling the frame horizontally (roughly 2:1). Entire silhouette including all wheels remains visible with modest empty margins. Dark graphite body made partly translucent smoked glass, understated ice-blue wireframe edges, visible gasoline engine under the front hood, radiator at the front, small 12V battery in the engine bay, seating in cabin, four tires and visible brake discs. NO electric skateboard battery pack, NO orange EV cables, no detached components, no labels, no indicators or callout dots (these will be real UI overlays). Subtle studio lighting designed to remain readable on a dark blue-gray #1b1e28 interface; brushed metal, elegant engineering visualization, restrained blue reflections, no neon environment. Background genuinely transparent, no floor or rectangular backdrop, a very soft contact shadow is okay. This is a conceptual component-location illustration, not an exact technical diagram.
```

## vehicle-engine.png

입력: `vehicle-cutaway.png` (편집 대상)

```text
Use case: precise-object-edit. Asset type: selected-component state for an interactive vehicle diagnostic web UI. EDIT TARGET is the supplied transparent cutaway car image. Keep EXACTLY the same camera, image canvas, framing, car silhouette, all component positions, proportions, transparency and lighting. Change ONLY the gasoline ENGINE ASSEMBLY (engine cover, engine block and intake hardware under the FRONT hood at left). Highlight only this engine, in warm AMBER #ffad48. Do not tint the 12V battery, radiator, wheels, cabin or entire hood. This is an X-ray diagnostic visualization; the named component itself becomes colored and emits a restrained soft glow at its own edges, not a blob over the car, not a callout dot. Keep all non-selected vehicle components in the original neutral blue-gray. Preserve exact full-image alignment because this state is crossfaded on top of the original. No text, no icons, no callouts, no arrows. Entire car must remain in the same location on the same wide 2:1 canvas, truly transparent background.
```

## vehicle-brakes.png

입력: `vehicle-cutaway.png` (편집 대상)

```text
Use case: precise-object-edit. Asset type: selected-component state for an interactive vehicle diagnostic web UI. EDIT TARGET is the supplied transparent cutaway car image. Keep EXACTLY the same camera, image canvas, framing, car silhouette, all component positions, proportions, transparency and lighting. Change ONLY the BRAKE DISCS AND CALIPERS inside the two visible wheels. Make the metal brake disc and caliper clearly visible through the rims as glowing CORAL RED #ff6565 solid components, with realistic details. Do not tint the tire rubber or rims. Slightly ghost only the wheel spokes enough to expose the brake disc. All other parts stay unchanged. This is an X-ray diagnostic visualization; the named component itself becomes colored and emits a restrained soft glow at its own edges, not a blob over the car, not a callout dot. Keep all non-selected vehicle components in the original neutral blue-gray. Preserve exact full-image alignment because this state is crossfaded on top of the original. No text, no icons, no callouts, no arrows. Entire car must remain in the same location on the same wide 2:1 canvas, truly transparent background.
```

## vehicle-battery.png

입력: `vehicle-cutaway.png` (편집 대상)

```text
Use case: precise-object-edit. Asset type: selected-component state for an interactive vehicle diagnostic web UI. EDIT TARGET is the supplied transparent cutaway car image. Keep EXACTLY the same camera, image canvas, framing, car silhouette, all component positions, proportions, transparency and lighting. Change ONLY the small rectangular 12 VOLT BATTERY in the FRONT engine bay, just above the near headlight, at approximately x=32%, y=57% of the image. Highlight only the battery casing and its two terminals in glowing CORAL RED #ff6565. Do not tint the engine, radiator, tires, fuel tank or rest of vehicle. This is an X-ray diagnostic visualization; the named component itself becomes colored and emits a restrained soft glow at its own edges, not a blob over the car, not a callout dot. Keep all non-selected vehicle components in the original neutral blue-gray. Preserve exact full-image alignment because this state is crossfaded on top of the original. No text, no icons, no callouts, no arrows. Entire car must remain in the same location on the same wide 2:1 canvas, truly transparent background.
```

## vehicle-tires.png

입력: `vehicle-cutaway.png` (편집 대상)

```text
Use case: precise-object-edit. EDIT TARGET: supplied transparent vehicle cutaway. Make one precise component-highlight variant for an interactive diagnostic UI. Keep EXACT same canvas, 2:1 aspect, camera, framing, silhouette, wheel positions, materials, all non-target pixels as faithfully as possible. Change ONLY the black rubber TIRES on both visible wheels. Give ONLY the rubber tire sidewalls and tread a detailed warm AMBER #ffad48 x-ray material, preserving all tire shape and grooves. The metal rims and brake discs stay original neutral. Both visible tires highlighted equally because the actual failed wheel is not known. Colored component must have its actual mechanical geometry and visible surfaces, NOT a circular glow blob. Preserve every other part unchanged in blue-gray. Subtle edge glow only at target. No text, labels, arrows or dots. Background truly transparent.
```

## vehicle-fuel.png

입력: `vehicle-cutaway.png` (편집 대상)

```text
Use case: precise-object-edit. EDIT TARGET: supplied transparent vehicle cutaway. Make one precise component-highlight variant for an interactive diagnostic UI. Keep EXACT same canvas, 2:1 aspect, camera, framing, silhouette, wheel positions, materials, all non-target pixels as faithfully as possible. Change ONLY the FUEL TANK under the rear passenger bench: the rectangular metal reservoir just ahead of the rear wheel at approximately x=71%, y=53%. Highlight ONLY that reservoir in warm AMBER #ffad48 with detailed three dimensional metal surface. Do NOT color the engine, battery, exhaust pipes or wheels. Colored component must have its actual mechanical geometry and visible surfaces, NOT a circular glow blob. Preserve every other part unchanged in blue-gray. Subtle edge glow only at target. No text, labels, arrows or dots. Background truly transparent.
```

## vehicle-oil.png

입력: `vehicle-cutaway.png` (편집 대상)

```text
Use case: precise-object-edit. EDIT TARGET: supplied transparent vehicle cutaway. Make one precise component-highlight variant for an interactive diagnostic UI. Keep EXACT same canvas, 2:1 aspect, camera, framing, silhouette, wheel positions, materials, all non-target pixels as faithfully as possible. Change ONLY the ENGINE OIL / LUBRICATION SYSTEM in the front engine assembly. Make the engine block, its lower oil sump and a few internal oil passages visibly CORAL RED #ff6565 through the front hood, highlighting the mechanical engine volume itself. Keep battery, radiator, suspension and air filter housing neutral. This shows the affected engine lubrication region, not an exact failed sensor. Colored component must have its actual mechanical geometry and visible surfaces, NOT a circular glow blob. Preserve every other part unchanged in blue-gray. Subtle edge glow only at target. No text, labels, arrows or dots. Background truly transparent.
```

## vehicle-coolant.png

입력: `vehicle-cutaway.png` (편집 대상)

```text
Use case: precise-object-edit. EDIT TARGET is supplied transparent vehicle cutaway. Create one aligned component-selection state for an interactive app. Keep EXACT same 2:1 canvas and every component position, camera, silhouette, perspective. Change ONLY the FRONT RADIATOR, the rectangular finned heat exchanger behind the front bumper at x=14%,y=65%, and its connecting coolant hoses only. Make them luminous icy CYAN #5de3ea, detailed metal fins still visible. No red fault implied. Keep all unrelated car parts neutral. Add a restrained local edge glow to the component itself, no circular marker. Keep the rest of the blue-gray car exactly unchanged. No labels, text, symbols, or arrows. Background truly transparent. The UI will separately reduce the opacity of the unselected body.
```

## vehicle-cabin.png

입력: `vehicle-cutaway.png` (편집 대상)

```text
Use case: precise-object-edit. EDIT TARGET is supplied transparent vehicle cutaway. Create one aligned component-selection state for an interactive app. Keep EXACT same 2:1 canvas and every component position, camera, silhouette, perspective. Change ONLY the occupant protection locations in the CABIN: small undeployed airbag MODULES at the steering wheel center and passenger dashboard, plus the two front seatbelt ribbons/buckles. Show these installed components through the transparent windshield and side glass in soft CORAL RED #ff6565. Do NOT deploy or inflate any airbag; no giant balloon. Do not color entire seat or cabin. Exact restraint locations are conceptual, not specific to a model. Add a restrained local edge glow to the component itself, no circular marker. Keep the rest of the blue-gray car exactly unchanged. No labels, text, symbols, or arrows. Background truly transparent. The UI will separately reduce the opacity of the unselected body.
```
