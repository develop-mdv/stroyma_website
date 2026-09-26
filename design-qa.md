# Проверка 3D-конфигуратора фасада

- Source visual truth: https://ceresitshop-msk.ru/assets/configurator/index.html?f=kamesh15&c=c2&p=tibet-5&t=day&l=full
- Implementation: http://127.0.0.1:8000/static/color_configurator/index.html?f=kamesh15&c=c2&p=tibet-5&t=day&l=full
- Host page: http://127.0.0.1:8000/color-selection/
- Source and implementation screenshots: paired captures in the in-app Browser during this task; the browser tool does not export screenshot files.
- Viewports: 1280×720 and 390×844 CSS px; captures at DPR 1 with matching pixel dimensions. Both direct widgets used the same default state (`kamesh15`, `c2`, `tibet-5`, `day`, `full`).

## Findings

No actionable P0, P1 or P2 differences in the widget. Paired desktop and phone captures show the same model, scenery, panel proportions, typography, colors, swatches, shadows and labels. The copied procedural assets keep image quality identical. The surrounding page follows СтройМа navigation and branding; the downloaded PNG brand caption is intentionally СтройМа.

## Interaction evidence

- Rotating the canvas changed the camera angle.
- Choosing Sahara 2/3 updated the facade and the host page selection summary.
- Choosing Короед, Tibet 2 and Закат updated the selected labels and URL parameters.
- The full-color picker opened and confirmed on a 390×844 phone viewport.
- The consultation button scrolled to the form and focused the name field.
- Browser console showed no errors on the page or standalone widget.
- Django system check and three targeted form/view tests passed, including restoration of the selected 3D state after a form error.

## Comparison history

One pass at matching desktop and mobile viewports. No P0, P1 or P2 finding required an iteration.

final result: passed
